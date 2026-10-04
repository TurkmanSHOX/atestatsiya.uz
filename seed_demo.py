import re
import os
from datetime import datetime, date, timedelta
from app import create_app
from app.extensions import db
from app.models.user import User, UserRole
from app.models.question import (
    Subject, SubjectSection, Topic, Question, QuestionOption, 
    QuestionType, DifficultyLevel
)
from app.models.package import Package, PackageSubject, Order, Payment, Entitlement
from app.models.test import Test, TestType
from app.models.session import TestSession, TestAnswer, SessionStatus
from app.models.result import Result, ResultDetail, UserQuestionStat, UserTopicStat
from app.models.system import Setting

app = create_app()

def slugify(text):
    text = text.lower()
    text = re.sub(r'[\'"`ʻʼ’]', '', text)
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text

def seed():
    with app.app_context():
        print("=" * 60)
        print("ATTESTATSIYA.UZ 2.0 — DEMO MA'LUMOTLARNI YUKLASH")
        print("=" * 60)

        print("\n[1/7] Ma'lumotlar bazasi jadvallari yangilanmoqda...")
        db.create_all()

        # 1. Sozlamalar
        Setting.set_val('site_name', 'Attestatsiya.uz')
        Setting.set_val('support_phone', '+998 71 200 00 00')
        Setting.set_val('support_email', 'info@attestatsiya.uz')
        Setting.set_val('telegram_bot_token', '123456789:ABCdefGhIJKlmNoPQRstuVWXyz')
        Setting.set_val('telegram_admin_chat_id', '-1001234567890')
        Setting.set_val('click_merchant_id', '12345')
        Setting.set_val('click_service_id', '67890')
        Setting.set_val('click_secret_key', 'test_secret_key_123')

        # 2. Foydalanuvchilar (FAQAT 2 TA ROL: ADMIN va FOYDALANUVCHI)
        print("\n[2/7] Foydalanuvchilar yaratilmoqda (Admin va O'qituvchi)...")
        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin:
            admin = User(
                role=UserRole.ADMIN,
                email='admin@example.com',
                phone='+998901112233',
                first_name='Administrator',
                last_name='Boshqaruvchi',
                organization='O\'qituvchilar tayyorlov markazi',
                position='Bosh mutaxassis',
                is_active=True,
                is_verified=True
            )
            admin.set_password('Admin123!')
            db.session.add(admin)

        teacher = User.query.filter_by(email='user@example.com').first()
        if not teacher:
            teacher = User(
                role=UserRole.FOYDALANUVCHI,
                email='user@example.com',
                phone='+998909998877',
                first_name='Dilshod',
                last_name='Karimov',
                middle_name='Ergashovich',
                birth_date=date(1989, 4, 15),
                gender='ERKAK',
                region='Toshkent shahri',
                organization='154-sonli umumiy o\'rta ta\'lim maktabi',
                position='Matematika fani o\'qituvchisi',
                specialty='Matematika va informatika',
                experience_years=11,
                is_active=True,
                is_verified=True
            )
            teacher.set_password('User123!')
            db.session.add(teacher)

        db.session.commit()

        # 3. Attestatsiya Fanlari Katalogi (26 ta fan)
        print("\n[3/7] O'zbekiston maktab pedagoglari uchun 26 ta fan katalogi yaratilmoqda...")
        subjects_catalog = [
            ("Matematika", "Algebra, Geometriya, Matematik analiz va ehtimollar nazariyasi", "MAT"),
            ("Informatika va axborot texnologiyalari", "Dasturlash, algoritmlar, tarmoqlar va axborot xavfsizligi", "INF"),
            ("Fizika", "Mexanika, Molekulyar fizika, Elektrodinamika va Optika", "FIZ"),
            ("Kimyo", "Anorganik, Organik, Analitik va Umumiy kimyo", "KIM"),
            ("Biologiya", "Botanika, Zoologiya, Odam anatomiyasi va Sitologiya", "BIO"),
            ("Geografiya", "Tabiiy, Ijtimoiy-iqtisodiy va O'zbekiston geografiyasi", "GEO"),
            ("Tarix", "O'zbekiston tarixi, Jahon tarixi va Manbashunoslik", "TAR"),
            ("Ona tili va adabiyoti", "Fonetika, Morfologiya, Sintaksis va O'zbek mumtoz adabiyoti", "ONA"),
            ("O'zbek tili", "Davlat tili sifatida o'qitish metodikasi va nutq madaniyati", "UZB"),
            ("Ingliz tili", "Grammar, Reading comprehension, Vocabulary and Methodology", "ENG"),
            ("Rus tili", "Русский язык и литература для национальных школ", "RUS"),
            ("Nemis tili", "Deutsche Sprache und Fachdidaktik", "DEU"),
            ("Fransuz tili", "Langue française et méthode pédagogique", "FRA"),
            ("Qoraqalpoq tili", "Qaraqalpaq tili hám ádebiyatı", "QAR"),
            ("Davlat va huquq asoslari", "Konstitutsiya, Fuqarolik, Mehnat va Jinoyat huquqi", "HUQ"),
            ("Tarbiya", "Ma'naviyat asoslari, Etika va milliy tarbiya", "TRB"),
            ("Psixologiya", "Yosh davrlari psixologiyasi, Pedagogik muloqot va ijtimoiy moslashuv", "PSI"),
            ("Jismoniy tarbiya", "Harakatli o'yinlar, sport turlari va jismoniy salomatlik", "JIS"),
            ("Chaqiruvga qadar boshlang'ich tayyorgarlik", "Harbiy bilim asoslari va fuqaro muhofazasi", "CHBT"),
            ("Iqtisodiyot asoslari", "Mikroiqtisodiyot, Makroiqtisodiyot va Moliya asoslari", "IQT"),
            ("Texnologiya", "Mehnat ta'limi, Servis xizmati va Texnik modellashtirish", "TEX"),
            ("Musiqa", "Musiqa nazariyasi, Notatsiya, Vokal va Cholg'u ijrochiligi", "MUS"),
            ("Tasviriy san'at", "Rasm chizish qoidalari, Rangshunoslik va Kompozitsiya", "SAN"),
            ("Boshlang'ich ta'lim", "Savod o'rgatish, O'qish savodxonligi, Boshlang'ich matematika", "BOS"),
            ("Maktabgacha ta'lim", "Maktabgacha yoshdagi bolalarni rivojlantirish va tarbiyalash", "MTM"),
            ("Pedagogika va kasbiy mahorat", "Didaktika, dars tahlili, kriterial baholash va zamonaviy metodlar", "PED")
        ]

        subject_objs = {}
        for idx, (s_name, s_desc, s_code) in enumerate(subjects_catalog, 1):
            s_slug = slugify(s_name)
            subj = Subject.query.filter_by(name=s_name).first()
            if not subj:
                subj = Subject(
                    name=s_name,
                    slug=s_slug,
                    code=s_code,
                    description=s_desc,
                    order_num=idx,
                    is_active=True
                )
                db.session.add(subj)
                db.session.flush()
            subject_objs[s_name] = subj

        db.session.commit()

        # 4. Bo'limlar va Mavzular (Sections and Topics)
        print("\n[4/7] Asosiy fanlar bo'yicha Bo'limlar va Mavzular tuzilmasi yaratilmoqda...")
        math_subj = subject_objs["Matematika"]
        math_sections_data = [
            ("Algebra va matematik analiz", [
                "Chiziqli va kvadrat tenglamalar",
                "Tengsizliklar va ularning sistemalari",
                "Arifmetik va geometrik progressiya",
                "Ko'rsatkichli va logarifmik funksiyalar",
                "Hosilaning geometrik va mexanik ma'nosi",
                "Aniq va aniqmas integrallar"
            ]),
            ("Geometriya va stereometriya", [
                "Uchburchaklar va ularning ajoyib nuqtalari",
                "To'rtburchaklar va ko'pburchaklar",
                "Aylana, doira va ularning elementlari",
                "Fazoda to'g'ri chiziq va tekisliklar",
                "Prizma, piramida va ko'pyoqlar",
                "Aylanma jismlar: silindr, konus, shar"
            ]),
            ("Trigonometriya va kombinatorika", [
                "Trigonometrik funksiyalar va formulalar",
                "Trigonometrik tenglamalar va tengsizliklar",
                "Kombinatorika asoslari va Nyuton binomi",
                "Ehtimollar nazariyasi elementlari"
            ])
        ]

        math_topic_objs = {}
        for s_order, (sec_name, topics_list) in enumerate(math_sections_data, 1):
            sec = SubjectSection.query.filter_by(subject_id=math_subj.id, name=sec_name).first()
            if not sec:
                sec = SubjectSection(subject_id=math_subj.id, name=sec_name, order_num=s_order)
                db.session.add(sec)
                db.session.flush()

            for t_order, t_name in enumerate(topics_list, 1):
                top = Topic.query.filter_by(subject_id=math_subj.id, name=t_name).first()
                if not top:
                    top = Topic(
                        subject_id=math_subj.id,
                        section_id=sec.id,
                        name=t_name,
                        code=f"M{s_order}.{t_order}",
                        order_num=t_order,
                        is_active=True
                    )
                    db.session.add(top)
                    db.session.flush()
                math_topic_objs[t_name] = top

        # Informatika uchun bo'lim va mavzular
        inf_subj = subject_objs["Informatika va axborot texnologiyalari"]
        inf_sections_data = [
            ("Dasturlash va algoritmlash", [
                "Python dasturlash tili asoslari",
                "Massivlar, ro'yxatlar va lug'atlar",
                "Rekursiv algoritmlar va funksiyalar",
                "Murakkablik nazariyasi va saralash algoritmlari"
            ]),
            ("Axborot tizimlari va xavfsizlik", [
                "Ma'lumotlar bazasi va SQL so'rovlar",
                "Kompyuter tarmoqlari va protokollar",
                "Kiberxavfsizlik va axborotni shifrlash"
            ])
        ]
        inf_topic_objs = {}
        for s_order, (sec_name, topics_list) in enumerate(inf_sections_data, 1):
            sec = SubjectSection.query.filter_by(subject_id=inf_subj.id, name=sec_name).first()
            if not sec:
                sec = SubjectSection(subject_id=inf_subj.id, name=sec_name, order_num=s_order)
                db.session.add(sec)
                db.session.flush()

            for t_order, t_name in enumerate(topics_list, 1):
                top = Topic.query.filter_by(subject_id=inf_subj.id, name=t_name).first()
                if not top:
                    top = Topic(
                        subject_id=inf_subj.id,
                        section_id=sec.id,
                        name=t_name,
                        code=f"INF{s_order}.{t_order}",
                        order_num=t_order,
                        is_active=True
                    )
                    db.session.add(top)
                    db.session.flush()
                inf_topic_objs[t_name] = top

        # Ona tili va Pedagogika uchun ham mavzular
        ped_subj = subject_objs["Pedagogika va kasbiy mahorat"]
        ped_sec = SubjectSection.query.filter_by(subject_id=ped_subj.id, name="Umumiy pedagogika").first()
        if not ped_sec:
            ped_sec = SubjectSection(subject_id=ped_subj.id, name="Umumiy pedagogika", order_num=1)
            db.session.add(ped_sec)
            db.session.flush()

        ped_topics = ["Didaktika va o'qitish tamoyillari", "Kriterial baholash tizimi", "Interfaol ta'lim metodlari"]
        ped_topic_objs = {}
        for idx, t_name in enumerate(ped_topics, 1):
            top = Topic.query.filter_by(subject_id=ped_subj.id, name=t_name).first()
            if not top:
                top = Topic(subject_id=ped_subj.id, section_id=ped_sec.id, name=t_name, code=f"PED{idx}", order_num=idx)
                db.session.add(top)
                db.session.flush()
            ped_topic_objs[t_name] = top

        db.session.commit()

        # 5. Savollar Banki (Bank of Questions)
        print("\n[5/7] Savollar banki boyitilmoqda (Single choice, izohlar, qiyinlik darajalari)...")
        sample_questions_data = [
            # Matematika savollari
            {
                'subject': math_subj,
                'topic': math_topic_objs["Chiziqli va kvadrat tenglamalar"],
                'difficulty': DifficultyLevel.EASY,
                'text': "Agar x² - 5x + 6 = 0 bo'lsa, tenglamaning ildizlari yig'indisini toping.",
                'explanation': "Viyet teoremasiga ko'ra, x1 + x2 = -p = 5 bo'ladi.",
                'options': [
                    ('A', '5', True),
                    ('B', '-5', False),
                    ('C', '6', False),
                    ('D', '-6', False)
                ]
            },
            {
                'subject': math_subj,
                'topic': math_topic_objs["Chiziqli va kvadrat tenglamalar"],
                'difficulty': DifficultyLevel.MEDIUM,
                'text': "2x² - 7x + 3 = 0 tenglamaning ildizlari ko'paytmasini toping.",
                'explanation': "Keltirilmagan kvadrat tenglamada Viyet teoremasiga ko'ra: x1 * x2 = c/a = 3/2 = 1.5.",
                'options': [
                    ('A', '1.5', True),
                    ('B', '3.5', False),
                    ('C', '3', False),
                    ('D', '-1.5', False)
                ]
            },
            {
                'subject': math_subj,
                'topic': math_topic_objs["Ko'rsatkichli va logarifmik funksiyalar"],
                'difficulty': DifficultyLevel.EASY,
                'text': "log₂(32) ifodaning qiymatini toping.",
                'explanation': "2 ning 5-darajasi 32 ga teng: 2⁵ = 32, shuning uchun log₂(32) = 5.",
                'options': [
                    ('A', '5', True),
                    ('B', '4', False),
                    ('C', '6', False),
                    ('D', '16', False)
                ]
            },
            {
                'subject': math_subj,
                'topic': math_topic_objs["Hosilaning geometrik va mexanik ma'nosi"],
                'difficulty': DifficultyLevel.MEDIUM,
                'text': "f(x) = x³ - 3x² + 4x - 5 funksiyaning x = 2 nuqtadagi hosilasi qiymatini toping.",
                'explanation': "f'(x) = 3x² - 6x + 4. x = 2 da f'(2) = 3(4) - 6(2) + 4 = 12 - 12 + 4 = 4.",
                'options': [
                    ('A', '4', True),
                    ('B', '2', False),
                    ('C', '6', False),
                    ('D', '0', False)
                ]
            },
            {
                'subject': math_subj,
                'topic': math_topic_objs["Uchburchaklar va ularning ajoyib nuqtalari"],
                'difficulty': DifficultyLevel.EASY,
                'text': "To'g'ri burchakli uchburchakning katetlari 6 sm va 8 sm bo'lsa, gipotenuzasini toping.",
                'explanation': "Pifagor teoremasi: c = √(6² + 8²) = √(36 + 64) = √100 = 10 sm.",
                'options': [
                    ('A', '10 sm', True),
                    ('B', '12 sm', False),
                    ('C', '14 sm', False),
                    ('D', '11 sm', False)
                ]
            },
            {
                'subject': math_subj,
                'topic': math_topic_objs["Uchburchaklar va ularning ajoyib nuqtalari"],
                'difficulty': DifficultyLevel.HARD,
                'text': "Gipotenuzasi 25 sm, katetlaridan biri 15 sm bo'lgan to'g'ri burchakli uchburchakka ichki chizilgan aylana radiusini toping.",
                'explanation': "Ikkinchi katet: b = √(25² - 15²) = 20 sm. Ichki chizilgan aylana radiusi r = (a + b - c)/2 = (15 + 20 - 25)/2 = 10/2 = 5 sm.",
                'options': [
                    ('A', '5 sm', True),
                    ('B', '4 sm', False),
                    ('C', '6 sm', False),
                    ('D', '7.5 sm', False)
                ]
            },
            {
                'subject': math_subj,
                'topic': math_topic_objs["Trigonometrik funksiyalar va formulalar"],
                'difficulty': DifficultyLevel.EASY,
                'text': "sin²(α) + cos²(α) ifodaning asosiy trigonometrik tenglik bo'yicha qiymati nimaga teng?",
                'explanation': "Asosiy trigonometrik ayniyatga ko'ra har qanday burchak uchun sin²(α) + cos²(α) = 1 ga teng.",
                'options': [
                    ('A', '1', True),
                    ('B', '0', False),
                    ('C', '2', False),
                    ('D', 'tan(α)', False)
                ]
            },
            {
                'subject': math_subj,
                'topic': math_topic_objs["Ehtimollar nazariyasi elementlari"],
                'difficulty': DifficultyLevel.MEDIUM,
                'text': "Oddiy o'yin suyagi (zarracha) bir marta tashlanganda, juft son tushish ehtimolligini toping.",
                'explanation': "Jami holatlar soni n = 6. Qulay holatlar m = {2, 4, 6} (3 ta). P = 3/6 = 1/2 = 0.5.",
                'options': [
                    ('A', '0.5', True),
                    ('B', '0.33', False),
                    ('C', '0.67', False),
                    ('D', '0.25', False)
                ]
            },
            {
                'subject': math_subj,
                'topic': math_topic_objs["Aniq va aniqmas integrallar"],
                'difficulty': DifficultyLevel.HARD,
                'text': "∫ (3x² + 2x) dx aniqmas integralni hisoblang.",
                'explanation': "Integral formulasi bo'yicha: 3*(x³/3) + 2*(x²/2) + C = x³ + x² + C.",
                'options': [
                    ('A', 'x³ + x² + C', True),
                    ('B', '6x + 2 + C', False),
                    ('C', '3x³ + 2x² + C', False),
                    ('D', 'x³ + 2x + C', False)
                ]
            },
            {
                'subject': math_subj,
                'topic': math_topic_objs["Aylanma jismlar: silindr, konus, shar"],
                'difficulty': DifficultyLevel.MEDIUM,
                'text': "Radiusi 3 sm bo'lgan sharning hajmini hisoblang (π = 3 deb olinsin).",
                'explanation': "Shar hajmi formulasi: V = (4/3)πR³ = (4/3)*3*(27) = 108 sm³.",
                'options': [
                    ('A', '108 sm³', True),
                    ('B', '36 sm³', False),
                    ('C', '72 sm³', False),
                    ('D', '144 sm³', False)
                ]
            },

            # Informatika savollari
            {
                'subject': inf_subj,
                'topic': inf_topic_objs["Python dasturlash tili asoslari"],
                'difficulty': DifficultyLevel.EASY,
                'text': "Python dasturlash tilida quyidagi kod natijasi nima bo'ladi?\n\nprint(type([1, 2, 3]))",
                'explanation': "Kvadrat qavslar ichidagi elementlar ketma-ketligi 'list' (ro'yxat) turiga tegishli.",
                'options': [
                    ('A', "<class 'list'>", True),
                    ('B', "<class 'tuple'>", False),
                    ('C', "<class 'array'>", False),
                    ('D', "<class 'set'>", False)
                ]
            },
            {
                'subject': inf_subj,
                'topic': inf_topic_objs["Python dasturlash tili asoslari"],
                'difficulty': DifficultyLevel.MEDIUM,
                'text': "Python-da `x = [i**2 for i in range(4)]` ifodasi bajarilgandan so'ng x ro'yxati nimaga teng bo'ladi?",
                'explanation': "range(4) [0, 1, 2, 3] sonlarini beradi. Kvadratlari esa [0, 1, 4, 9] bo'ladi.",
                'options': [
                    ('A', '[0, 1, 4, 9]', True),
                    ('B', '[1, 4, 9, 16]', False),
                    ('C', '[0, 1, 2, 3]', False),
                    ('D', '[0, 2, 4, 6]', False)
                ]
            },
            {
                'subject': inf_subj,
                'topic': inf_topic_objs["Ma'lumotlar bazasi va SQL so'rovlar"],
                'difficulty': DifficultyLevel.EASY,
                'text': "SQL tilida jadvaldagi barcha ma'lumotlarni o'qish uchun qaysi kalit so'z ishlatiladi?",
                'explanation': "Jadvaldan ustunlarni tanlab olish uchun SELECT komandasi ishlatiladi: SELECT * FROM jadval.",
                'options': [
                    ('A', 'SELECT', True),
                    ('B', 'GET', False),
                    ('C', 'FETCH', False),
                    ('D', 'RETRIEVE', False)
                ]
            },
            {
                'subject': inf_subj,
                'topic': inf_topic_objs["Kompyuter tarmoqlari va protokollar"],
                'difficulty': DifficultyLevel.MEDIUM,
                'text': "OSI modelining qaysi sathi IP manzillash va marshrutlash (routing) uchun javobgar?",
                'explanation': "Tarmoq sathi (Network layer / 3-sath) paketlarni marshrutlash va IP manzillash vazifasini bajaradi.",
                'options': [
                    ('A', 'Tarmoq sathi (Network layer)', True),
                    ('B', 'Kanal sathi (Data Link layer)', False),
                    ('C', 'Transport sathi (Transport layer)', False),
                    ('D', 'Amaliy sath (Application layer)', False)
                ]
            },

            # Pedagogika savollari
            {
                'subject': ped_subj,
                'topic': ped_topic_objs["Kriterial baholash tizimi"],
                'difficulty': DifficultyLevel.EASY,
                'text': "Formatif (shakllantiruvchi) baholashning asosiy maqsadi nima?",
                'explanation': "Formatif baholash ta'lim jarayonida o'quvchining kuchli va zaif tomonlarini aniqlash, o'rganishni yaxshilash va teskari aloqa (feedback) berish uchun xizmat qiladi.",
                'options': [
                    ('A', 'O\'quvchi o\'zlashtirishini muntazam kuzatish va o\'z vaqtida tuzatishlar kiritish', True),
                    ('B', 'Faqat choraklik yakuniy baho qo\'yish', False),
                    ('C', 'O\'quvchilarni reyting bo\'yicha saralash', False),
                    ('D', 'Imtihondan yiqitish', False)
                ]
            },
            {
                'subject': ped_subj,
                'topic': ped_topic_objs["Interfaol ta'lim metodlari"],
                'difficulty': DifficultyLevel.MEDIUM,
                'text': "Kichik guruhlarda ma'lum bir muammo bo'yicha ko'plab yangi g'oyalarni erkin bildirishga asoslangan metod qanday ataladi?",
                'explanation': "Aqliy hujum (Brainstorming) metodida ishtirokchilar hech qanday tanqidsiz erkin fikr va g'oyalarni o'rtaga tashlaydilar.",
                'options': [
                    ('A', 'Aqliy hujum (Brainstorming)', True),
                    ('B', 'Sinkveyn', False),
                    ('C', 'Klaster', False),
                    ('D', 'B-B-B (Bilar edim, Bildim, Bilmoqchiman)', False)
                ]
            }
        ]

        # Pillow yordamida geometrik shakllar tasvirlarini demo sifatida yaratish
        demo_dir = os.path.join(app.root_path, 'static', 'uploads', 'demo')
        os.makedirs(demo_dir, exist_ok=True)
        from PIL import Image, ImageDraw

        # 1. Uchburchak
        tri_path = os.path.join(demo_dir, 'triangle.png')
        if not os.path.exists(tri_path):
            im_tri = Image.new('RGB', (200, 160), color='#f8fafc')
            d_tri = ImageDraw.Draw(im_tri)
            d_tri.polygon([(30, 140), (170, 140), (30, 30)], fill='#22c55e', outline='#15803d')
            d_tri.rectangle([(30, 125), (45, 140)], outline='#15803d')
            im_tri.save(tri_path)

        # 2. Kvadrat
        sq_path = os.path.join(demo_dir, 'square.png')
        if not os.path.exists(sq_path):
            im_sq = Image.new('RGB', (200, 160), color='#f8fafc')
            d_sq = ImageDraw.Draw(im_sq)
            d_sq.rectangle([(40, 30), (160, 140)], fill='#3b82f6', outline='#1d4ed8')
            im_sq.save(sq_path)

        # 3. Doira
        cir_path = os.path.join(demo_dir, 'circle.png')
        if not os.path.exists(cir_path):
            im_cir = Image.new('RGB', (200, 160), color='#f8fafc')
            d_cir = ImageDraw.Draw(im_cir)
            d_cir.ellipse([(40, 20), (160, 140)], fill='#f59e0b', outline='#b45309')
            im_cir.save(cir_path)

        # 4. Trapetsiya
        trp_path = os.path.join(demo_dir, 'trapezoid.png')
        if not os.path.exists(trp_path):
            im_trp = Image.new('RGB', (200, 160), color='#f8fafc')
            d_trp = ImageDraw.Draw(im_trp)
            d_trp.polygon([(60, 40), (140, 40), (170, 130), (30, 130)], fill='#ec4899', outline='#be185d')
            im_trp.save(trp_path)

        # Geometrik rasm-variantli namunaviy savollarni qo'shish
        plan_topic = math_topic_objs.get("Planimetriya asoslari") or list(math_topic_objs.values())[0]
        sample_questions_data.extend([
            {
                'subject': math_subj,
                'topic': plan_topic,
                'difficulty': DifficultyLevel.EASY,
                'text': "Quyidagi tasvirlardan qaysi biri to'g'ri burchakli uchburchakni ifodalaydi?",
                'explanation': "A variantdagi shaklda katetlar orasidagi burchak 90 gradusga teng, ya'ni to'g'ri burchakli uchburchak tasvirlangan.",
                'options': [
                    ('A', "To'g'ri burchakli uchburchak", '/static/uploads/demo/triangle.png', True),
                    ('B', "To'rtburchak", '/static/uploads/demo/square.png', False),
                    ('C', "Doira", '/static/uploads/demo/circle.png', False),
                    ('D', "Trapetsiya", '/static/uploads/demo/trapezoid.png', False)
                ]
            },
            {
                'subject': math_subj,
                'topic': plan_topic,
                'difficulty': DifficultyLevel.MEDIUM,
                'text': "Berilgan geometrik shakllar orasidan gipotenuzaga ega bo'lganini tanlang:",
                'explanation': "Faqat to'g'ri burchakli uchburchakda to'g'ri burchak qarshisidagi tomon gipotenuza deb ataladi.",
                'options': [
                    ('A', "", '/static/uploads/demo/triangle.png', True),
                    ('B', "", '/static/uploads/demo/square.png', False),
                    ('C', "", '/static/uploads/demo/circle.png', False),
                    ('D', "", '/static/uploads/demo/trapezoid.png', False)
                ]
            }
        ])

        created_questions = []
        from app.models.question import QuestionOptionMedia
        for q_data in sample_questions_data:
            q_hash = Question.calculate_hash(q_data['text'])
            q_obj = Question.query.filter_by(hash=q_hash).first()
            if not q_obj:
                q_obj = Question(
                    subject_id=q_data['subject'].id,
                    topic_id=q_data['topic'].id,
                    question_type=QuestionType.SINGLE_CHOICE,
                    text=q_data['text'],
                    explanation=q_data.get('explanation', ''),
                    difficulty=q_data['difficulty'],
                    source="Attestatsiya namunaviy savollar banki 2026",
                    status='ACTIVE',
                    is_approved=True,
                    version=1,
                    hash=q_hash
                )
                db.session.add(q_obj)
                db.session.flush()

                for opt_item in q_data['options']:
                    opt_key = opt_item[0]
                    opt_text = opt_item[1]
                    if len(opt_item) == 4:
                        opt_img = opt_item[2]
                        is_corr = opt_item[3]
                    else:
                        opt_img = None
                        is_corr = opt_item[2]

                    opt = QuestionOption(
                        question_id=q_obj.id,
                        key=opt_key,
                        text=opt_text,
                        is_correct=is_corr
                    )
                    db.session.add(opt)
                    db.session.flush()

                    if opt_img:
                        db.session.add(QuestionOptionMedia(
                            option_id=opt.id,
                            file_path=opt_img,
                            file_url=opt_img,
                            original_name=f"{opt_key}.png",
                            media_type='IMAGE'
                        ))

            created_questions.append(q_obj)

        db.session.commit()

        # 6. Paketlar (Packages) va Narxlar (Monetizatsiya)
        print("\n[6/7] Tayyorgarlik paketlari yaratilmoqda...")
        packages_data = [
            {
                'name': '1 ta test sinovi',
                'slug': '1-test',
                'description': 'Bilimingizni bir marta sinab ko\'rish va test tizimi bilan tanishish uchun.',
                'price': 10000.0,
                'duration_days': 3,
                'test_limit': 1,
                'is_all_subjects': True,
                'order_num': 1,
                'features': [
                    'Ixtiyoriy fandan 1 ta attestatsiya simulyatsiyasi',
                    'Batafsil natijalar va tahlil',
                    '3 kun davomida faol'
                ]
            },
            {
                'name': '7 kunlik tezkor paket',
                'slug': '7-kunlik-paket',
                'description': 'Attestatsiya oldidan bir haftalik intensiv tayyorgarlik va simulyatsiya.',
                'price': 30000.0,
                'duration_days': 7,
                'test_limit': None,
                'is_all_subjects': True,
                'order_num': 2,
                'features': [
                    'Barcha maktab fanlari bo\'yicha cheksiz testlar',
                    'Attestatsiya simulyatsiyalari',
                    'Xatolar ustida ishlash moduli',
                    'Zaif mavzularni mustahkamlash',
                    '7 kunlik to\'liq kirish'
                ]
            },
            {
                'name': '30 kunlik to\'liq tayyorgarlik',
                'slug': '30-kunlik-paket',
                'description': 'Eng ommabop va to\'liq imkoniyatli paket. Yuqori toifaga tayyorgarlik uchun tavsiya etiladi.',
                'price': 70000.0,
                'duration_days': 30,
                'test_limit': None,
                'is_all_subjects': True,
                'order_num': 3,
                'features': [
                    'Barcha fanlar va mavzular katalogi',
                    'Cheksiz attestatsiya simulyatsiyalari',
                    'Shaxsiy xatolar banki va tahlil',
                    'AI tayyorgarlik ko\'rsatkichi & tavsiyalar',
                    'Telegram bildirishnomalar',
                    '30 kunlik to\'liq kafolatlangan kirish'
                ]
            }
        ]

        package_objs = []
        for p_data in packages_data:
            pkg = Package.query.filter_by(slug=p_data['slug']).first()
            if not pkg:
                pkg = Package(
                    name=p_data['name'],
                    slug=p_data['slug'],
                    description=p_data['description'],
                    price=p_data['price'],
                    duration_days=p_data['duration_days'],
                    test_limit=p_data['test_limit'],
                    is_all_subjects=p_data['is_all_subjects'],
                    features=p_data['features'],
                    order_num=p_data['order_num'],
                    is_active=True
                )
                db.session.add(pkg)
                db.session.flush()
            package_objs.append(pkg)

        db.session.commit()

        # 7. Testlar va Namunaviy Foydalanuvchi Progressi
        print("\n[7/7] Testlar, namunaviy sessiya va tayyorgarlik statistikasi yaratilmoqda...")
        math_sim_test = Test.query.filter_by(subject_id=math_subj.id, test_type=TestType.SIMULYATSIYA).first()
        if not math_sim_test:
            math_sim_test = Test(
                title="Matematika attestatsiya simulyatsiyasi",
                test_type=TestType.SIMULYATSIYA,
                subject_id=math_subj.id,
                duration_minutes=90,
                passing_score=60.0,
                total_questions=10,
                shuffle_questions=True,
                shuffle_options=True,
                is_free=False,
                status='ACTIVE'
            )
            db.session.add(math_sim_test)

        math_free_test = Test.query.filter_by(subject_id=math_subj.id, is_free=True).first()
        if not math_free_test:
            math_free_test = Test(
                title="Matematika - Namunaviy bepul test",
                test_type=TestType.FAN,
                subject_id=math_subj.id,
                duration_minutes=30,
                passing_score=60.0,
                total_questions=5,
                shuffle_questions=True,
                shuffle_options=True,
                is_free=True,
                status='ACTIVE'
            )
            db.session.add(math_free_test)

        inf_test = Test.query.filter_by(subject_id=inf_subj.id).first()
        if not inf_test:
            inf_test = Test(
                title="Informatika - Namunaviy test",
                test_type=TestType.FAN,
                subject_id=inf_subj.id,
                duration_minutes=45,
                passing_score=60.0,
                total_questions=5,
                shuffle_questions=True,
                shuffle_options=True,
                is_free=True,
                status='ACTIVE'
            )
            db.session.add(inf_test)

        db.session.commit()

        # O'qituvchiga faol paket va to'lov biriktirish (30 kunlik)
        ent = Entitlement.query.filter_by(user_id=teacher.id, is_active=True).first()
        if not ent:
            pkg_30 = package_objs[2]
            order = Order(
                order_number=Order.generate_order_number(),
                user_id=teacher.id,
                package_id=pkg_30.id,
                amount=pkg_30.price,
                status='PAID'
            )
            db.session.add(order)
            db.session.flush()

            payment = Payment(
                order_id=order.id,
                user_id=teacher.id,
                amount=pkg_30.price,
                status='CONFIRMED',
                payment_method='CLICK',
                click_trans_id='CLK_DEMO_998877'
            )
            db.session.add(payment)
            db.session.flush()

            ent = Entitlement(
                user_id=teacher.id,
                package_id=pkg_30.id,
                order_id=order.id,
                starts_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=pkg_30.duration_days),
                tests_remaining=pkg_30.test_limit,
                is_active=True
            )
            db.session.add(ent)
            db.session.commit()

        # O'qituvchi uchun sinov natijasi, xatolari va zaif mavzulari
        sample_result = Result.query.filter_by(user_id=teacher.id).first()
        if not sample_result and len(created_questions) >= 5:
            # Namunaviy natija: 10 ta savoldan 7 tasi to'g'ri, 3 tasi xato (70%)
            import uuid
            sess = TestSession(
                id=str(uuid.uuid4()),
                user_id=teacher.id,
                test_id=math_sim_test.id,
                status=SessionStatus.SUBMITTED,
                started_at=datetime.utcnow() - timedelta(minutes=45),
                expires_at=datetime.utcnow() + timedelta(minutes=45),
                finished_at=datetime.utcnow() - timedelta(minutes=5)
            )
            db.session.add(sess)
            db.session.flush()

            res = Result(
                session_id=sess.id,
                user_id=teacher.id,
                test_id=math_sim_test.id,
                total_questions=10,
                correct_answers=7,
                incorrect_answers=3,
                unanswered=0,
                score=70.0,
                percentage=70.0,
                is_passed=True,
                completion_time_seconds=2400,
                ai_recommendation="Siz algebra va trigonometriya bo'limlaridan ajoyib natija ko'rsatdingiz. Ammo stereometriya va ehtimollar nazariyasi bo'yicha ayrim formulalarni qayta ko'rib chiqish tavsiya etiladi."
            )
            db.session.add(res)
            db.session.flush()

            # ResultDetail
            first_topic = list(math_topic_objs.values())[0] if math_topic_objs else None
            rd = ResultDetail(
                result_id=res.id,
                subject_id=math_subj.id,
                topic_id=first_topic.id if first_topic else None,
                total_topic_questions=10,
                correct_topic_questions=7,
                topic_percentage=70.0
            )
            db.session.add(rd)

            # Xato qilingan 3 ta savol (UserQuestionStat)
            for i, q in enumerate(created_questions[:3]):
                uqs = UserQuestionStat(
                    user_id=teacher.id,
                    question_id=q.id,
                    attempts_count=2,
                    correct_count=0,
                    incorrect_count=2,
                    is_last_correct=False
                )
                db.session.add(uqs)

            # Zaif mavzu statistikasi (UserTopicStat - aniqlik 40% < 60%)
            weak_topic = math_topic_objs["Ehtimollar nazariyasi elementlari"]
            uts = UserTopicStat(
                user_id=teacher.id,
                topic_id=weak_topic.id,
                total_answered=5,
                correct_answered=2,
                accuracy_percentage=40.0
            )
            db.session.add(uts)

            db.session.commit()

        print("\n" + "=" * 60)
        print("Muvaffaqiyatli yakunlandi!")
        print(f"1. Admin hisobi:       admin@example.com / Admin123!")
        print(f"2. O'qituvchi hisobi:  user@example.com / User123!")
        print(f"3. Fanlar soni:        {Subject.query.count()} ta fan")
        print(f"4. Savollar soni:      {Question.query.count()} ta savol")
        print(f"5. Paketlar soni:      {Package.query.count()} ta paket")
        print(f"6. O'qituvchi obunasi: 30 kunlik faol to'liq paket")
        print("=" * 60)

if __name__ == '__main__':
    seed()
