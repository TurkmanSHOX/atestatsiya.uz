import os
import requests
from datetime import datetime
from flask import current_app

class TelegramService:
    @staticmethod
    def send_payment_notification(user, package, payment, subject_name=None):
        """
        Click orqali to'lov muvaffaqiyatli yakunlangach, Telegram orqali Adminlarga bildirishnoma yuborish.
        Format talabi:
        🔔 YANGI TO'LOV
        Foydalanuvchi: ...
        Fan: ...
        Paket: ...
        Summa: 10 000 so'm
        To'lov tizimi: Click
        Tranzaksiya: ...
        Vaqt: ...
        Holat: PAID
        """
        bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN') or os.environ.get('TELEGRAM_BOT_TOKEN')
        chat_id = current_app.config.get('TELEGRAM_ADMIN_CHAT_ID') or os.environ.get('TELEGRAM_ADMIN_CHAT_ID')

        if not bot_token or not chat_id:
            current_app.logger.info("Telegram Bot Token yoki Admin Chat ID sozlanmagan, xabar yuborilmadi.")
            return False

        subj_text = subject_name if subject_name else ("Barcha fanlar" if package.is_all_subjects else "Tanlangan fanlar")
        now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M')

        message = (
            f"🔔 *YANGI TO'LOV*\n\n"
            f"👤 *Foydalanuvchi:* {user.full_name} ({user.phone})\n"
            f"📚 *Fan:* {subj_text}\n"
            f"📦 *Paket:* {package.name}\n"
            f"💰 *Summa:* {payment.formatted_amount()}\n"
            f"💳 *To'lov tizimi:* {payment.payment_method}\n"
            f"🆔 *Tranzaksiya:* `{payment.click_trans_id or payment.id}`\n"
            f"🕒 *Vaqt:* {now_str}\n"
            f"✅ *Holat:* PAID"
        )

        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            resp = requests.post(url, json=payload, timeout=5)
            return resp.status_code == 200
        except Exception as e:
            current_app.logger.error(f"Telegramga xabar yuborishda xatolik: {e}")
            return False
