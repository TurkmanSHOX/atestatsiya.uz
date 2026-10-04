import os
from datetime import datetime, date, timedelta
from app import create_app
from app.extensions import db
from app.models.user import User, UserRole
from app.models.attestation import Attestation, AttestationStatus, AttestationRegistration, RegistrationStep
from app.models.payment import Payment, PaymentStatus, PaymentMethod, PaymentReceipt
from app.models.question import Subject, Topic, Question, QuestionOption, QuestionType, DifficultyLevel
from app.models.test import Test, TestBlueprint, TestBlueprintRule
from app.models.system import Setting
from app.services.test_engine_service import TestEngineService
from app.services.certificate_service import CertificateService

app = create_app()

def seed():
    with app.app_context():
        print("[1/6] Ma'lumotlar bazasi jadvallari tekshirilmoqda...")
        db.create_all()

        # 1. Sozlamalar
        Setting.set_val('site_name', 'Attestatsiya.uz')
        Setting.set_val('support_phone', '+998 71 200 00 00')
        Setting.set_val('support_email', 'info@attestatsiya.uz')

        # 2. Foydalanuvchilar (Admin va Foydalanuvchi - FAQAT 2 TA ROL)
        print("[2/6] Foydalanuvchilar (Admin va Nomzod) yaratilmoqda...")
        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin:
            admin = User(
                role=UserRole.ADMIN,
                email='admin@example.com',
                phone='+998901112233',
                first_name='Administrator',
                last_name='Boshqaruvchi',
                organization='Davlat Attestatsiya Markazi',
                position='Bosh Administrator',
                is_active=True,
                is_verified=True
            )
            admin.set_password('Admin123!')
            db.session.add(admin)

        candidate = User.query.filter_by(email='user@example.com').first()
        if not candidate:
            candidate = User(
                role=UserRole.FOYDALANUVCHI,
                email='user@example.com',
                phone='+998909998877',
                first_name='Anvar',
                last_name='Qodirov',
                middle_name='Ergash o\'g\'li',
                birth_date=date(1988, 5, 14),
                gender='ERKAK',
                region='Toshkent shahri',
                organization='154-umumiy o\'rta ta\'lim maktabi',
                position='Oliy toifali o\'qituvchi',
                specialty='Pedagogika va metodika',
                experience_years=12,
                is_active=True,
                is_verified=True
            )
            candidate.set_password('User123!')
            db.session.add(candidate)

        db.session.commit()

        # 3. Fanlar va Mavzular
        print("[3/6] Fanlar va mavzular katalogi yaratilmoqda...")
        subjects_data = [
            {
                'name': 'Pedagogika nazariyasi va amaliyoti',
                'code': 'PED',
                'topics': ['Ta\'lim tamoyillari', 'Didaktika', 'Tarbiyaviy ishlar metodikasi']
            },
            {
                'name': 'Umumiy va yosh davrlari psixologiyasi',
                'code': 'PSY',
                'topics': ['O\'quvchi shaxsining rivojlanishi', 'Kognitiv jarayonlar', 'Muloqot psixologiyasi']
            },
            {
                'name': 'Zamonaviy ta\'lim texnologiyalari',
                'code': 'MET',
                'topics': ['Interfaol metodlar', 'Baholash mezonlari (Kriterial)', 'Raqamli ta\'lim']
            },
            {
                'name': 'Mutaxassislik fani va huquqiy savodxonlik',
                'code': 'MUT',
                'topics': ['Ta\'lim to\'g\'risidagi qonun hujjatlari', 'Milliy o\'quv dasturi']
            }
        ]

        subject_map = {}
        topic_map = {}

        for s_data in subjects_data:
            subj = Subject.query.filter_by(name=s_data['name']).first()
            if not subj:
                subj = Subject(name=s_data['name'], code=s_data['code'])
                db.session.add(subj)
                db.session.flush()
            subject_map[s_data['code']] = subj

            for t_name in s_data['topics']:
                top = Topic.query.filter_by(subject_id=subj.id, name=t_name).first()
                if not top:
                    top = Topic(subject_id=subj.id, name=t_name)
                    db.session.add(top)
                    db.session.flush()
                topic_map[(s_data['code'], t_name)] = top

        db.session.commit()

        # 4. Attestatsiya yaratish: "Pedagog kadrlar attestatsiyasi"
        print("[4/6] Demo Attestatsiya dasturi yaratilmoqda...")
        attestation = Attestation.query.filter_by(slug='pedagog-kadrlar-attestatsiyasi').first()
        if not attestation:
            attestation = Attestation(
                title='Pedagog kadrlar attestatsiyasi',
                slug='pedagog-kadrlar-attestatsiyasi',
                short_description='Umumiy o\'rta ta\'lim, maktabgacha va professional ta\'lim muassasalari pedagog xodimlari uchun toifa berish sinovi.',
                full_description='Mazkur attestatsiya O\'zbekiston Respublikasi Vazirlar Mahkamasining tegishli qarorlari asosida pedagog xodimlarning kasbiy mahorati, zamonaviy metodik kompetensiyalari va psixologik tayyorgarligini baholash uchun mo\'ljallangan.\n\nSinov 40 ta test savolidan iborat bo\'lib, 90 daqiqa davom etadi. O\'tish bali kamida 70% ni tashkil qiladi.',
                field_name='Pedagogika',
                price=340000.00,
                currency='UZS',
                questions_count=40,
                duration_minutes=90,
                passing_score=70.00,
                max_score=100.00,
                max_attempts=2,
                issue_certificate=True,
                certificate_validity_months=36,
                status=AttestationStatus.ACTIVE
            )
            db.session.add(attestation)
            db.session.flush()

        # 5. Savollar banki: 40 ta professional savol (Pedagogika, Psixologiya, Metodika, Mutaxassislik)
        print("[5/6] 40 ta professional test savollari savollar bankiga yuklanmoqda...")
        raw_questions = [
            # Pedagogika (10 ta)
            ("Didaktikaning 'Ko'rgazmalilik' tamoyili qaysi pedagogik asosga tayanadi?", "PED", "Ta'lim tamoyillari", "MEDIUM", 1.0, [
                ("Bilimlarni faqat kitobdan yodlatishga", False),
                ("Hissiy idrok va real obyektlar orqali tushunchalarni mustahkamlashga", True),
                ("Faqat texnik vositalardan foydalanishga", False),
                ("Mustaqil topshiriqlarni cheklashga", False)
            ]),
            ("Pedagogik jarayonda tarbiyaning asosiy maqsadi nima?", "PED", "Tarbiyaviy ishlar metodikasi", "EASY", 1.0, [
                ("Shaxsni har tomonlama va uyg'un kamol toptirish", True),
                ("Faqat o'quv dasturidagi bilimlarni to'liq o'zlashtirish", False),
                ("Maktab intizomiga so'zsiz bo'ysundirish", False),
                ("Yil oxirida imtihonlarni yaxshi topshirtirish", False)
            ]),
            ("Ta'lim jarayonida tizimlilik va izchillik tamoyili nimani anglatadi?", "PED", "Didaktika", "MEDIUM", 1.0, [
                ("Mavzularni ixtiyoriy tartibda o'tishni", False),
                ("Bilimlarning mantiqiy bog'liqlikda va oddiydan murakkabga qarab berilishini", True),
                ("Faqat amaliy mashg'ulotlar o'tkazishni", False),
                ("Dars vaqtini qisqartirishni", False)
            ]),
            ("Insonparvarlik (Gumanizm) tamoyili pedagogikada nimaga asoslanadi?", "PED", "Ta'lim tamoyillari", "EASY", 1.0, [
                ("O'quvchi shaxsini oliy qadriyat deb bilish va hurmat qilishga", True),
                ("Qat'iy intizomiy jazolarga", False),
                ("Hamma o'quvchiga bir xil talab qo'yishga", False),
                ("Baholashni bekor qilishga", False)
            ]),
            ("O'qitish metodlarining manbasiga ko'ra tasnifida qaysi guruh mavjud?", "PED", "Didaktika", "MEDIUM", 1.0, [
                ("Og'zaki, ko'rgazmali va amaliy metodlar", True),
                ("Faqat yozma va og'zaki metodlar", False),
                ("Faqat jismoniy mashqlar", False),
                ("Individual va guruhli metodlar", False)
            ]),
            ("Pedagogik texnologiyaning an'anaviy metodikadan asosiy farqi nimada?", "PED", "Didaktika", "HARD", 1.0, [
                ("Kafolatlangan yakuniy natijaga yo'naltirilganligida", True),
                ("Faqat kompyuterdan foydalanishida", False),
                ("Vaqt chegarasi yo'qligida", False),
                ("O'qituvchining faoliyatini kamaytirishida", False)
            ]),
            ("Darsning qaysi bosqichida o'quvchilarning yangi mavzuni qabul qilishga tayyorgarligi ta'minlanadi?", "PED", "Didaktika", "EASY", 1.0, [
                ("Tashkiliy va motivatsion bosqichda", True),
                ("Uy vazifasini berish bosqichida", False),
                ("Yakuniy baholash bosqichida", False),
                ("Dars tahlilida", False)
            ]),
            ("Tarbiyaning qaysi metodi shaxs ongini shakllantirishga xizmat qiladi?", "PED", "Tarbiyaviy ishlar metodikasi", "MEDIUM", 1.0, [
                ("Suhbat, ma'ruza, tushuntirish va o'rnak ko'rsatish", True),
                ("Jazo va majburlash", False),
                ("Musobaqa uyushtirish", False),
                ("Faqat mustaqil ish", False)
            ]),
            ("Inklyuziv ta'limning tub mohiyati nimadan iborat?", "PED", "Ta'lim tamoyillari", "MEDIUM", 1.0, [
                ("Alohida ta'lim ehtiyojlari bo'lgan bolalarni umumiy sinfda birga o'qitish", True),
                ("Faqat iqtidorli bolalarni saralab o'qitish", False),
                ("Maxsus maktab-internatlarni ko'paytirish", False),
                ("Masofaviy ta'limni kengaytirish", False)
            ]),
            ("O'qituvchining kasbiy kompetentligiga qaysi sifatlar kiradi?", "PED", "Didaktika", "HARD", 1.0, [
                ("Maxsus, pedagogik-psixologik, metodik va kommunikativ bilim va ko'nikmalar", True),
                ("Faqat o'z fanini mukammal bilish", False),
                ("Faqat qat'iy intizom o'rnatish qobiliyati", False),
                ("Darslik yozish mahorati", False)
            ]),

            # Psixologiya (10 ta)
            ("O'smirlik davrining (11-15 yosh) yetakchi faoliyat turi qaysi?", "PSY", "O'quvchi shaxsining rivojlanishi", "MEDIUM", 1.0, [
                ("Tengdoshlar bilan shaxsiy-intim muloqot", True),
                ("O'quv faoliyati", False),
                ("Syujetli-rolli o'yinlar", False),
                ("Mehnat faoliyati", False)
            ]),
            ("Temperamentning qaysi turi asab tizimining kuchli, muvozanatlashgan va harakatchan tipiga to'g'ri keladi?", "PSY", "O'quvchi shaxsining rivojlanishi", "MEDIUM", 1.0, [
                ("Sangvinik", True),
                ("Xolerik", False),
                ("Flegmatik", False),
                ("Melanxolik", False)
            ]),
            ("O'quvchida diqqatning qaysi turi iroda kuchi sarflamasdan, qiziqish asosida yuzaga keladi?", "PSY", "Kognitiv jarayonlar", "EASY", 1.0, [
                ("Ixtiyorsiz diqqat", True),
                ("Ixtiyoriy diqqat", False),
                ("Ixtiyoriydan so'nggi diqqat", False),
                ("Mexanik diqqat", False)
            ]),
            ("L.S.Vigotskiyning 'Yaqin rivojlanish zonasi' nazariyasi nimani ifodalaydi?", "PSY", "O'quvchi shaxsining rivojlanishi", "HARD", 1.0, [
                ("Bola kattalar yordamida bajara oladigan, lekin mustaqil hali eplay olmaydigan daraja", True),
                ("Bolaning to'liq mustaqil bajara oladigan bilimlari chegarasi", False),
                ("Bolaning kelajakdagi kasbiy faoliyati", False),
                ("Miya yarim sharlarining rivojlanish darajasi", False)
            ]),
            ("Konfliktli vaziyatda o'z manfaatidan kechib, boshqa tomonning talabini qabul qilish qanday strategiya deyiladi?", "PSY", "Muloqot psixologiyasi", "MEDIUM", 1.0, [
                ("Moslashish (Yondashuv)", True),
                ("Raqobat", False),
                ("Murosasozlik (Kompromiss)", False),
                ("Hamkorlik", False)
            ]),
            ("Xotiraning qaysi turi ma'lumotlarni mantiqiy tushunib, tahlil qilish orqali esda saqlashga asoslanadi?", "PSY", "Kognitiv jarayonlar", "EASY", 1.0, [
                ("Mantiqiy (ma'noli) xotira", True),
                ("Mexanik xotira", False),
                ("Hissiy xotira", False),
                ("Dvigatel xotira", False)
            ]),
            ("O'quvchida ichki motivatsiyani oshirishning eng samarali usuli nima?", "PSY", "O'quvchi shaxsining rivojlanishi", "MEDIUM", 1.0, [
                ("Topshiriqni hayotiy tajriba bilan bog'lash va erishilgan yutuqni e'tirof etish", True),
                ("Yomon baho qo'yish bilan qo'rqitish", False),
                ("Faqat moddiy rag'batlantirish", False),
                ("Uyga ko'p topshiriq berish", False)
            ]),
            ("Kreativlik (ijodiy fikrlash) psixologiyada qaysi tafakkur turiga ko'proq bog'liq?", "PSY", "Kognitiv jarayonlar", "HARD", 1.0, [
                ("Divergent fikrlash (nostandart yechimlar izlash)", True),
                ("Konvergent fikrlash", False),
                ("Reproduktiv tafakkur", False),
                ("Ko'rgazmali-harakatli tafakkur", False)
            ]),
            ("O'qituvchining empatiya qobiliyati deganda nima tushuniladi?", "PSY", "Muloqot psixologiyasi", "EASY", 1.0, [
                ("Boshqa insonning his-tuyg'ularini tushunish va uning holatiga kira olish", True),
                ("Barchaga o'z fikrini qat'iy o'tkazish", False),
                ("O'quvchilarga doimiy ravishda yuqori baho qo'yish", False),
                ("O'z hissiyotlarini jilovlay olmaslik", False)
            ]),
            ("Emotsional so'nish (Professional burnout) sindromining asosiy belgilaridan biri qaysi?", "PSY", "Muloqot psixologiyasi", "MEDIUM", 1.0, [
                ("Surunkali charchoq, ishga qiziqishning so'nishi va hissiy loqaydlik", True),
                ("Haddan tashqari yuqori energiya va tashabbuskorlik", False),
                ("Yangi metodlarni o'rganishga ishtiyoq", False),
                ("Hamma bilan samimiy muloqot o'rnatish", False)
            ]),

            # Zamonaviy metodika va ta'lim texnologiyalari (10 ta)
            ("Blum taksonomiyasining bilish darajalari ierarxiyasida eng yuqori pog'ona qaysi?", "MET", "Baholash mezonlari (Kriterial)", "HARD", 1.0, [
                ("Yaratish (Ijod qilish)", True),
                ("Tahlil", False),
                ("Qo'llash", False),
                ("Eslab qolish", False)
            ]),
            ("Formatik (shakllantiruvchi) baholashning asosiy vazifasi nima?", "MET", "Baholash mezonlari (Kriterial)", "MEDIUM", 1.0, [
                ("O'quv jarayonini yaxshilash uchun doimiy qayta aloqa (feedback) berish", True),
                ("Choraklik yakuniy bahosini chiqarish", False),
                ("O'quvchilarni bir-biri bilan taqqoslash", False),
                ("Jazolash vositasi sifatida qo'llash", False)
            ]),
            ("'Klaster' interfaol metodining maqsadi nimadan iborat?", "MET", "Interfaol metodlar", "EASY", 1.0, [
                ("Mavzuga oid tushuncha va g'oyalarni tarmoqlash, tizimlashtirish", True),
                ("O'quvchilar o'rtasida munozara tashkil etish", False),
                ("Faqat test savollarini tuzish", False),
                ("Matnni tarjima qilish", False)
            ]),
            ("'Aql charxi' (Brainstorming) metodida qaysi qoidaga qat'iy amal qilinadi?", "MET", "Interfaol metodlar", "MEDIUM", 1.0, [
                ("Fikr bildirish vaqtida g'oyalarni tanqid qilish va baholash taqiqlanadi", True),
                ("Har bir fikr darhol tahlil qilinib baholanadi", False),
                ("Faqat to'g'ri deb topilgan 1 ta fikr yoziladi", False),
                ("Faqat a'lochi o'quvchilar gapiradi", False)
            ]),
            ("Summativ baholash qachon amalga oshiriladi?", "MET", "Baholash mezonlari (Kriterial)", "EASY", 1.0, [
                ("Bo'lim, bob yoki chorak yakunida bilimlarni umumiy xulosalash uchun", True),
                ("Har bir dars boshida yangi mavzu kiritilishidan oldin", False),
                ("Faqat dars o'rtasida og'zaki so'rovda", False),
                ("Uy vazifasini berish vaqtida", False)
            ]),
            ("Loyiha ta'limi (PBL) qanday tamoyilga asoslanadi?", "MET", "Interfaol metodlar", "HARD", 1.0, [
                ("Haqiqiy hayotiy muammoni tadqiq etish va aniq mahsulot/yechim yaratishga", True),
                ("Faqat tayyor konspektni yodlab berishga", False),
                ("Laboratoriya xavfsizligi qoidalariga", False),
                ("Guruhsiz yakka tartibda ishlashga", False)
            ]),
            ("Raqamli ta'limda LMS (Learning Management System) nima?", "MET", "Raqamli ta'lim", "MEDIUM", 1.0, [
                ("O'quv jarayonini boshqarish, kontent yetkazish va monitoring qilish platformasi", True),
                ("Faqat rasm tahrirlash dasturi", False),
                ("Kompyuter operatsion tizimi", False),
                ("Interfaol doskaning elektron ruchkasi", False)
            ]),
            ("'Flipped Classroom' (Teskari sinf) texnologiyasida o'quvchilar yangi mavzuni qachon o'rganadi?", "MET", "Raqamli ta'lim", "MEDIUM", 1.0, [
                ("Darsdan oldin uyda (video/materiallar orqali), sinfda esa amaliy qo'llaydi", True),
                ("Faqat sinfda o'qituvchi ma'ruzasi orqali", False),
                ("Imtihon paytida mustaqil qidirib", False),
                ("Faqat ta'til vaqtida", False)
            ]),
            ("Rubrika (Baholash shkalasi) o'qituvchi va o'quvchiga nima beradi?", "MET", "Baholash mezonlari (Kriterial)", "MEDIUM", 1.0, [
                ("Baholashning shaffof, aniq mezonlari va darajalarini ko'rsatadi", True),
                ("Baholash vaqtini ikki barobar uzaytiradi", False),
                ("Faqat yozma ishlarni cheklaydi", False),
                ("O'quvchilar bahosini sir saqlashga xizmat qiladi", False)
            ]),
            ("'Zigzag' (Jigsaw) metodi qaysi vazifani bajarishga yo'naltirilgan?", "MET", "Interfaol metodlar", "HARD", 1.0, [
                ("Katta hajmdagi matnni guruh a'zolari o'rtasida bo'lib o'rganish va bir-biriga o'rgatish", True),
                ("Tezkor hisoblash ko'nikmasini rivojlantirish", False),
                ("Lug'at ustida alohida ishlash", False),
                ("Xatolarni mustaqil tahrirlash", False)
            ]),

            # Mutaxassislik fani va qonunchilik (10 ta)
            ("O'zbekiston Respublikasining 'Ta'lim to'g'risida'gi yangi tahrirdagi Qonuni qachon qabul qilingan?", "MUT", "Ta'lim to'g'risidagi qonun hujjatlari", "MEDIUM", 1.0, [
                ("2020-yil 23-sentabrda", True),
                ("2018-yil 15-mayda", False),
                ("2022-yil 1-sentabrda", False),
                ("1997-yil 29-avgustda", False)
            ]),
            ("'Ta'lim to'g'risida'gi Qonunga binoan O'zbekistonda ta'lim turlari nechta?", "MUT", "Ta'lim to'g'risidagi qonun hujjatlari", "HARD", 1.0, [
                ("6 ta (Maktabgacha, Umumiy o'rta va o'rta maxsus, Professional, Oliy, Oliy ta'limdan keyingi, Kadrlarni qayta tayyorlash va ularning malakasini oshirish)", True),
                ("3 ta (Maktab, Kollej, Institut)", False),
                ("4 ta", False),
                ("8 ta", False)
            ]),
            ("Pedagog xodimning kasbiy etika kodeksi nimani tartibga soladi?", "MUT", "Ta'lim to'g'risidagi qonun hujjatlari", "EASY", 1.0, [
                ("Pedagogning kasbiy faoliyatidagi axloqiy me'yorlari va xulq-atvor qoidalarini", True),
                ("Faqat oylik maoshini hisoblash tartibini", False),
                ("Dars soatlari taqsimotini", False),
                ("Xizmat safarlari jadvalini", False)
            ]),
            ("Milliy o'quv dasturining bosh g'oyasi nima?", "MUT", "Milliy o'quv dasturi", "MEDIUM", 1.0, [
                ("O'quvchida hayotiy ko'nikma va kompetensiyalarni shakllantirish (amaliyotga yo'naltirilganlik)", True),
                ("Faqat nazariy ma'lumotlarni yod oldirish", False),
                ("Darsliklar sonini kamaytirish", False),
                ("Faqat ixtisoslashgan fanlarni o'qitish", False)
            ]),
            ("STEAM ta'lim yondashuvi qaysi yo'nalishlarni o'z ichiga oladi?", "MUT", "Milliy o'quv dasturi", "MEDIUM", 1.0, [
                ("Fan (Science), Texnologiya (Technology), Muhandislik (Engineering), San'at (Art) va Matematika (Math)", True),
                ("Faqat Tabiiy fanlar va Tarix", False),
                ("Faqat Til va adabiyot", False),
                ("Jismoniy tarbiya va Chaqiruvga qadar tayyorgarlik", False)
            ]),
            ("O'qituvchining ish vaqtidan tashqari ruxsatsiz majburiy mehnatga jalb etilishi qonunan qanday baholanadi?", "MUT", "Ta'lim to'g'risidagi qonun hujjatlari", "EASY", 1.0, [
                ("Qat'iyan taqiqlanadi va qonuniy javobgarlikka sabab bo'ladi", True),
                ("Maktab ma'muriyati buyrug'i bilan ruxsat etiladi", False),
                ("Faqat ta'til vaqtida mumkin", False),
                ("Ota-onalar qo'mitasi roziligi bilan ruxsat beriladi", False)
            ]),
            ("PISA xalqaro baholash dasturi 15 yoshli o'quvchilarning qaysi savodxonligini baholaydi?", "MUT", "Milliy o'quv dasturi", "HARD", 1.0, [
                ("O'qish, matematika va tabiiy fanlar savodxonligini", True),
                ("Faqat chet tili grammatikasini", False),
                ("Faqat tarixiy sanalarni eslab qolish darajasini", False),
                ("Jismoniy chidamliligini", False)
            ]),
            ("PIRLS xalqaro baholash dasturi qaysi sinf o'quvchilari uchun mo'ljallangan?", "MUT", "Milliy o'quv dasturi", "MEDIUM", 1.0, [
                ("4-sinf o'quvchilarining matnni o'qish va tushunish darajasini baholaydi", True),
                ("11-sinf bitiruvchilari uchun", False),
                ("Oliy o'quv yurti talabalari uchun", False),
                ("Maktabgacha ta'lim tarbiyalanuvchilari uchun", False)
            ]),
            ("Pedagog xodim qachon navbatdagi majburiy attestatsiyadan o'tadi?", "MUT", "Ta'lim to'g'risidagi qonun hujjatlari", "EASY", 1.0, [
                ("Har 5 yilda bir marta", True),
                ("Har yili", False),
                ("Har 10 yilda bir marta", False),
                ("Faqat ish joyini almashtirganda", False)
            ]),
            ("O'zbekistonda pedagoglarga malaka toifasini berish bo'yicha eng yuqori toifa qaysi?", "MUT", "Ta'lim to'g'risidagi qonun hujjatlari", "EASY", 1.0, [
                ("Oliy toifa (bosh o'qituvchi)", True),
                ("Birinchi toifa (yetakchi o'qituvchi)", False),
                ("Ikkinchi toifa (katta o'qituvchi)", False),
                ("Mutaxassis", False)
            ])
        ]

        for q_tuple in raw_questions:
            q_text, s_code, t_name, diff, pts, opts = q_tuple
            q_hash = Question.calculate_hash(q_text)

            existing = Question.query.filter_by(hash=q_hash).first()
            if not existing:
                subj = subject_map[s_code]
                top = topic_map[(s_code, t_name)]

                q = Question(
                    subject_id=subj.id,
                    topic_id=top.id,
                    question_type=QuestionType.SINGLE_CHOICE,
                    text=q_text,
                    difficulty=diff,
                    points=pts,
                    status='ACTIVE',
                    hash=q_hash
                )
                db.session.add(q)
                db.session.flush()

                for idx, (opt_text, is_corr) in enumerate(opts):
                    o = QuestionOption(
                        question_id=q.id,
                        option_key=chr(65 + idx),
                        text=opt_text,
                        is_correct=is_corr,
                        order_index=idx
                    )
                    db.session.add(o)

        db.session.commit()

        # 6. Test va Test Blueprint yaratish
        print("[6/6] Test va Blueprint kvotalari sozlanmoqda...")
        test = Test.query.filter_by(attestation_id=attestation.id).first()
        if not test:
            test = Test(
                attestation_id=attestation.id,
                title='Pedagog kadrlar malaka attestatsiyasi testi',
                duration_minutes=90,
                passing_score=70.00,
                shuffle_questions=True,
                shuffle_options=True,
                proctoring_enabled=True,
                status='ACTIVE'
            )
            db.session.add(test)
            db.session.flush()

            blueprint = TestBlueprint(
                test_id=test.id,
                total_questions=40
            )
            db.session.add(blueprint)
            db.session.flush()

            # 4 ta blok bo'yicha 10 tadan savol kvotasi (Jami: 40 ta)
            for s_code in ['PED', 'PSY', 'MET', 'MUT']:
                rule = TestBlueprintRule(
                    blueprint_id=blueprint.id,
                    subject_id=subject_map[s_code].id,
                    difficulty='ANY',
                    questions_count=10
                )
                db.session.add(rule)

            db.session.commit()

        # 7. Demo arizani tasdiqlangan holatga keltirish (Test topshirishga tayyor)
        reg = AttestationRegistration.query.filter_by(user_id=candidate.id, attestation_id=attestation.id).first()
        if not reg:
            reg = AttestationRegistration(
                registration_number='REG-2026-DEMO01',
                user_id=candidate.id,
                attestation_id=attestation.id,
                step=RegistrationStep.EXAM_READY,
                reviewed_by=admin.id,
                reviewed_at=datetime.utcnow()
            )
            db.session.add(reg)
            db.session.flush()

            # To'lov
            payment = Payment(
                registration_id=reg.id,
                user_id=candidate.id,
                amount=attestation.price,
                currency='UZS',
                payment_method=PaymentMethod.CARD_MANUAL,
                transaction_id='TX-DEMO-PAY001',
                status=PaymentStatus.PAID,
                confirmed_by=admin.id,
                confirmed_at=datetime.utcnow()
            )
            db.session.add(payment)
            db.session.flush()

            receipt = PaymentReceipt(
                payment_id=payment.id,
                file_path='uploads/receipts/demo_receipt.png',
                file_name='kvitansiya_340000.png',
                mime_type='image/png'
            )
            db.session.add(receipt)
            db.session.commit()

        print("\n=======================================================")
        print(" BARCHA MA'LUMOTLAR MUVAFFAQIYATLI YARATILDI!")
        print("=======================================================")
        print("1. Admin hisobi:")
        print("   Email:    admin@example.com")
        print("   Parol:    Admin123!")
        print("2. Nomzod (User) hisobi:")
        print("   Email:    user@example.com")
        print("   Parol:    User123!")
        print("3. Attestatsiya:")
        print("   Nomi:     Pedagog kadrlar attestatsiyasi")
        print("   Savollar: 40 ta (Pedagogika: 10, Psixologiya: 10, Metodika: 10, Qonunchilik: 10)")
        print("   Vaqt:     90 daqiqa")
        print("   O'tish:   70%")
        print("=======================================================\n")

if __name__ == '__main__':
    seed()
