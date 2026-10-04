from datetime import datetime
from app.extensions import db

class Result(db.Model):
    __tablename__ = 'results'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.String(36), db.ForeignKey('test_sessions.id', ondelete='CASCADE'), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    attestation_id = db.Column(db.Integer, db.ForeignKey('attestations.id', ondelete='CASCADE'), nullable=False, index=True)

    total_questions = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False)
    incorrect_answers = db.Column(db.Integer, nullable=False)
    unanswered = db.Column(db.Integer, nullable=False)
    
    score = db.Column(db.Numeric(6, 2), nullable=False)
    percentage = db.Column(db.Numeric(5, 2), nullable=False)
    is_passed = db.Column(db.Boolean, nullable=False)
    completion_time_seconds = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Aloqalar
    session = db.relationship('TestSession', back_populates='result')
    user = db.relationship('User', back_populates='results')
    attestation = db.relationship('Attestation')
    details = db.relationship('ResultDetail', back_populates='result', cascade='all, delete-orphan')
    certificate = db.relationship('Certificate', back_populates='result', uselist=False, cascade='all, delete-orphan')

    def formatted_completion_time(self):
        minutes = self.completion_time_seconds // 60
        seconds = self.completion_time_seconds % 60
        return f"{minutes} daqiqa {seconds} soniya"

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'attestation_title': self.attestation.title if self.attestation else None,
            'total_questions': self.total_questions,
            'correct_answers': self.correct_answers,
            'incorrect_answers': self.incorrect_answers,
            'unanswered': self.unanswered,
            'score': float(self.score),
            'percentage': float(self.percentage),
            'is_passed': self.is_passed,
            'completion_time': self.formatted_completion_time(),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'has_certificate': bool(self.certificate)
        }

class ResultDetail(db.Model):
    __tablename__ = 'result_details'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    result_id = db.Column(db.Integer, db.ForeignKey('results.id', ondelete='CASCADE'), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=True)
    
    total_topic_questions = db.Column(db.Integer, nullable=False)
    correct_topic_questions = db.Column(db.Integer, nullable=False)
    topic_percentage = db.Column(db.Numeric(5, 2), nullable=False)

    result = db.relationship('Result', back_populates='details')
    subject = db.relationship('Subject')
    topic = db.relationship('Topic')
