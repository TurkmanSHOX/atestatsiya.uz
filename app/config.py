import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class Config:
    """Production and Base Configuration for Attestatsiya.uz 2.0"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-attestatsiya-2026')
    
    # Ma'lumotlar bazasi: MariaDB (HeidiSQL) yoki avtomatik SQLite fallback
    # MariaDB format: mysql+pymysql://user:password@localhost:3306/attestatsiya_uz?charset=utf8mb4
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'attestatsiya.db')}"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True,
    }

    # Sessiya xavfsizligi
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # Set to True on production HTTPS

    # Fayllarni yuklash
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16 MB
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    ALLOWED_DOC_EXTENSIONS = {'xlsx', 'xls', 'docx', 'doc', 'pdf', 'txt'}

    # Tashkilot va Qo'llab-quvvatlash rekvizitlari
    SUPPORT_PHONE = os.environ.get('SUPPORT_PHONE', '+998 71 200 00 00')
    SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', 'info@attestatsiya.uz')

    # Click To'lov Tizimi Rekvizitlari
    CLICK_MERCHANT_ID = os.environ.get('CLICK_MERCHANT_ID', 'test_merchant_id')
    CLICK_SERVICE_ID = os.environ.get('CLICK_SERVICE_ID', 'test_service_id')
    CLICK_SECRET_KEY = os.environ.get('CLICK_SECRET_KEY', 'test_secret_key')

    # Telegram Xabarnoma Bot Sozlamalari
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_ADMIN_CHAT_ID = os.environ.get('TELEGRAM_ADMIN_CHAT_ID', '')

    # AI Sozlamalari
    AI_API_KEY = os.environ.get('AI_API_KEY', '')
    AI_MODEL_NAME = os.environ.get('AI_MODEL_NAME', 'gpt-4o-mini')
    AI_ENABLED = os.environ.get('AI_ENABLED', 'true').lower() in ('true', '1', 't')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
