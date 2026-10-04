import os
import hashlib
import unittest
from datetime import datetime, timedelta
from app import create_app
from app.extensions import db
from app.models.user import User, UserRole
from app.models.question import Subject, Topic, Question, QuestionOption, QuestionType, DifficultyLevel
from app.models.package import Package, Order, Payment, Entitlement, PaymentStatus
from app.models.test import Test, TestType
from app.models.session import TestSession, SessionStatus
from app.models.result import Result, UserQuestionStat, UserTopicStat
from app.services.test_engine_service import TestEngineService
from app.services.analytics_service import AnalyticsService
from app.services.payment_service import PaymentService
from app.services.telegram_service import TelegramService
from app.services.ai_service import AIService
from app.services.import_service import QuestionImportService

class AttestatsiyaTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('development')
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_01_public_pages(self):
        """Ochiq sahifalar to'g'ri 200 OK qaytarishini tekshirish"""
        routes = ['/', '/subjects', '/packages', '/how-it-works', '/faq', '/contact']
        for route in routes:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200, f"{route} sahifasi ochilmadi.")

    def test_02_auth_pages_and_registration(self):
        """Kirish va o'qituvchi ro'yxatdan o'tish (2 bosqichli) jarayoni"""
        # Login sahifasi
        res_login = self.client.get('/login')
        self.assertEqual(res_login.status_code, 200)

        # Ro'yxatdan o'tish 1-bosqich
        res_reg1 = self.client.get('/register?step=1')
        self.assertEqual(res_reg1.status_code, 200)

        # Test ro'yxatdan o'tish (1-bosqich)
        ts_now = int(datetime.utcnow().timestamp() * 100)
        test_email = f"test_teacher_{ts_now}@example.com"
        test_phone = f"+99890{ts_now % 10000000:07d}"
        res_step1 = self.client.post('/register?step=1', data={
            'current_step': 1,
            'first_name': 'Nodira',
            'last_name': 'Alimova',
            'middle_name': 'Botirovna',
            'email': test_email,
            'phone': test_phone,
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        }, follow_redirects=True)
        self.assertEqual(res_step1.status_code, 200)

        # Test ro'yxatdan o'tish (2-bosqich)
        res_step2 = self.client.post('/register?step=2', data={
            'current_step': 2,
            'region': 'Toshkent shahri',
            'organization': '15-umumiy o\'rta ta\'lim maktabi',
            'position': 'Boshlang\'ich sinf o\'qituvchisi',
            'specialty': 'Boshlang\'ich ta\'lim',
            'experience_years': 6
        }, follow_redirects=True)
        self.assertEqual(res_step2.status_code, 200)

        # Foydalanuvchi bazada mavjudligi va roli FOYDALANUVCHI ekanligi
        created_user = User.query.filter_by(email=test_email).first()
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.role, UserRole.FOYDALANUVCHI)
        self.assertTrue(created_user.check_password('Password123!'))

    def test_03_admin_access_control(self):
        """Admin paneliga ruxsatsiz yoki oddiy foydalanuvchi kira olmasligi"""
        # Anonim foydalanuvchi redirect bo'lishi kerak
        res_anon = self.client.get('/admin/dashboard')
        self.assertEqual(res_anon.status_code, 302)

        # Oddiy o'qituvchi bilan kirish
        teacher = User.query.filter_by(email='user@example.com').first()
        self.assertIsNotNone(teacher)
        
        self.client.post('/login', data={'login': teacher.email, 'password': 'User123!'}, follow_redirects=True)
        res_teacher = self.client.get('/admin/dashboard')
        self.assertEqual(res_teacher.status_code, 403)

        # Chiqish
        self.client.get('/logout', follow_redirects=True)

        # Admin foydalanuvchi bilan kirish
        admin = User.query.filter_by(email='admin@example.com').first()
        self.assertIsNotNone(admin)

        self.client.post('/login', data={'login': admin.email, 'password': 'Admin123!'}, follow_redirects=True)
        res_admin = self.client.get('/admin/dashboard')
        self.assertEqual(res_admin.status_code, 200)

        # Boshqa admin bo'limlari
        for admin_route in ['/admin/subjects', '/admin/questions', '/admin/packages', '/admin/payments', '/admin/telegram', '/admin/tests']:
            r = self.client.get(admin_route)
            self.assertEqual(r.status_code, 200, f"Admin yo'li {admin_route} ochilmadi.")

    def test_04_test_engine_session_and_answers(self):
        """Test topshirish mexanizmi: savollarni olish, javob saqlash, yakunlash va xatolarni hisoblash"""
        teacher = User.query.filter_by(email='user@example.com').first()
        self.assertIsNotNone(teacher)

        # Matematika bepul testini olish
        math_subj = Subject.query.filter_by(name='Matematika').first()
        self.assertIsNotNone(math_subj)

        test = Test.query.filter_by(subject_id=math_subj.id, is_free=True).first()
        self.assertIsNotNone(test)

        # Sessiyani boshlash
        session = TestEngineService.start_session(
            user_id=teacher.id,
            test_id=test.id,
            ip_address='127.0.0.1',
            user_agent='TestRunner/2.0'
        )
        self.assertIsNotNone(session)
        self.assertEqual(session.status, SessionStatus.IN_PROGRESS)

        # Payload olish
        payload = TestEngineService.get_session_payload(session.id)
        self.assertIn('questions', payload)
        self.assertGreater(len(payload['questions']), 0)

        # Javoblarni saqlash (birinchi savolga to'g'ri, ikkinchisiga xato javob)
        for idx, q_data in enumerate(payload['questions']):
            q_id = q_data['question_id']
            q_db = Question.query.get(q_id)
            
            if idx == 0:
                # To'g'ri variant
                chosen = [opt.id for opt in q_db.options if opt.is_correct]
            else:
                # Xato variant
                wrong_opts = [opt.id for opt in q_db.options if not opt.is_correct]
                chosen = wrong_opts[:1] if wrong_opts else []

            res_save = TestEngineService.save_answer(
                session_id=session.id,
                question_id=q_id,
                selected_option_ids=chosen,
                time_spent=5
            )
            self.assertTrue(res_save['success'])

        # Sessiyani yakunlash
        result = TestEngineService.finish_session(session.id)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.total_questions, 1)
        self.assertEqual(result.correct_answers, 1)
        self.assertIsNotNone(result.ai_recommendation)

        # Foydalanuvchining xato va mavzu statistikasi yangilanganligini tekshirish
        mistakes_count = UserQuestionStat.query.filter_by(user_id=teacher.id, is_last_correct=False).count()
        self.assertGreaterEqual(mistakes_count, 1)

    def test_05_analytics_readiness_score(self):
        """Tayyorgarlik darajasi ko'rsatkichi (Readiness Score) va zaif mavzular tahlili"""
        teacher = User.query.filter_by(email='user@example.com').first()
        self.assertIsNotNone(teacher)

        score = AnalyticsService.get_user_readiness_score(teacher.id)
        self.assertIsInstance(score, (int, float))
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

        weak_topics = AnalyticsService.get_weak_topics(teacher.id)
        self.assertIsInstance(weak_topics, list)

        stats = AnalyticsService.get_user_dashboard_stats(teacher.id)
        self.assertIn('readiness_score', stats)
        self.assertIn('total_tests', stats)
        self.assertIn('weak_topics_count', stats)
        self.assertIn('mistakes_count', stats)

    def test_06_click_payment_webhook(self):
        """Click to'lov tizimi integratsiyasi: Prepare va Complete so'rovlari va MD5 imzo tekshiruvi"""
        teacher = User.query.filter_by(email='user@example.com').first()
        pkg = Package.query.first()
        self.assertIsNotNone(pkg)

        # 1. Buyurtma yaratish
        order = PaymentService.create_order(user_id=teacher.id, package_id=pkg.id)
        self.assertIsNotNone(order)
        self.assertEqual(order.status, 'PENDING')

        secret = self.app.config.get('CLICK_SECRET_KEY', 'test_secret_key')
        service_id = self.app.config.get('CLICK_SERVICE_ID', 'test_service_id')
        click_trans_id = f"CLK_TEST_{int(datetime.utcnow().timestamp())}"
        amount = float(pkg.price)
        sign_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        # 2. Click Prepare (action = 0)
        # MD5 digest = md5(click_trans_id + service_id + secret_key + merchant_trans_id + amount + action + sign_time)
        prep_str = f"{click_trans_id}{service_id}{secret}{order.id}{amount}0{sign_time}"
        sign_prep = hashlib.md5(prep_str.encode('utf-8')).hexdigest()

        prep_data = {
            'click_trans_id': click_trans_id,
            'service_id': service_id,
            'merchant_trans_id': str(order.id),
            'amount': amount,
            'action': 0,
            'error': 0,
            'error_note': 'Success',
            'sign_time': sign_time,
            'sign_string': sign_prep
        }
        res_prep = self.client.post('/api/payments/click/prepare', data=prep_data)
        self.assertEqual(res_prep.status_code, 200)
        json_prep = res_prep.get_json()
        self.assertEqual(json_prep.get('error'), 0)
        merchant_prepare_id = json_prep.get('merchant_prepare_id')
        self.assertIsNotNone(merchant_prepare_id)

        # 3. Click Complete (action = 1)
        # MD5 digest = md5(click_trans_id + service_id + secret_key + merchant_trans_id + merchant_prepare_id + amount + action + sign_time)
        comp_str = f"{click_trans_id}{service_id}{secret}{order.id}{merchant_prepare_id}{amount}1{sign_time}"
        sign_comp = hashlib.md5(comp_str.encode('utf-8')).hexdigest()

        comp_data = {
            'click_trans_id': click_trans_id,
            'service_id': service_id,
            'merchant_trans_id': str(order.id),
            'merchant_prepare_id': merchant_prepare_id,
            'amount': amount,
            'action': 1,
            'error': 0,
            'error_note': 'Success',
            'sign_time': sign_time,
            'sign_string': sign_comp
        }
        res_comp = self.client.post('/api/payments/click/complete', data=comp_data)
        self.assertEqual(res_comp.status_code, 200)
        json_comp = res_comp.get_json()
        self.assertEqual(json_comp.get('error'), 0)

        # Buyurtma va to'lov holati CONFIRMED / PAID bo'lganligi
        order_db = Order.query.get(order.id)
        self.assertEqual(order_db.status, 'PAID')

        payment_db = Payment.query.filter_by(order_id=order.id).first()
        self.assertIsNotNone(payment_db)
        self.assertEqual(payment_db.status, PaymentStatus.CONFIRMED)

        # Foydalanuvchiga Entitlement (kirish ruxsati) berilganligini tekshirish
        ent = Entitlement.query.filter_by(order_id=order.id).first()
        self.assertIsNotNone(ent)
        self.assertTrue(ent.is_valid)

    def test_07_telegram_service_handling(self):
        """Telegram bildirishnoma xizmati xatoliksiz xabar yuborishga urinishini tekshirish"""
        teacher = User.query.filter_by(email='user@example.com').first()
        pkg = Package.query.first()
        pmt = Payment.query.first()

        # Dummy token bilan ham xatolik (exception) otmasligi va False/True qaytarishi kerak
        res = TelegramService.send_payment_notification(teacher, pkg, pmt)
        self.assertIsInstance(res, bool)

    def test_08_ai_and_import_services(self):
        """Sun'iy intellekt matn tahlili va import funksiyalari"""
        uid = int(datetime.utcnow().timestamp() * 1000)
        raw_text = f"""
        1. Savol {uid}: O'zbekiston Respublikasi Konstitutsiyasi nechanchi moddadan iborat?
        A) 128
        *B) 155
        C) 120
        D) 100

        2. Savol {uid}: Pifagor teoremasi qaysi uchburchak uchun amal qiladi?
        *A) To'g'ri burchakli
        B) Teng yonli
        C) Muntazam
        D) O'tkir burchakli
        """
        ai_res = AIService.parse_unstructured_text(raw_text)
        self.assertTrue(ai_res['success'])
        self.assertEqual(len(ai_res['questions']), 2)

        # Savollarni bazaga saqlash va duplikatni o'tkazib yuborish
        import_res = QuestionImportService.save_imported_questions(ai_res['questions'])
        self.assertGreaterEqual(import_res['imported'], 1)

        # Qayta import qilganda duplikat deb o'tkazib yuborishini tekshirish
        re_import = QuestionImportService.save_imported_questions(ai_res['questions'])
        self.assertEqual(re_import['imported'], 0)
        self.assertEqual(re_import['skipped'], len(ai_res['questions']))

if __name__ == '__main__':
    unittest.main()
