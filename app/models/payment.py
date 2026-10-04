from datetime import datetime
from app.extensions import db

class PaymentStatus:
    PENDING = 'PENDING'
    PAID = 'PAID'
    REJECTED = 'REJECTED'
    REFUNDED = 'REFUNDED'
    EXPIRED = 'EXPIRED'

class PaymentMethod:
    CARD_MANUAL = 'CARD_MANUAL'
    BANK_TRANSFER = 'BANK_TRANSFER'
    CLICK = 'CLICK'
    PAYME = 'PAYME'
    UZCARD_HUMO = 'UZCARD_HUMO'

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('attestation_registrations.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(10), default='UZS')
    payment_method = db.Column(db.String(30), default=PaymentMethod.CARD_MANUAL)
    transaction_id = db.Column(db.String(120), unique=True, nullable=True)

    status = db.Column(db.String(20), default=PaymentStatus.PENDING, index=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    confirmed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Aloqalar
    registration = db.relationship('AttestationRegistration', back_populates='payments')
    user = db.relationship('User', back_populates='payments', foreign_keys=[user_id])
    confirmer = db.relationship('User', foreign_keys=[confirmed_by])
    receipts = db.relationship('PaymentReceipt', back_populates='payment', cascade='all, delete-orphan')

    @property
    def latest_receipt(self):
        return self.receipts[-1] if self.receipts else None

    def formatted_amount(self):
        return f"{self.amount:,.0f} {self.currency}".replace(',', ' ')

class PaymentReceipt(db.Model):
    __tablename__ = 'payment_receipts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id', ondelete='CASCADE'), nullable=False, index=True)
    file_path = db.Column(db.String(255), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    mime_type = db.Column(db.String(80), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    payment = db.relationship('Payment', back_populates='receipts')
