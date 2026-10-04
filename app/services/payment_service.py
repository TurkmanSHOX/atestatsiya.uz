import hashlib
from datetime import datetime, timedelta
from flask import current_app, url_for
from app.extensions import db
from app.models.package import Package, Order, Payment, PaymentEvent, Entitlement, OrderStatus, PaymentStatus
from app.models.user import User
from app.services.telegram_service import TelegramService

class PaymentService:
    @staticmethod
    def create_order(user_id: int, package_id: int):
        """Yangi buyurtma yaratish va to'lovga tayyorlash"""
        user = User.query.get(user_id)
        package = Package.query.get(package_id)

        if not user or not package:
            raise ValueError("Foydalanuvchi yoki paket topilmadi.")

        order_num = Order.generate_order_number()
        order = Order(
            order_number=order_num,
            user_id=user.id,
            package_id=package.id,
            amount=package.price,
            status=OrderStatus.PENDING
        )
        db.session.add(order)
        db.session.flush()

        payment = Payment(
            order_id=order.id,
            user_id=user.id,
            amount=package.price,
            currency='UZS',
            payment_method='CLICK',
            status=PaymentStatus.PENDING
        )
        db.session.add(payment)
        db.session.commit()

        return order

    @staticmethod
    def generate_click_url(order_id: int, return_url: str = None) -> str:
        """Click to'lov sahifasiga yo'naltiruvchi URL generatsiyasi"""
        order = Order.query.get(order_id)
        if not order:
            return ""

        service_id = current_app.config.get('CLICK_SERVICE_ID', '')
        merchant_id = current_app.config.get('CLICK_MERCHANT_ID', '')
        
        if not return_url:
            return_url = url_for('user.dashboard', _external=True)

        amount_str = f"{order.amount:.2f}"
        return (
            f"https://my.click.uz/services/pay"
            f"?service_id={service_id}"
            f"&merchant_id={merchant_id}"
            f"&amount={amount_str}"
            f"&transaction_param={order.id}"
            f"&return_url={return_url}"
        )

    @staticmethod
    def handle_click_prepare(data: dict, ip_address: str = None):
        """
        Click Merchant API - Action 0 (Prepare)
        Signature: md5(click_trans_id + service_id + secret_key + merchant_trans_id + amount + action + sign_time)
        """
        click_trans_id = str(data.get('click_trans_id', ''))
        service_id = str(data.get('service_id', ''))
        merchant_trans_id = str(data.get('merchant_trans_id', '')) # Bizning order.id
        amount = str(data.get('amount', ''))
        action = str(data.get('action', '0'))
        error = int(data.get('error', 0))
        sign_time = str(data.get('sign_time', ''))
        sign_string = str(data.get('sign_string', ''))

        secret_key = current_app.config.get('CLICK_SECRET_KEY', '')

        # 1. Imzo tekshirish
        to_hash = f"{click_trans_id}{service_id}{secret_key}{merchant_trans_id}{amount}{action}{sign_time}"
        calculated_sign = hashlib.md5(to_hash.encode('utf-8')).hexdigest()

        if sign_string.lower() != calculated_sign.lower():
            return {
                'click_trans_id': click_trans_id,
                'merchant_trans_id': merchant_trans_id,
                'error': -1,
                'error_note': 'Sign check failed'
            }

        # 2. Buyurtmani tekshirish
        try:
            order_id = int(merchant_trans_id)
            order = Order.query.get(order_id)
        except Exception:
            order = None

        if not order:
            return {
                'click_trans_id': click_trans_id,
                'merchant_trans_id': merchant_trans_id,
                'error': -5,
                'error_note': 'User/Order does not exist'
            }

        if order.status == OrderStatus.PAID:
            return {
                'click_trans_id': click_trans_id,
                'merchant_trans_id': merchant_trans_id,
                'error': -4,
                'error_note': 'Already paid'
            }

        # 3. Summani solishtirish
        try:
            if float(amount) != float(order.amount):
                return {
                    'click_trans_id': click_trans_id,
                    'merchant_trans_id': merchant_trans_id,
                    'error': -2,
                    'error_note': 'Incorrect amount'
                }
        except ValueError:
            pass

        payment = Payment.query.filter_by(order_id=order.id).first()
        if not payment:
            payment = Payment(
                order_id=order.id,
                user_id=order.user_id,
                amount=order.amount,
                status=PaymentStatus.PENDING
            )
            db.session.add(payment)
            db.session.flush()

        payment.click_trans_id = click_trans_id
        payment.sign_time = sign_time

        # Event log
        event = PaymentEvent(
            payment_id=payment.id,
            event_type='PREPARE',
            payload=data,
            status='SUCCESS',
            ip_address=ip_address
        )
        db.session.add(event)
        db.session.commit()

        return {
            'click_trans_id': click_trans_id,
            'merchant_trans_id': merchant_trans_id,
            'merchant_prepare_id': payment.id,
            'error': 0,
            'error_note': 'Success'
        }

    @staticmethod
    def handle_click_complete(data: dict, ip_address: str = None):
        """
        Click Merchant API - Action 1 (Complete)
        Signature: md5(click_trans_id + service_id + secret_key + merchant_trans_id + merchant_prepare_id + amount + action + sign_time)
        """
        click_trans_id = str(data.get('click_trans_id', ''))
        service_id = str(data.get('service_id', ''))
        merchant_trans_id = str(data.get('merchant_trans_id', ''))
        merchant_prepare_id = str(data.get('merchant_prepare_id', ''))
        amount = str(data.get('amount', ''))
        action = str(data.get('action', '1'))
        error = int(data.get('error', 0))
        sign_time = str(data.get('sign_time', ''))
        sign_string = str(data.get('sign_string', ''))

        secret_key = current_app.config.get('CLICK_SECRET_KEY', '')

        # 1. Imzo tekshirish
        to_hash = f"{click_trans_id}{service_id}{secret_key}{merchant_trans_id}{merchant_prepare_id}{amount}{action}{sign_time}"
        calculated_sign = hashlib.md5(to_hash.encode('utf-8')).hexdigest()

        if sign_string.lower() != calculated_sign.lower():
            return {
                'click_trans_id': click_trans_id,
                'merchant_trans_id': merchant_trans_id,
                'error': -1,
                'error_note': 'Sign check failed'
            }

        try:
            payment_id = int(merchant_prepare_id)
            payment = Payment.query.get(payment_id)
        except Exception:
            payment = None

        if not payment:
            return {
                'click_trans_id': click_trans_id,
                'merchant_trans_id': merchant_trans_id,
                'error': -6,
                'error_note': 'Transaction not found'
            }

        # Agar Click tomonida xatolik yuz bergan bo'lsa
        if error < 0:
            payment.status = PaymentStatus.FAILED
            payment.error_code = error
            payment.error_note = str(data.get('error_note', 'Click error'))
            db.session.commit()
            return {
                'click_trans_id': click_trans_id,
                'merchant_trans_id': merchant_trans_id,
                'error': -9,
                'error_note': 'Transaction cancelled'
            }

        if payment.status == PaymentStatus.PAID:
            return {
                'click_trans_id': click_trans_id,
                'merchant_trans_id': merchant_trans_id,
                'merchant_confirm_id': payment.id,
                'error': 0,
                'error_note': 'Already completed'
            }

        # 2. To'lovni tasdiqlash va huquq (Entitlement) berish
        order = payment.order
        order.status = OrderStatus.PAID
        payment.status = PaymentStatus.PAID
        payment.click_paydoc_id = str(data.get('click_paydoc_id', ''))
        payment.updated_at = datetime.utcnow()

        package = order.package
        user = order.user

        # Yangi Entitlement yaratish
        now = datetime.utcnow()
        expires_at = now + timedelta(days=package.duration_days)

        entitlement = Entitlement(
            user_id=user.id,
            package_id=package.id,
            order_id=order.id,
            subject_id=None if package.is_all_subjects else (package.package_subjects[0].subject_id if package.package_subjects else None),
            starts_at=now,
            expires_at=expires_at,
            tests_remaining=package.test_limit,
            is_active=True
        )
        db.session.add(entitlement)

        # Event log
        event = PaymentEvent(
            payment_id=payment.id,
            event_type='COMPLETE',
            payload=data,
            status='SUCCESS',
            ip_address=ip_address
        )
        db.session.add(event)
        db.session.commit()

        # 3. Telegram orqali adminga xabar yuborish
        try:
            TelegramService.send_payment_notification(
                user=user,
                package=package,
                payment=payment
            )
        except Exception as e:
            current_app.logger.error(f"Telegram notification error: {e}")

        return {
            'click_trans_id': click_trans_id,
            'merchant_trans_id': merchant_trans_id,
            'merchant_confirm_id': payment.id,
            'error': 0,
            'error_note': 'Success'
        }
