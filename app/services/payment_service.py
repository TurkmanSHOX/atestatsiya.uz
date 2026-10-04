import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.payment import Payment, PaymentReceipt, PaymentStatus, PaymentMethod
from app.models.attestation import AttestationRegistration, RegistrationStep
from app.models.system import Notification
from app.services.audit_service import AuditService

ALLOWED_RECEIPT_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

class PaymentService:
    @staticmethod
    def process_manual_receipt(registration_id: int, user_id: int, amount: float, file_obj, upload_folder: str):
        reg = AttestationRegistration.query.get(registration_id)
        if not reg or reg.user_id != user_id:
            return {'success': False, 'message': "Attestatsiya arizasi topilmadi."}

        filename = secure_filename(file_obj.filename)
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in ALLOWED_RECEIPT_EXTENSIONS:
            return {'success': False, 'message': "Faqat JPG, PNG yoki PDF formatdagi cheklar qabul qilinadi."}

        receipts_dir = os.path.join(upload_folder, 'receipts')
        os.makedirs(receipts_dir, exist_ok=True)

        saved_name = f"receipt_{uuid.uuid4().hex[:12]}.{ext}"
        saved_path = os.path.join(receipts_dir, saved_name)
        file_obj.save(saved_path)
        file_size = os.path.getsize(saved_path)

        payment = Payment(
            registration_id=reg.id,
            user_id=user_id,
            amount=amount,
            currency=reg.attestation.currency,
            payment_method=PaymentMethod.CARD_MANUAL,
            transaction_id=f"TX-{uuid.uuid4().hex[:10].upper()}",
            status=PaymentStatus.PENDING
        )
        db.session.add(payment)
        db.session.flush()

        receipt = PaymentReceipt(
            payment_id=payment.id,
            file_path=f"uploads/receipts/{saved_name}",
            file_name=filename,
            file_size=file_size,
            mime_type=file_obj.mimetype or f"image/{ext}"
        )
        db.session.add(receipt)

        reg.step = RegistrationStep.ADMIN_REVIEW
        db.session.commit()

        AuditService.log_action(
            user_id=user_id,
            action='PAYMENT_UPLOADED',
            entity='PAYMENT',
            entity_id=payment.id,
            new_values={'amount': float(amount), 'filename': filename}
        )

        return {'success': True, 'payment_id': payment.id}

    @staticmethod
    def approve_payment(payment_id: int, admin_id: int):
        payment = Payment.query.get(payment_id)
        if not payment:
            return {'success': False, 'message': "To'lov topilmadi."}

        old_status = payment.status
        payment.status = PaymentStatus.PAID
        payment.confirmed_by = admin_id
        payment.confirmed_at = datetime.utcnow()

        reg = payment.registration
        reg.step = RegistrationStep.EXAM_READY

        # Bildirishnoma yuborish
        notif = Notification(
            user_id=payment.user_id,
            title="To'lov tasdiqlandi",
            message=f"«{reg.attestation.title}» bo'yicha to'lovingiz muvaffaqiyatli tasdiqlandi. Imtihon topshirishingiz mumkin.",
            link=f"/attestation/{reg.id}/instructions"
        )
        db.session.add(notif)
        db.session.commit()

        AuditService.log_action(
            user_id=admin_id,
            action='PAYMENT_APPROVED',
            entity='PAYMENT',
            entity_id=payment.id,
            old_values={'status': old_status},
            new_values={'status': PaymentStatus.PAID}
        )

        return {'success': True, 'message': "To'lov tasdiqlandi va imtihonga ruxsat berildi."}

    @staticmethod
    def reject_payment(payment_id: int, admin_id: int, reason: str):
        payment = Payment.query.get(payment_id)
        if not payment:
            return {'success': False, 'message': "To'lov topilmadi."}

        old_status = payment.status
        payment.status = PaymentStatus.REJECTED
        payment.rejection_reason = reason
        payment.confirmed_by = admin_id
        payment.confirmed_at = datetime.utcnow()

        reg = payment.registration
        reg.step = RegistrationStep.PAYMENT
        reg.admin_comment = reason

        # Bildirishnoma
        notif = Notification(
            user_id=payment.user_id,
            title="To'lov rad etildi",
            message=f"«{reg.attestation.title}» bo'yicha to'lov cheki rad etildi. Sababi: {reason}",
            link=f"/attestation/{reg.id}/payment"
        )
        db.session.add(notif)
        db.session.commit()

        AuditService.log_action(
            user_id=admin_id,
            action='PAYMENT_REJECTED',
            entity='PAYMENT',
            entity_id=payment.id,
            old_values={'status': old_status},
            new_values={'status': PaymentStatus.REJECTED, 'reason': reason}
        )

        return {'success': True, 'message': "To'lov rad etildi."}
