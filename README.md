# ATTESTATSIYA.UZ — Professional Attestatsiya va Imtihon Boshqaruv Tizimi

O'zbekistonda pullik professional attestatsiyalar va onlayn imtihonlarni o'tkazish, nomzodlar bilimini xolis baholash, anti-cheat va proktoring nazorati hamda QR-kodli elektron sertifikatlar berish uchun mo'ljallangan milliy web-platforma.

---

## 1. Asosiy Xususiyatlar va Imkoniyatlar

- **Faqat 2 ta Rol:** `ADMIN` va `FOYDALANUVCHI` (Candidate).
- **To'liq Attestatsiya Sikli:**
  1. Ro'yxatdan o'tish (3 bosqichli: Shaxsiy -> Kasbiy -> Hujjatlar)
  2. Attestatsiya tanlash va ariza topshirish
  3. Karta orqali to'lov va to'lov kvitansiyasini (chek) yuklash
  4. Administrator tekshiruvi va ruxsat berish
  5. Texnik tekshiruv (Veb-kamera, Mikrofon, Fullscreen mosligi)
  6. Imtihon sinovi (Server-side taymer, savollar navigatori, avto-saqlash)
  7. Kiberxavfsizlik va Anti-cheat nazorati (Tab almashtirish, o'ng tugma, nusxa olish, devtools bloklash)
  8. Avtomatik baholash va mavzular bo'yicha batafsil tahlil
  9. QR-kodli rasmiy PDF sertifikat generatsiyasi
  10. Ochiq QR sertifikat verifikatsiyasi (`/verify-certificate/<cert_no>`).
- **Savollar Banki va Import:**
  - 11 turdagi savollarni qo'llab-quvvatlash (Bitta to'g'ri, Bir nechta, Moslashtirish, Ketma-ketlik, Jadval, Rasm, Formula, Bo'sh joy va h.k.)
  - **Excel Import:** Ustunlarni avtomatik aniqlash, xatoliklar (qator raqamlari bilan), takroriylikni aniqlash va preview.
  - **Word Import:** `1. Savol`, `A) Variant`, `*B) To'g'ri javob` formatini avtomatik ajratish.
  - **AI Import:** Nostrukturalangan matn, PDF va Word matnlaridan savollarni ajratish hamda Admin preview orqali tasdiqlash.
- **Test Blueprint Konstruktori:** Fan va mavzular hamda qiyinlik darajalari (Oson, O'rta, Qiyin) bo'yicha aniq kvotalar asosida tasodifiy savollar generatsiyasi.
- **Jonli Monitoring va Audit:** Faol imtihon sessiyalarini kuzatish, shubhali harakatlar jurnali, barcha administrator harakatlarining to'liq audit jurnali.

---

## 2. Texnologik Stack

- **Backend:** Python 3.12, Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Werkzeug.
- **Ma'lumotlar Bazasi:** MariaDB / MySQL (HeidiSQL orqali qulay boshqaruv) hamda sinov uchun SQLite fallback.
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla ES6), Bootstrap 5, Bootstrap Icons.
- **PDF & QR Generatsiya:** ReportLab, QRCode, Pillow.
- **Fayllar Bilan Ishlash:** Pandas, OpenPyXL (Excel), python-docx (Word).
- **Xavfsizlik:** Bcrypt (parollar xeshlash), CSRF himoyasi, Anti-Cheat proktoring moduli, Rate limiting.

---

## 3. Loyihani O'rnatish va Ishga Tushirish

### 1-qadam: Virtual muhitni faollashtirish
```powershell
# Windows PowerShell
.\venv\Scripts\Activate.ps1
```

### 2-qadam: Kutubxonalarni o'rnatish
```powershell
pip install -r requirements.txt
```

### 3-qadam: Sozlamalar (.env)
Loyiha ildizidagi `.env` faylida quyidagi konfiguratsiyalar mavjud:
```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=attestatsiya-super-secure-production-key-2026-uzb
DATABASE_URL=sqlite:///attestatsiya.db
PORT=5000
HOST=0.0.0.0
```

### 4-qadam: MariaDB / HeidiSQL bilan ulash (Ixtiyoriy)
MariaDB serveringizda yangi baza yarating:
```sql
CREATE DATABASE attestatsiya_uz CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
`.env` faylida `DATABASE_URL` parametrini MariaDB ulanishiga o'zgartiring:
```env
DATABASE_URL=mysql+pymysql://root:parol@localhost:3306/attestatsiya_uz?charset=utf8mb4
```

### 5-qadam: Demo ma'lumotlarni yuklash (Seeder)
```powershell
python seed_demo.py
```
Bu buyruq:
- Jadvallarni yaratadi;
- Admin va Nomzod hisoblarini ochadi;
- Fanlar va mavzularni kiritadi;
- "Pedagog kadrlar attestatsiyasi" dasturini yaratadi;
- 40 ta professional pedagogik va psixologik savollarni kiritadi;
- Test va Blueprint kvotalarini o'rnatadi.

### 6-qadam: Serverni ishga tushirish
```powershell
python run.py
```
Brauzerda oching: **`http://localhost:5000`**

---

## 4. Tizimga Kirish (Demo Hisoblar)

### Administrator (ADMIN):
- **Email:** `admin@example.com`
- **Parol:** `Admin123!`
- **Panel:** `http://localhost:5000/admin/dashboard`

### Nomzod (FOYDALANUVCHI):
- **Email:** `user@example.com`
- **Parol:** `User123!`
- **Kabinet:** `http://localhost:5000/dashboard`

---

## 5. Sahifalar va Yo'nalishlar Xaritasi

### Ochiq Sayt (Public):
- `/` — Bosh sahifa (Hero banner, faol attestatsiyalar, statistika, afzalliklar)
- `/attestations` — Attestatsiyalar katalogi (Qidiruv, narx va yo'nalish filtrlari)
- `/attestations/<slug>` — Attestatsiya haqida batafsil va ariza topshirish
- `/exam-rules` — Imtihon tartibi va anti-cheat talablari
- `/pricing` — Narxlar va rasmiy to'lov rekvizitlari
- `/faq` — Ko'p beriladigan savollar
- `/help` — Texnik yo'riqnoma
- `/contact` — Bog'lanish va qayta aloqa
- `/news` — Yangiliklar va rasmiy e'lonlar
- `/verify-certificate/<cert_no>` — **QR Sertifikatni ochiq tekshirish**

### Foydalanuvchi Kabineti:
- `/dashboard` — Shaxsiy kabinet bosh sahifasi
- `/profile` — Profil tahrirlash va parolni almashtirish
- `/my-attestations` — Arizalar va ularning bosqichma-bosqich vizual holati
- `/attestation/<id>/payment` — Karta rekvizitlari va chek yuklash
- `/attestation/<id>/device-check` — Veb-kamera va mikrofon texnik tekshiruvi
- `/attestation/<id>/instructions` — Imtihon oldi rozilik yo'riqnomasi
- `/exam/<session_id>` — **Imtihon oynasi (Taymer, navigator, anti-cheat)**
- `/results` va `/results/<id>` — Natijalar tarixi va mavzular bo'yicha tahlil
- `/certificates` — Elektron sertifikatlar ro'yxati va PDF yuklab olish

### Admin Markazi:
- `/admin/dashboard` — Boshqaruv paneli, real-vaqt statistikasi
- `/admin/users` — Foydalanuvchilarni qidirish, faollashtirish va bloklash
- `/admin/attestations` & `create` — Attestatsiya konstruktori
- `/admin/questions` & `create` — Savollar banki va 11 turdagi savol muharriri
- `/admin/import-excel` — Excel import (xatoliklar hisoboti va preview)
- `/admin/import-word` — Word import (`*` belgisi bilan to'g'ri javobni aniqlash)
- `/admin/import-ai` — AI / matndan savollarni ajratish va admin tasdig'i
- `/admin/tests` — Test va Blueprint kvotalari (Validatsiya tekshiruvi)
- `/admin/payments` — To'lov cheklarini ko'rish, tasdiqlash va rad etish
- `/admin/exam-sessions` — Jonli imtihon monitoringi
- `/admin/results` — Umumiy baholash natijalari
- `/admin/certificates` — Sertifikatlar reyestri va bekor qilish (Revoke)
- `/admin/proctoring-events` — Qoidabuzarliklar va xavflar jurnali
- `/admin/audit-logs` — Barcha administrator amallarining to'liq audit jurnali
- `/admin/settings` — Tashkilot rekvizitlari va platforma sozlamalari

---

## 6. Testlarni Avtomatlashtirilgan Tekshirish

Tizimning to'liq ishlashini avtomatik test qilish:
```powershell
python test_app.py
```
Natija:
```text
Ran 6 tests in 0.784s
OK
```

---

## 7. Xavfsizlik Kafolatlari

1. **SQL Injection himoyasi:** Parametrlashtirilgan SQLAlchemy ORM so'rovlari.
2. **CSRF himoyasi:** Barcha formalar `csrf_token` bilan himoyalangan.
3. **Parollar:** `Bcrypt` (12 rounds) orqali xeshlanadi.
4. **Anti-Cheat:** Ekranni almashtirish (`blur`, `visibilitychange`), sichqoncha o'ng tugmasi va dasturchi vositalari (DevTools) imtihon davomida bloklanadi va serverga hodisa yuboriladi.
5. **Server-Side Vaqt:** Vaqt server tomondan hisoblanadi, brauzer JavaScript'i faqat vizual taymerdir.
