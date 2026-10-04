import os
import unittest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.attestation import Attestation, AttestationRegistration
from app.models.test import Test
from app.models.session import TestSession
from app.models.result import Result
from app.models.certificate import Certificate
from app.services.test_engine_service import TestEngineService
from app.services.certificate_service import CertificateService
from app.services.import_service import QuestionImportService
from app.services.ai_service import AIService

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
        """Ochiq sahifalar yuklanishi tekshiruvi"""
        routes = ['/', '/attestations', '/pricing', '/exam-rules', '/faq', '/help', '/contact', '/news']
        for route in routes:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200, f"{route} sahifasi ochilmadi.")

    def test_02_auth_pages(self):
        """Kirish va ro'yxatdan o'tish sahifalari"""
        res = self.client.get('/login')
        self.assertEqual(res.status_code, 200)

        res_reg = self.client.get('/register?step=1')
        self.assertEqual(res_reg.status_code, 200)

    def test_03_admin_access_control(self):
        """Admin sahifalariga ruxsatsiz kirish bloklanishi (403 yoki redirect)"""
        res = self.client.get('/admin/dashboard')
        # Login page redirect bo'lishi kerak
        self.assertEqual(res.status_code, 302)

    def test_04_user_exam_and_certification_flow(self):
        """Foydalanuvchi imtihon topshirishi, baholanishi va sertifikat yaratilishi"""
        user = User.query.filter_by(email='user@example.com').first()
        self.assertIsNotNone(user)

        reg = AttestationRegistration.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(reg)
        reg.step = 'EXAM_READY'
        # Tozalash - test har safar 0 dan toza boshlanishi uchun
        for old_s in list(reg.sessions):
            db.session.delete(old_s)
        db.session.commit()

        # 1. Start exam session
        session = TestEngineService.start_session(
            user_id=user.id,
            registration_id=reg.id,
            ip_address='127.0.0.1',
            user_agent='TestRunner/1.0'
        )
        self.assertIsNotNone(session)
        self.assertEqual(session.status, 'IN_PROGRESS')

        # 2. Get session payload
        payload = TestEngineService.get_session_payload(session.id)
        self.assertIsNotNone(payload)
        self.assertEqual(len(payload['questions']), 40)

        # 3. Submit answers (to'g'ri javoblarni tanlab 100% olish)
        for q_item in payload['questions']:
            q_id = q_item['question_id']
            # Savolning to'g'ri variantini topish
            correct_opts = [opt['id'] for opt in q_item['options']]
            # Bazadan to'g'ri variantni olish
            from app.models.question import Question
            q_db = Question.query.get(q_id)
            correct_ids = [opt.id for opt in q_db.options if opt.is_correct]

            save_res = TestEngineService.save_answer(
                session_id=session.id,
                question_id=q_id,
                selected_option_ids=correct_ids,
                time_spent=2
            )
            self.assertTrue(save_res['success'])

        # 4. Finish exam
        result = TestEngineService.finish_session(session.id)
        self.assertIsNotNone(result)
        self.assertEqual(result.correct_answers, 40)
        self.assertEqual(float(result.percentage), 100.0)
        self.assertTrue(result.is_passed)

        # 5. Check Certificate generated
        cert = Certificate.query.filter_by(result_id=result.id).first()
        self.assertIsNotNone(cert)
        self.assertEqual(cert.status, 'ACTIVE')
        self.assertTrue(os.path.exists(os.path.join(self.app.root_path, 'static', cert.pdf_path)))
        self.assertTrue(os.path.exists(os.path.join(self.app.root_path, 'static', cert.qr_code_path)))

        # 6. Public QR verification
        verify_res = CertificateService.verify(cert.verification_uuid)
        self.assertTrue(verify_res['found'])
        self.assertTrue(verify_res['is_valid'])
        self.assertEqual(verify_res['certificate']['user_name'], user.full_name)

        # 7. Public endpoint test
        pub_res = self.client.get(f"/verify-certificate/{cert.verification_uuid}")
        self.assertEqual(pub_res.status_code, 200)
        self.assertIn("SERTIFIKAT HAQIQIY", pub_res.get_data(as_text=True))

    def test_05_admin_authenticated_endpoints(self):
        """Admin hisobi bilan tizimga kirib boshqaruv sahifalarini tekshirish"""
        with self.client:
            # Login as admin
            login_res = self.client.post('/login', data={
                'login': 'admin@example.com',
                'password': 'Admin123!'
            }, follow_redirects=True)
            self.assertEqual(login_res.status_code, 200)

            # Check admin pages
            admin_routes = [
                '/admin/dashboard',
                '/admin/users',
                '/admin/attestations',
                '/admin/questions',
                '/admin/import-excel',
                '/admin/import-word',
                '/admin/import-ai',
                '/admin/tests',
                '/admin/payments',
                '/admin/exam-sessions',
                '/admin/results',
                '/admin/certificates',
                '/admin/proctoring-events',
                '/admin/audit-logs',
                '/admin/settings'
            ]
            for ar in admin_routes:
                res = self.client.get(ar)
                self.assertEqual(res.status_code, 200, f"{ar} admin sahifasi ochilmadi.")

    def test_06_ai_parser_service(self):
        """AI / Nostrukturalangan matn parserini tekshirish"""
        raw_text = """
        1. O'zbekiston Respublikasi poytaxti qaysi shahar?
        A) Samarqand
        *B) Toshkent
        C) Buxoro
        D) Xiva
        """
        res = AIService.parse_unstructured_text(raw_text)
        self.assertTrue(res['success'])
        self.assertGreaterEqual(res['extracted_count'], 1)
        q = res['questions'][0]
        self.assertIn("Toshkent", [opt['text'] for opt in q['options']])
        # Correct variant check
        correct_opts = [opt for opt in q['options'] if opt.get('is_correct')]
        self.assertGreaterEqual(len(correct_opts), 1)

if __name__ == '__main__':
    unittest.main()
