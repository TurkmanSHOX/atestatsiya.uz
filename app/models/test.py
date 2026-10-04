from datetime import datetime
from app.extensions import db

class Test(db.Model):
    __tablename__ = 'tests'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    attestation_id = db.Column(db.Integer, db.ForeignKey('attestations.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    
    duration_minutes = db.Column(db.Integer, nullable=False, default=60)
    passing_score = db.Column(db.Numeric(5, 2), nullable=False, default=60.00)
    
    shuffle_questions = db.Column(db.Boolean, default=True)
    shuffle_options = db.Column(db.Boolean, default=True)
    proctoring_enabled = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='DRAFT', index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Aloqalar
    attestation = db.relationship('Attestation', back_populates='tests')
    blueprint = db.relationship('TestBlueprint', back_populates='test', uselist=False, cascade='all, delete-orphan')
    sessions = db.relationship('TestSession', back_populates='test')

    def to_dict(self):
        return {
            'id': self.id,
            'attestation_id': self.attestation_id,
            'attestation_title': self.attestation.title if self.attestation else None,
            'title': self.title,
            'duration_minutes': self.duration_minutes,
            'passing_score': float(self.passing_score),
            'shuffle_questions': self.shuffle_questions,
            'shuffle_options': self.shuffle_options,
            'proctoring_enabled': self.proctoring_enabled,
            'status': self.status,
            'rules_count': len(self.blueprint.rules) if (self.blueprint and self.blueprint.rules) else 0,
            'total_questions': self.blueprint.total_questions if self.blueprint else 0
        }

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
