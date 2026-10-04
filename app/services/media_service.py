import os
import uuid
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app

class MediaService:
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
    ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/pjpeg', 'image/x-png'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
    MAX_DIMENSION = 1600  # Maksimal kenglik yoki balandlik (px)

    @classmethod
    def is_allowed_image(cls, filename: str, content_type: str = None) -> bool:
        if not filename or '.' not in filename:
            return False
        ext = filename.rsplit('.', 1)[1].lower()
        if ext not in cls.ALLOWED_IMAGE_EXTENSIONS:
            return False
        if content_type and content_type.lower() not in cls.ALLOWED_MIME_TYPES:
            return False
        return True

    @classmethod
    def save_image(cls, file_storage, subfolder: str = 'options') -> dict:
        """
        Yuklangan rasmni tekshirish, optimallashtirish va xavfsiz saqlash.
        subfolder: 'options' yoki 'questions'
        """
        if not file_storage or not file_storage.filename:
            return None

        filename = file_storage.filename
        content_type = file_storage.content_type

        if not cls.is_allowed_image(filename, content_type):
            raise ValueError(f"Faqat quyidagi rasm formatlari qo'llab-quvvatlanadi: JPG, JPEG, PNG, WEBP. (Fayl: {filename})")

        # Fayl hajmini tekshirish
        file_storage.seek(0, os.SEEK_END)
        size = file_storage.tell()
        file_storage.seek(0)

        if size > cls.MAX_FILE_SIZE:
            raise ValueError(f"Rasm hajmi juda katta ({size // 1024} KB). Ruxsat etilgan maksimal hajm: 5 MB.")

        # Saqlash papkasi
        upload_base = current_app.config.get('UPLOAD_FOLDER')
        target_dir = os.path.join(upload_base, subfolder)
        os.makedirs(target_dir, exist_ok=True)

        # Xavfsiz unikal fayl nomi
        ext = filename.rsplit('.', 1)[1].lower()
        safe_base = secure_filename(filename.rsplit('.', 1)[0])
        unique_name = f"{uuid.uuid4().hex[:12]}_{safe_base}.{ext}" if safe_base else f"{uuid.uuid4().hex[:16]}.{ext}"
        target_path = os.path.join(target_dir, unique_name)

        # Pillow orqali rasmni ochish va validatsiya qilish
        try:
            img = Image.open(file_storage)
            img.verify() # Buzilgan yoki zararli fayllarni aniqlaydi
        except Exception as e:
            raise ValueError(f"Yuklangan rasm fayli yaroqsiz yoki shikastlangan: {str(e)}")

        # Qayta o'qish va optimallashtirish
        file_storage.seek(0)
        img = Image.open(file_storage)

        # O'lchamni moslashtirish (agar 1600px dan katta bo'lsa)
        if img.width > cls.MAX_DIMENSION or img.height > cls.MAX_DIMENSION:
            img.thumbnail((cls.MAX_DIMENSION, cls.MAX_DIMENSION), Image.Resampling.LANCZOS)

        # Format bo'yicha to'g'ri saqlash
        save_format = img.format or ('JPEG' if ext in ['jpg', 'jpeg'] else ext.upper())
        if save_format in ['JPEG', 'JPG'] and img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')

        img.save(target_path, format=save_format, quality=88, optimize=True)

        # Nisbiy yo'llar
        rel_path = os.path.join('static', 'uploads', subfolder, unique_name).replace('\\', '/')
        web_url = f"/{rel_path}"

        final_size = os.path.getsize(target_path)

        return {
            'file_path': rel_path,
            'file_url': web_url,
            'original_name': filename,
            'mime_type': content_type or f"image/{ext}",
            'file_size': final_size,
            'media_type': 'IMAGE'
        }

    @classmethod
    def delete_file(cls, file_path: str):
        """Faylni xavfsiz o'chirish"""
        if not file_path:
            return
        clean_path = file_path.lstrip('/')
        if clean_path.startswith('static/'):
            base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
            full_path = os.path.join(base_dir, clean_path)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                try:
                    os.remove(full_path)
                except OSError:
                    pass
