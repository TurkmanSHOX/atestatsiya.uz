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

    # Kasbiy ma'lumotlar
    organization = db.Column(db.String(255), nullable=True)
    position = db.Column(db.String(150), nullable=True)
    specialty = db.Column(db.String(150), nullable=True)
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
    documents = db.relationship('UserDocument', back_populates='user', cascade='all, delete-orphan')
    registrations = db.relationship('AttestationRegistration', back_populates='user', foreign_keys='AttestationRegistration.user_id')
    payments = db.relationship('Payment', back_populates='user', foreign_keys='Payment.user_id')
    sessions = db.relationship('TestSession', back_populates='user')
    results = db.relationship('Result', back_populates='user')
    certificates = db.relationship('Certificate', back_populates='user')
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
            'is_verified': self.is_verified,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
        }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class UserDocument(db.Model):
    __tablename__ = 'user_documents'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    doc_type = db.Column(db.String(50), nullable=False)  # PASSPORT, DIPLOM, MEHNAT_DAFTARCHASI, SERTIFIKAT, BOSHQA
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(80), nullable=False)
    verification_status = db.Column(db.String(20), default='PENDING', index=True)  # PENDING, APPROVED, REJECTED
    verified_at = db.Column(db.DateTime, nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='documents')
