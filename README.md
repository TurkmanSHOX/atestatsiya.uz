# ATTESTATSIYA.UZ 2.0 — Maktab O'qituvchilari Uchun Professional Attestatsiyaga Tayyorlov Platformasi

> **MUHIM ESLATMA:** Mazkur platforma rasmiy davlat attestatsiyasi o'tkazuvchi organ yoki davlat sertifikati beruvchi muassasa EMAS. Ushbu tizim — O'zbekiston maktab pedagoglari uchun attestatsiya imtihonlariga mustaqil, tizimli va samarali tayyorgarlik ko'rishga mo'ljallangan mustaqil, pullik onlayn o'quv-mashg'ulot web-platformasidir.

---

## 1. Platformaning Asosiy Maqsadi va Imkoniyatlari

Platforma maktab o'qituvchilariga o'z mutaxassislik fanlari bo'yicha bilimlarini mustahkamlash, attestatsiya imtihoni formati va vaqtiga ko'nikish, zaif mavzularni aniqlash va xatolar ustida ishlash imkonini beradi.

### Asosiy Imkoniyatlar:
- **Faqat 2 ta Rol:** `ADMIN` va `FOYDALANUVCHI` (O'qituvchi / Nomzod).
- **26+ Maktab Fani:** Matematika, Informatika, Fizika, Kimyo, Biologiya, Geografiya, Tarix, Ona tili va adabiyoti, Chet tillari, Boshlang'ich ta'lim, Pedagogika va barcha maktab fanlari.
- **Ko'p Pog'onali Tuzilma:** `Fan` ➔ `Bo'lim` ➔ `Mavzu` ➔ `Savol` ➔ `Javob variantlari`.
- **7 Xil Test Rejimi:**
  1. **Mavzu bo'yicha test** — aniq bir mavzuni chuqur o'zlashtirish.
  2. **Fan bo'yicha test** — butun fan dasturi bo'yicha nazorat testi.
  3. **Attestatsiya simulyatsiyasi** — haqiqiy attestatsiya formati (50 ta savol, 90 daqiqa, 20 oson / 20 o'rta / 10 qiyin savollar nisbatida).
  4. **Aralash test** — bir nechta fan va bo'limlardan integrallashgan test.
  5. **Xatolarim ustida ishlash** — foydalanuvchi ilgari xato ishlagan barcha savollardan avtomatik test tuzish.
  6. **Zaif mavzularni mustahkamlash** — o'zlashtirish ko'rsatkichi 60% dan past bo'lgan mavzulardan maqsadli test.
  7. **Tasodifiy test** — erkin sinov mashg'uloti.
- **Shaxsiy Tahlil va AI Tavsiyalar:**
  - **Tayyorgarlik indeksi (Readiness Score):** 0% dan 100% gacha dinamik hisoblanadigan pedagogik tayyorgarlik darajasi.
  - **Zaif mavzular xaritasi:** past natija qayd etilgan mavzular ro'yxati va foizlari.
  - **AI pedagogik xulosasi:** yakunlangan testlar bo'yicha sun'iy intellekt tavsiyalari.
- **Pullik Obunalar va Click Integratsiyasi:**
  - Hamyonbop paketlar: "1 ta test" (10 000 so'm), "7 kunlik paket" (30 000 so'm), "30 kunlik to'liq paket" (70 000 so'm).
  - Rasmiy **Click Merchant** protokoli (Prepare & Complete server callback'lari, MD5 imzo tekshiruvi, xavfsiz aktivatsiya).
- **Telegram Bot Xabarnomalari:**
  - Muvaffaqiyatli to'lov amalga oshirilganda admin guruhiga / shaxsiy chatiga zudlik bilan avtomatik bildirishnoma.
- **Kengaytirilgan Savollar Banki va Import:**
  - Savollar versiyalanishi (`QuestionVersion`) va avtomatik dublikatlarni aniqlash (SHA-256 xesh va matn o'xshashligi).
  - **Excel Import:** jadval ustunlarini avtomatik tahlil qilish va qatorlar bo'yicha tekshirish.
  - **Word Import:** `.docx` matnidan savollar va to'g'ri javoblarni (`*` belgisi orqali) ajratish.
  - **AI Import:** erkin matn va test bloklaridan aqlli savol ajratish va Admin Preview orqali tasdiqlash.

---

## 2. Texnologik Stack

- **Backend:** Python 3.12, Flask 3.x, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Werkzeug.
- **Ma'lumotlar Bazasi:** MariaDB / MySQL (HeidiSQL orqali qulay boshqaruv) hamda lokal SQLite fallback.
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla ES6), Bootstrap 5.3, Bootstrap Icons.
- **Fayllar va Tahlil:** Pandas, OpenPyXL (Excel), python-docx (Word), Requests (Telegram & Click).
- **Xavfsizlik:** Bcrypt (parollarni kuchli xeshlash), CSRF himoyasi, MD5 Click raqamli imzosi, SQL injection va XSS himoyasi.

---

## 3. O'rnatish va Ishga Tushirish

### 1-qadam: Virtual muhitni yaratish va faollashtirish
```powershell
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2-qadam: Kutubxonalarni o'rnatish
```powershell
pip install -r requirements.txt
```

### 3-qadam: Konfiguratsiya (.env)
Loyiha ildizidagi `.env` faylini sozlang:
```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=attestatsiya-super-secure-production-key-2026-uzb
DATABASE_URL=sqlite:///attestatsiya.db
PORT=5000
HOST=0.0.0.0

# Click To'lov Tizimi
CLICK_MERCHANT_ID=test_merchant_id
CLICK_SERVICE_ID=test_service_id
CLICK_SECRET_KEY=test_secret_key

# Telegram Admin Xabarnoma Boti
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuVWXyz
TELEGRAM_ADMIN_CHAT_ID=-1001234567890
```

> **MariaDB (HeidiSQL) ulanish parametri:**
> Agar MariaDB ishlatmoqchi bo'lsangiz:
> 1. HeidiSQL orqali `attestatsiya_uz` nomli bo'sh ma'lumotlar bazasini yarating (utf8mb4_unicode_ci).
> 2. `database_schema.sql` faylini HeidiSQL ichida ishga tushiring.
> 3. `.env` faylida quyidagi qatorni faollashtiring:
> ```env
> DATABASE_URL=mysql+pymysql://root:parol@localhost:3306/attestatsiya_uz?charset=utf8mb4
> ```

---

## 4. Boshlang'ich Ma'lumotlarni Yuklash (Seeding)

Barcha 26 ta fan katalogi, mavzular tuzilmasi, namunaviy savollar banki, tarif paketlari hamda namunaviy administrator va o'qituvchi akkauntlarini yuklash uchun:
```powershell
python seed_demo.py
```

### Boshlang'ich Demo Foydalanuvchilar:
| Rol | Email | Parol | Tavsifi |
|---|---|---|---|
| **ADMIN** | `admin@example.com` | `Admin123!` | To'liq tizim va fanlar boshqaruvi |
| **FOYDALANUVCHI** | `user@example.com` | `User123!` | O'qituvchi (30 kunlik faol paket bilan) |

---

## 5. Avtomatlashtirilgan Testlarni Ishga Tushirish

Barcha funksional modullar (Ochiq sahifalar, 2 bosqichli ro'yxatdan o'tish, Admin ruxsatlari, Test topshirish sessiyasi, Tayyorgarlik indeksi, Click Webhook, Telegram bildirishnoma, AI import) uchun yozilgan testlarni yurgizish:
```powershell
python test_app.py
```
Natija: `Ran 8 tests ... OK` (100% muvaffaqiyatli).

---

## 6. Serverni Ishga Tushirish

```powershell
python run.py
```
Brauzerda oching: **`http://localhost:5000`** yoki **`http://127.0.0.1:5000`**

---

## 7. Loyiha Tuzilmasi

```
attestatsiya.uz/
├── app/
│   ├── blueprints/
│   │   ├── admin/           # Fanlar, savollar, paketlar, to'lovlar, telegram sozlamalari
│   │   ├── api/             # Test topshirish, Click prepare/complete callback'lari
│   │   ├── auth/            # 2 bosqichli ro'yxatdan o'tish va kirish
│   │   ├── public/          # Ochiq sayt: bosh sahifa, fanlar katalogi, paketlar
│   │   └── user/            # Shaxsiy kabinet, testlar, xatolarim, zaif mavzular, tahlil
│   ├── models/
│   │   ├── package.py       # Paketlar, Buyurtmalar, To'lovlar, Huquqlar (Entitlements)
│   │   ├── question.py      # Fanlar, Bo'limlar, Mavzular, Savollar, Versiyalar, Variantlar
│   │   ├── result.py        # Natijalar, Xatolar statistikasi, Zaif mavzular
│   │   ├── session.py       # Test topshirish sessiyalari va javoblar
│   │   ├── system.py        # Audit jurnali, Sozlamalar, Bildirishnomalar
│   │   └── user.py          # Foydalanuvchi modeli (Readiness score, paket tekshiruvi)
│   ├── services/
│   │   ├── ai_service.py           # AI matn tahlili va tavsiyalar
│   │   ├── analytics_service.py    # Tayyorgarlik ko'rsatkichi va zaif mavzular tahlili
│   │   ├── import_service.py       # Excel va Word import + duplikat tekshiruvi
│   │   ├── payment_service.py      # Click Prepare/Complete protokoli va MD5 validatsiya
│   │   ├── telegram_service.py     # Telegram to'lov xabarnomalari
│   │   └── test_engine_service.py  # 7 ta test rejimi, server taymeri va baholash
│   ├── static/              # CSS, JavaScript va rasmlar
│   └── templates/           # Jinja2 shablonlari (100% o'zbek tilida)
├── database_schema.sql      # MariaDB / MySQL uchun to'liq DDL sxemasi
├── requirements.txt         # Python kutubxonalari
├── run.py                   # Flask server kirish nuqtasi
├── seed_demo.py             # Baza ma'lumotlarini to'ldirish skripti
└── test_app.py              # Avtomatlashtirilgan testlar to'plami
```

---

## 8. Xavfsizlik Qoidalari va Standartlar

- Barcha to'lovlar rasmiy Click protokoli bo'yicha MD5 raqamli imzosi bilan ikki bosqichda (`Prepare` va `Complete`) tekshiriladi.
- Anti-cheat va taymer nazorati server darajasida amalga oshiriladi (mijoz taymerni soxtalashtira olmaydi).
- Barcha amallar `AuditLog` jurnalida xavfsiz qayd etib boriladi.
