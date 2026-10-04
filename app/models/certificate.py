import uuid
from datetime import datetime
from app.extensions import db

class CertificateStatus:
    ACTIVE = 'ACTIVE'
    EXPIRED = 'EXPIRED'
    REVOKED = 'REVOKED'
    CANCELLED = 'CANCELLED'

class Certificate(db.Model):
    __tablename__ = 'certificates'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    certificate_number = db.Column(db.String(64), unique=True, nullable=False, index=True)
    verification_uuid = db.Column(db.String(64), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    attestation_id = db.Column(db.Integer, db.ForeignKey('attestations.id', ondelete='CASCADE'), nullable=False, index=True)
    result_id = db.Column(db.Integer, db.ForeignKey('results.id', ondelete='CASCADE'), unique=True, nullable=False)

    issue_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    valid_until = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default=CertificateStatus.ACTIVE, index=True)

    pdf_path = db.Column(db.String(255), nullable=True)
    qr_code_path = db.Column(db.String(255), nullable=True)
    revocation_reason = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Aloqalar
    user = db.relationship('User', back_populates='certificates')
    attestation = db.relationship('Attestation', back_populates='certificates')
    result = db.relationship('Result', back_populates='certificate')
    verifications = db.relationship('CertificateVerification', back_populates='certificate', cascade='all, delete-orphan')

    @property
    def is_valid(self):
        if self.status != CertificateStatus.ACTIVE:
            return False
        return datetime.utcnow().date() <= self.valid_until

    def to_dict(self):
        return {
            'id': self.id,
            'certificate_number': self.certificate_number,
            'verification_uuid': self.verification_uuid,
            'user_name': self.user.full_name if self.user else None,
            'attestation_title': self.attestation.title if self.attestation else None,
            'score': float(self.result.score) if self.result else 0.0,
            'percentage': float(self.result.percentage) if self.result else 0.0,
            'issue_date': self.issue_date.strftime('%Y-%m-%d'),
            'valid_until': self.valid_until.strftime('%Y-%m-%d'),
            'status': self.status,
            'is_valid': self.is_valid,
            'pdf_path': self.pdf_path,
            'qr_code_path': self.qr_code_path
        }

class CertificateVerification(db.Model):
    __tablename__ = 'certificate_verifications'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    certificate_id = db.Column(db.Integer, db.ForeignKey('certificates.id', ondelete='CASCADE'), nullable=False, index=True)
    verified_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)

    certificate = db.relationship('Certificate', back_populates='verifications')
