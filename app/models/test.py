from datetime import datetime
from app.extensions import db

class TestType:
    MAVZU = 'MAVZU'                 # Mavzu bo'yicha test
    FAN = 'FAN'                     # Fan bo'yicha test
    ARALASH = 'ARALASH'             # Aralash test
    SIMULYATSIYA = 'SIMULYATSIYA'   # Attestatsiya simulyatsiyasi (50 ta savol, 90 daqiqa)
    XATOLAR = 'XATOLAR'             # Xatolarimdan test
    ZAIF_MAVZULAR = 'ZAIF_MAVZULAR' # Zaif mavzulardan test
    TASODIFIY = 'TASODIFIY'         # Tasodifiy test

    CHOICES = [
        ('MAVZU', "Mavzu bo'yicha test"),
        ('FAN', "Fan bo'yicha test"),
        ('ARALASH', "Aralash test"),
        ('SIMULYATSIYA', "Attestatsiya simulyatsiyasi"),
        ('XATOLAR', "Xatolarim"),
        ('ZAIF_MAVZULAR', "Zaif mavzular"),
        ('TASODIFIY', "Tasodifiy test")
    ]

class Test(db.Model):
    __tablename__ = 'tests'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    test_type = db.Column(db.String(30), default=TestType.FAN, index=True)
    
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='SET NULL'), nullable=True, index=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id', ondelete='SET NULL'), nullable=True, index=True)
    
    duration_minutes = db.Column(db.Integer, nullable=False, default=60)
    passing_score = db.Column(db.Numeric(5, 2), nullable=False, default=60.00) # Foizda
    total_questions = db.Column(db.Integer, default=30)
    
    shuffle_questions = db.Column(db.Boolean, default=True)
    shuffle_options = db.Column(db.Boolean, default=True)
    is_free = db.Column(db.Boolean, default=False, index=True) # Bepul demo test
    status = db.Column(db.String(20), default='ACTIVE', index=True) # ACTIVE, DRAFT

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Aloqalar
    subject = db.relationship('Subject', back_populates='tests')
    topic = db.relationship('Topic')
    blueprint = db.relationship('TestBlueprint', back_populates='test', uselist=False, cascade='all, delete-orphan')
    test_questions = db.relationship('TestQuestion', back_populates='test', cascade='all, delete-orphan')
    sessions = db.relationship('TestSession', back_populates='test')
    results = db.relationship('Result', back_populates='test')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'test_type': self.test_type,
            'subject_id': self.subject_id,
            'subject_name': self.subject.name if self.subject else None,
            'topic_id': self.topic_id,
            'topic_name': self.topic.name if self.topic else None,
            'duration_minutes': self.duration_minutes,
            'passing_score': float(self.passing_score),
            'total_questions': self.total_questions,
            'shuffle_questions': self.shuffle_questions,
            'shuffle_options': self.shuffle_options,
            'is_free': self.is_free,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
        }

class TestQuestion(db.Model):
    __tablename__ = 'test_questions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id', ondelete='CASCADE'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, index=True)
    order_num = db.Column(db.Integer, default=0)

    test = db.relationship('Test', back_populates='test_questions')
    question = db.relationship('Question')

class TestBlueprint(db.Model):
    __tablename__ = 'test_blueprints'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id', ondelete='CASCADE'), unique=True, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False, default=40)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    test = db.relationship('Test', back_populates='blueprint')
    rules = db.relationship('TestBlueprintRule', back_populates='blueprint', cascade='all, delete-orphan')

class TestBlueprintRule(db.Model):
    __tablename__ = 'test_blueprint_rules'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    blueprint_id = db.Column(db.Integer, db.ForeignKey('test_blueprints.id', ondelete='CASCADE'), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=True)
    difficulty = db.Column(db.String(20), default='ANY')
    questions_count = db.Column(db.Integer, nullable=False, default=10)

    blueprint = db.relationship('TestBlueprint', back_populates='rules')
    subject = db.relationship('Subject')
    topic = db.relationship('Topic')
