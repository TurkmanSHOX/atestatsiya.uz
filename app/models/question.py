import hashlib
from datetime import datetime
from app.extensions import db

class QuestionType:
    SINGLE_CHOICE = 'SINGLE_CHOICE'
    MULTIPLE_CHOICE = 'MULTIPLE_CHOICE'
    TRUE_FALSE = 'TRUE_FALSE'
    MATCHING = 'MATCHING'
    ORDERING = 'ORDERING'
    IMAGE_BASED = 'IMAGE_BASED'
    TABLE_BASED = 'TABLE_BASED'
    FORMULA_BASED = 'FORMULA_BASED'
    AUDIO_BASED = 'AUDIO_BASED'
    VIDEO_BASED = 'VIDEO_BASED'
    FILL_BLANK = 'FILL_BLANK'

    CHOICES = [
        ('SINGLE_CHOICE', "Bitta to'g'ri javob"),
        ('MULTIPLE_CHOICE', "Bir nechta to'g'ri javob"),
        ('TRUE_FALSE', "To'g'ri / Noto'g'ri"),
        ('MATCHING', "Moslashtirish"),
        ('ORDERING', "Ketma-ketlik"),
        ('IMAGE_BASED', "Rasm asosidagi savol"),
        ('TABLE_BASED', "Jadval asosidagi savol"),
        ('FORMULA_BASED', "Formula asosidagi savol"),
        ('AUDIO_BASED', "Audio savol"),
        ('VIDEO_BASED', "Video savol"),
        ('FILL_BLANK', "Bo'sh joyni to'ldirish")
    ]

class DifficultyLevel:
    EASY = 'EASY'
    MEDIUM = 'MEDIUM'
    HARD = 'HARD'

    CHOICES = [
        ('EASY', 'Oson'),
        ('MEDIUM', "O'rta"),
        ('HARD', 'Qiyin')
    ]

class Subject(db.Model):
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    code = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    topics = db.relationship('Topic', back_populates='subject', cascade='all, delete-orphan')
    questions = db.relationship('Question', back_populates='subject')

class Topic(db.Model):
    __tablename__ = 'topics'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subject = db.relationship('Subject', back_populates='topics')
    questions = db.relationship('Question', back_populates='topic')

class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False, index=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=False, index=True)
    
    question_type = db.Column(db.String(30), nullable=False, default=QuestionType.SINGLE_CHOICE, index=True)
    text = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.String(20), default=DifficultyLevel.MEDIUM, index=True)
    points = db.Column(db.Numeric(5, 2), default=1.00)
    
    status = db.Column(db.String(20), default='ACTIVE', index=True)
    hash = db.Column(db.String(64), nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Aloqalar
    subject = db.relationship('Subject', back_populates='questions')
    topic = db.relationship('Topic', back_populates='questions')
    options = db.relationship('QuestionOption', back_populates='question', cascade='all, delete-orphan')
    media = db.relationship('QuestionMedia', back_populates='question', cascade='all, delete-orphan')

    @staticmethod
    def calculate_hash(text: str) -> str:
        clean = " ".join(text.strip().lower().split())
        return hashlib.sha256(clean.encode('utf-8')).hexdigest()

    def get_correct_option_ids(self):
        return [opt.id for opt in self.options if opt.is_correct]

    def to_dict(self, include_correct=False):
        return {
            'id': self.id,
            'subject_id': self.subject_id,
            'subject_name': self.subject.name if self.subject else None,
            'topic_id': self.topic_id,
            'topic_name': self.topic.name if self.topic else None,
            'question_type': self.question_type,
            'text': self.text,
            'explanation': self.explanation if include_correct else None,
            'difficulty': self.difficulty,
            'points': float(self.points),
            'status': self.status,
            'options': [opt.to_dict(include_correct=include_correct) for opt in self.options],
            'media': [m.to_dict() for m in self.media]
        }

class QuestionOption(db.Model):
    __tablename__ = 'question_options'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, index=True)
    option_key = db.Column(db.String(10), nullable=True)
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False, nullable=False)
    order_index = db.Column(db.Integer, default=0)
    match_key = db.Column(db.String(100), nullable=True)

    question = db.relationship('Question', back_populates='options')

    def to_dict(self, include_correct=False):
        data = {
            'id': self.id,
            'option_key': self.option_key,
            'text': self.text,
            'order_index': self.order_index,
            'match_key': self.match_key
        }
        if include_correct:
            data['is_correct'] = self.is_correct
        return data

class QuestionMedia(db.Model):
    __tablename__ = 'question_media'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, index=True)
    media_type = db.Column(db.String(20), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)

    question = db.relationship('Question', back_populates='media')

    def to_dict(self):
        return {
            'id': self.id,
            'media_type': self.media_type,
            'file_path': self.file_path
        }
