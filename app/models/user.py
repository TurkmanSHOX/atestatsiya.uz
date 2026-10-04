from datetime import datetime
import bcrypt
from flask_login import UserMixin
from app.extensions import db, login_manager

class UserRole:
    ADMIN = 'ADMIN'
    FOYDALANUVCHI = 'FOYDALANUVCHI'

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role = db.Column(db.String(20), nullable=False, default=UserRole.FOYDALANUVCHI, index=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Shaxsiy ma'lumotlar
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    middle_name = db.Column(db.String(80), nullable=True)
    birth_date = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10), nullable=True)  # ERKAK, AYOL
    region = db.Column(db.String(100), nullable=True)  # Toshkent sh., Samarqand vil., etc.

    # Kasbiy / Maktab ma'lumotlari
    organization = db.Column(db.String(255), nullable=True) # Maktab yoki tashkilot nomi
    position = db.Column(db.String(150), nullable=True)     # O'qituvchi, Metodist va h.k.
    specialty = db.Column(db.String(150), nullable=True)    # Fan (Matematika, Fizika...)
    experience_years = db.Column(db.Integer, default=0)
    avatar_path = db.Column(db.String(255), nullable=True)

    # Holat va xavfsizlik
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_verified = db.Column(db.Boolean, default=False)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(64), nullable=True)
    last_login_at = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(45), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Aloqalar
    orders = db.relationship('Order', back_populates='user', cascade='all, delete-orphan')
    payments = db.relationship('Payment', back_populates='user', cascade='all, delete-orphan')
    entitlements = db.relationship('Entitlement', back_populates='user', cascade='all, delete-orphan')
    sessions = db.relationship('TestSession', back_populates='user', cascade='all, delete-orphan')
    results = db.relationship('Result', back_populates='user', cascade='all, delete-orphan')
    question_stats = db.relationship('UserQuestionStat', back_populates='user', cascade='all, delete-orphan')
    topic_stats = db.relationship('UserTopicStat', back_populates='user', cascade='all, delete-orphan')
    bookmarks = db.relationship('Bookmark', back_populates='user', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', back_populates='user', cascade='all, delete-orphan')

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(parts)

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    def set_password(self, password: str):
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def has_active_package(self) -> bool:
        """Foydalanuvchida faol va muddati o'tmagan paket bormi?"""
        if self.is_admin:
            return True
        now = datetime.utcnow()
        for ent in self.entitlements:
            if ent.is_active and ent.expires_at > now:
                if ent.tests_remaining is None or ent.tests_remaining > 0:
                    return True
        return False

    def has_subject_access(self, subject_id: int = None) -> bool:
        """Muayyan fan bo'yicha premium test ishlashga huquqi bormi?"""
        if self.is_admin:
            return True
        now = datetime.utcnow()
        for ent in self.entitlements:
            if ent.is_active and ent.expires_at > now:
                if ent.tests_remaining is None or ent.tests_remaining > 0:
                    # Agar subject_id bo'lmasa yoki ent.subject_id None (barcha fanlar) bo'lsa yoki mos kelsa
                    if subject_id is None or ent.subject_id is None or ent.subject_id == subject_id:
                        return True
        return False

    def get_active_entitlement(self, subject_id: int = None):
        """Faol entitlement obyektini qaytarish"""
        now = datetime.utcnow()
        for ent in self.entitlements:
            if ent.is_active and ent.expires_at > now:
                if ent.tests_remaining is None or ent.tests_remaining > 0:
                    if subject_id is None or ent.subject_id is None or ent.subject_id == subject_id:
                        return ent
        return None

    def get_readiness_score(self) -> int:
        """
        Attestatsiyaga tayyorgarlik darajasi indeksi (0-100%).
        Foydalanuvchining ishlangan testlari, so'nggi natijalari va mavzular qamrovi asosida.
        """
        if not self.results:
            return 0
        
        # 1. So'nggi testlar o'rtacha foizi (vazn 50%)
        recent_results = sorted(self.results, key=lambda r: r.created_at, reverse=True)[:5]
        avg_score = sum(float(r.percentage) for r in recent_results) / len(recent_results)
        
        # 2. Mavzular qamrovi va aniqligi (vazn 30%)
        topic_scores = [float(ts.accuracy_percentage) for ts in self.topic_stats if ts.total_answered >= 3]
        topic_avg = sum(topic_scores) / len(topic_scores) if topic_scores else avg_score
        
        # 3. Testlar soni bo'yicha faollik ko'rsatkichi (vazn 20%)
        tests_count_factor = min(100.0, len(self.results) * 10)
        
        readiness = (avg_score * 0.50) + (topic_avg * 0.30) + (tests_count_factor * 0.20)
        return int(min(100, max(0, round(readiness))))

    @property
    def weak_topics_count(self) -> int:
        """Zaif mavzular soni (<60% aniqlik)"""
        return sum(1 for ts in self.topic_stats if ts.total_answered >= 3 and float(ts.accuracy_percentage) < 60.0)

    def to_dict(self):
        return {
            'id': self.id,
            'role': self.role,
            'email': self.email,
            'phone': self.phone,
            'full_name': self.full_name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'middle_name': self.middle_name,
            'organization': self.organization,
            'position': self.position,
            'specialty': self.specialty,
            'experience_years': self.experience_years,
            'region': self.region,
            'is_active': self.is_active,
            'has_active_package': self.has_active_package(),
            'readiness_score': self.get_readiness_score(),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
        }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
