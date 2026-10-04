import uuid
from datetime import datetime
from app.extensions import db

class SessionStatus:
    IN_PROGRESS = 'IN_PROGRESS'
    SUBMITTED = 'SUBMITTED'
    EXPIRED = 'EXPIRED'
    TERMINATED = 'TERMINATED'

class TestSession(db.Model):
    __tablename__ = 'test_sessions'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id', ondelete='CASCADE'), nullable=False, index=True)

    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    
    status = db.Column(db.String(20), default=SessionStatus.IN_PROGRESS, index=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    last_heartbeat_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Aloqalar
    user = db.relationship('User', back_populates='sessions')
    test = db.relationship('Test', back_populates='sessions')
    answers = db.relationship('TestAnswer', back_populates='session', cascade='all, delete-orphan')
    result = db.relationship('Result', back_populates='session', uselist=False, cascade='all, delete-orphan')

    @property
    def remaining_seconds(self):
        if self.status != SessionStatus.IN_PROGRESS:
            return 0
        now = datetime.utcnow()
        if now >= self.expires_at:
            return 0
        return int((self.expires_at - now).total_seconds())

    @property
    def is_expired(self):
        return self.status == SessionStatus.IN_PROGRESS and datetime.utcnow() >= self.expires_at

class TestAnswer(db.Model):
    __tablename__ = 'test_answers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.String(36), db.ForeignKey('test_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, index=True)
    
    selected_option_ids = db.Column(db.JSON, nullable=True)
    text_answer = db.Column(db.Text, nullable=True)
    is_flagged = db.Column(db.Boolean, default=False)
    
    is_correct = db.Column(db.Boolean, nullable=True)
    awarded_points = db.Column(db.Numeric(5, 2), default=0.00)
    answered_at = db.Column(db.DateTime, nullable=True)
    time_spent_seconds = db.Column(db.Integer, default=0)

    session = db.relationship('TestSession', back_populates='answers')
    question = db.relationship('Question')
