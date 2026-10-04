from datetime import datetime
from app.extensions import db

class TelegramUser(db.Model):
    __tablename__ = 'telegram_users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    telegram_chat_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    username = db.Column(db.String(100), nullable=True)
    full_name = db.Column(db.String(150), nullable=True)
    role = db.Column(db.String(20), default='ADMIN') # ADMIN
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    action = db.Column(db.String(50), nullable=False, index=True) # CREATE, UPDATE, DELETE, PAYMENT, IMPORT
    entity = db.Column(db.String(50), nullable=False, index=True) # USER, SUBJECT, TOPIC, QUESTION, TEST, PACKAGE, ORDER
    entity_id = db.Column(db.String(50), nullable=True)
    old_values = db.Column(db.JSON, nullable=True)
    new_values = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User')

    def to_dict(self):
        return {
            'id': self.id,
            'user_name': self.user.full_name if self.user else "Tizim",
            'action': self.action,
            'entity': self.entity,
            'entity_id': self.entity_id,
            'ip_address': self.ip_address,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class Setting(db.Model):
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key_name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value_text = db.Column(db.Text, nullable=True)
    group_name = db.Column(db.String(50), default='GENERAL')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get_val(key: str, default=None):
        setting = Setting.query.filter_by(key_name=key).first()
        return setting.value_text if setting else default

    @staticmethod
    def set_val(key: str, value: str, group='GENERAL'):
        setting = Setting.query.filter_by(key_name=key).first()
        if not setting:
            setting = Setting(key_name=key, group_name=group)
            db.session.add(setting)
        setting.value_text = value
        setting.updated_at = datetime.utcnow()
        db.session.commit()
        return setting

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='notifications')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'link': self.link,
            'is_read': self.is_read,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }
