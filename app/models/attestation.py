from datetime import datetime
from app.extensions import db

class AttestationStatus:
    DRAFT = 'DRAFT'
    ACTIVE = 'ACTIVE'
    PAUSED = 'PAUSED'
    FINISHED = 'FINISHED'
    ARCHIVED = 'ARCHIVED'

class RegistrationStep:
    REGISTERED = 'REGISTERED'
    DOCUMENTS = 'DOCUMENTS'
    PAYMENT = 'PAYMENT'
    ADMIN_REVIEW = 'ADMIN_REVIEW'
    APPROVED = 'APPROVED'
    EXAM_READY = 'EXAM_READY'
    COMPLETED = 'COMPLETED'
    REJECTED = 'REJECTED'

class Attestation(db.Model):
    __tablename__ = 'attestations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False, index=True)
    short_description = db.Column(db.String(500), nullable=False)
    full_description = db.Column(db.Text, nullable=False)
    field_name = db.Column(db.String(150), nullable=False, index=True)
    
    price = db.Column(db.Numeric(12, 2), nullable=False, default=0.00)
    currency = db.Column(db.String(10), nullable=False, default='UZS')

    questions_count = db.Column(db.Integer, nullable=False, default=40)
    duration_minutes = db.Column(db.Integer, nullable=False, default=60)
    passing_score = db.Column(db.Numeric(5, 2), nullable=False, default=60.00)
    max_score = db.Column(db.Numeric(5, 2), nullable=False, default=100.00)
    max_attempts = db.Column(db.Integer, nullable=False, default=1)
    retake_delay_days = db.Column(db.Integer, default=30)
    
    show_result_immediately = db.Column(db.Boolean, default=True)
    show_answers_after_exam = db.Column(db.Boolean, default=False)
    issue_certificate = db.Column(db.Boolean, default=True)
    certificate_validity_months = db.Column(db.Integer, default=36)

    starts_at = db.Column(db.DateTime, nullable=True)
    ends_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default=AttestationStatus.DRAFT, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Aloqalar
    registrations = db.relationship('AttestationRegistration', back_populates='attestation', cascade='all, delete-orphan')
    tests = db.relationship('Test', back_populates='attestation', cascade='all, delete-orphan')
    certificates = db.relationship('Certificate', back_populates='attestation')

    def formatted_price(self):
        return f"{self.price:,.0f} {self.currency}".replace(',', ' ')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'short_description': self.short_description,
            'field_name': self.field_name,
            'price': float(self.price),
            'formatted_price': self.formatted_price(),
            'currency': self.currency,
            'questions_count': self.questions_count,
            'duration_minutes': self.duration_minutes,
            'passing_score': float(self.passing_score),
            'max_score': float(self.max_score),
            'max_attempts': self.max_attempts,
            'status': self.status,
            'issue_certificate': self.issue_certificate,
            'starts_at': self.starts_at.strftime('%Y-%m-%d') if self.starts_at else None,
            'ends_at': self.ends_at.strftime('%Y-%m-%d') if self.ends_at else None
        }

class AttestationRegistration(db.Model):
    __tablename__ = 'attestation_registrations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    registration_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    attestation_id = db.Column(db.Integer, db.ForeignKey('attestations.id', ondelete='CASCADE'), nullable=False, index=True)
    
    step = db.Column(db.String(30), default=RegistrationStep.REGISTERED, index=True)
    admin_comment = db.Column(db.Text, nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Aloqalar
    user = db.relationship('User', back_populates='registrations', foreign_keys=[user_id])
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    attestation = db.relationship('Attestation', back_populates='registrations')
    payments = db.relationship('Payment', back_populates='registration', cascade='all, delete-orphan')
    sessions = db.relationship('TestSession', back_populates='registration')

    @property
    def latest_payment(self):
        return self.payments[-1] if self.payments else None
