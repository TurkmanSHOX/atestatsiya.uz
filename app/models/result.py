from datetime import datetime
from app.extensions import db

class Result(db.Model):
    __tablename__ = 'results'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.String(36), db.ForeignKey('test_sessions.id', ondelete='CASCADE'), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id', ondelete='CASCADE'), nullable=False, index=True)

    total_questions = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False)
    incorrect_answers = db.Column(db.Integer, nullable=False)
    unanswered = db.Column(db.Integer, nullable=False)
    
    score = db.Column(db.Numeric(6, 2), nullable=False)
    percentage = db.Column(db.Numeric(5, 2), nullable=False)
    is_passed = db.Column(db.Boolean, nullable=False)
    completion_time_seconds = db.Column(db.Integer, nullable=False)
    
    ai_recommendation = db.Column(db.Text, nullable=True) # AI tavsiyasi
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Aloqalar
    session = db.relationship('TestSession', back_populates='result')
    user = db.relationship('User', back_populates='results')
    test = db.relationship('Test', back_populates='results')
    details = db.relationship('ResultDetail', back_populates='result', cascade='all, delete-orphan')

    def formatted_completion_time(self):
        minutes = self.completion_time_seconds // 60
        seconds = self.completion_time_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'test_id': self.test_id,
            'test_title': self.test.title if self.test else None,
            'total_questions': self.total_questions,
            'correct_answers': self.correct_answers,
            'incorrect_answers': self.incorrect_answers,
            'unanswered': self.unanswered,
            'score': float(self.score),
            'percentage': float(self.percentage),
            'is_passed': self.is_passed,
            'completion_time': self.formatted_completion_time(),
            'ai_recommendation': self.ai_recommendation,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'details': [d.to_dict() for d in self.details]
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

    def to_dict(self):
        return {
            'id': self.id,
            'subject_name': self.subject.name if self.subject else None,
            'topic_name': self.topic.name if self.topic else None,
            'total': self.total_topic_questions,
            'correct': self.correct_topic_questions,
            'percentage': float(self.topic_percentage)
        }

class UserQuestionStat(db.Model):
    """Foydalanuvchining har bir savol bo'yicha statistikasi (Xatolarim tizimi uchun)"""
    __tablename__ = 'user_question_stats'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, index=True)
    
    attempts_count = db.Column(db.Integer, default=1)
    correct_count = db.Column(db.Integer, default=0)
    incorrect_count = db.Column(db.Integer, default=0)
    is_last_correct = db.Column(db.Boolean, default=False, index=True)
    last_attempt_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='question_stats')
    question = db.relationship('Question')

class UserTopicStat(db.Model):
    """Foydalanuvchining har bir mavzu bo'yicha statistikasi (Zaif mavzular tizimi uchun)"""
    __tablename__ = 'user_topic_stats'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id', ondelete='CASCADE'), nullable=False, index=True)
    
    total_answered = db.Column(db.Integer, default=0)
    correct_answered = db.Column(db.Integer, default=0)
    accuracy_percentage = db.Column(db.Numeric(5, 2), default=0.00, index=True)
    last_updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='topic_stats')
    topic = db.relationship('Topic')

class Bookmark(db.Model):
    """Saqlangan savollar (Bookmarks)"""
    __tablename__ = 'bookmarks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='bookmarks')
    question = db.relationship('Question')
