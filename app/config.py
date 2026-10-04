import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class Config:
    """Production and Base Configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-attestatsiya-2026')
    
    # Ma'lumotlar bazasi: MariaDB (HeidiSQL) yoki avtomatik SQLite fallback
    # MariaDB format: mysql+pymysql://user:password@localhost:3306/attestatsiya_uz?charset=utf8mb4
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f"sqlite:///{os.path.join(BASE_DIR, 'attestatsiya.db')}"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True,
    }

    # Sessiya xavfsizligi
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # Set to True on production HTTPS

    # Fayllarni yuklash
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16 MB
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    ALLOWED_DOC_EXTENSIONS = {'pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg'}

    # Tashkilot va To'lov rekvizitlari
    PAYMENT_CARD_NUMBER = os.environ.get('PAYMENT_CARD_NUMBER', '8600 1234 5678 9012')
    PAYMENT_CARD_HOLDER = os.environ.get('PAYMENT_CARD_HOLDER', 'DAVLAT ATTESTATSIYA MARKAZI')
    PAYMENT_BANK_NAME = os.environ.get('PAYMENT_BANK_NAME', 'TIF MILLIY BANKI')
    PAYMENT_BANK_ACCOUNT = os.environ.get('PAYMENT_BANK_ACCOUNT', '20208000900000123001')
    PAYMENT_MFO = os.environ.get('PAYMENT_MFO', '00450')
    PAYMENT_INN = os.environ.get('PAYMENT_INN', '201122334')
    SUPPORT_PHONE = os.environ.get('SUPPORT_PHONE', '+998 71 200 00 00')
    SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', 'info@attestatsiya.uz')

    # AI sozlamalari
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
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
