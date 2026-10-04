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
    TEXT_BASED = 'TEXT_BASED'

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
        ('FILL_BLANK', "Bo'sh joyni to'ldirish"),
        ('TEXT_BASED', "Matnli savol")
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
    name = db.Column(db.String(150), nullable=False, unique=True, index=True)
    slug = db.Column(db.String(150), nullable=False, unique=True, index=True)
    code = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    order_num = db.Column(db.Integer, default=0)
    category = db.Column(db.String(100), default='Maktab fani')
    academic_year = db.Column(db.String(20), default='2024-2025')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Aloqalar
    sections = db.relationship('SubjectSection', back_populates='subject', cascade='all, delete-orphan', order_by='SubjectSection.order_num')
    topics = db.relationship('Topic', back_populates='subject', cascade='all, delete-orphan', order_by='Topic.order_num')
    questions = db.relationship('Question', back_populates='subject')
    tests = db.relationship('Test', back_populates='subject')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'code': self.code,
            'description': self.description,
            'image_path': self.image_path,
            'is_active': self.is_active,
            'order_num': self.order_num,
            'category': self.category,
            'academic_year': self.academic_year,
            'sections_count': len(self.sections),
            'topics_count': len(self.topics),
            'questions_count': len(self.questions)
        }

class SubjectSection(db.Model):
    __tablename__ = 'subject_sections'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    order_num = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subject = db.relationship('Subject', back_populates='sections')
    topics = db.relationship('Topic', back_populates='section', cascade='all, delete-orphan')
    questions = db.relationship('Question', back_populates='section')

class Topic(db.Model):
    __tablename__ = 'topics'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False, index=True)
    section_id = db.Column(db.Integer, db.ForeignKey('subject_sections.id', ondelete='SET NULL'), nullable=True, index=True)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(50), nullable=True)
    order_num = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subject = db.relationship('Subject', back_populates='topics')
    section = db.relationship('SubjectSection', back_populates='topics')
    subtopics = db.relationship('Subtopic', back_populates='topic', cascade='all, delete-orphan')
    questions = db.relationship('Question', back_populates='topic')

    def to_dict(self):
        return {
            'id': self.id,
            'subject_id': self.subject_id,
            'subject_name': self.subject.name if self.subject else None,
            'section_id': self.section_id,
            'section_name': self.section.name if self.section else None,
            'name': self.name,
            'code': self.code,
            'is_active': self.is_active,
            'questions_count': len(self.questions)
        }

class Subtopic(db.Model):
    __tablename__ = 'subtopics'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    order_num = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    topic = db.relationship('Topic', back_populates='subtopics')
    questions = db.relationship('Question', back_populates='subtopic')

class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False, index=True)
    section_id = db.Column(db.Integer, db.ForeignKey('subject_sections.id', ondelete='SET NULL'), nullable=True, index=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=False, index=True)
    subtopic_id = db.Column(db.Integer, db.ForeignKey('subtopics.id', ondelete='SET NULL'), nullable=True, index=True)
    
    question_type = db.Column(db.String(30), nullable=False, default=QuestionType.SINGLE_CHOICE, index=True)
    text = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.String(20), default=DifficultyLevel.MEDIUM, index=True)
    points = db.Column(db.Numeric(5, 2), default=1.00)
    
    source = db.Column(db.String(255), nullable=True) # Manba
    academic_year = db.Column(db.String(20), default='2024-2025')
    tags = db.Column(db.String(255), nullable=True)
    
    status = db.Column(db.String(20), default='ACTIVE', index=True) # ACTIVE, INACTIVE
    is_approved = db.Column(db.Boolean, default=True, index=True) # Admin tasdig'i
    version = db.Column(db.Integer, default=1)
    hash = db.Column(db.String(64), nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Aloqalar
    subject = db.relationship('Subject', back_populates='questions')
    section = db.relationship('SubjectSection', back_populates='questions')
    topic = db.relationship('Topic', back_populates='questions')
    subtopic = db.relationship('Subtopic', back_populates='questions')
    options = db.relationship('QuestionOption', back_populates='question', cascade='all, delete-orphan')
    media = db.relationship('QuestionMedia', back_populates='question', cascade='all, delete-orphan')
    versions = db.relationship('QuestionVersion', back_populates='question', cascade='all, delete-orphan')

    @staticmethod
    def calculate_hash(text: str) -> str:
        clean = " ".join(text.strip().lower().split())
        return hashlib.sha256(clean.encode('utf-8')).hexdigest()

    @property
    def first_image_url(self):
        images = [m for m in self.media if m.media_type == 'IMAGE']
        if images:
            first = images[0]
            if first.file_url:
                return first.file_url
            p = first.file_path.replace('\\', '/')
            return p if p.startswith(('http', '/')) else f"/{p}"
        return None

    def get_correct_option_ids(self):
        return [opt.id for opt in self.options if opt.is_correct]

    def create_version_snapshot(self, created_by_id=None):
        """Eski holatni question_versions jadvaliga arxivlash (shu jumladan variant rasmlari)"""
        opts_data = []
        for opt in self.options:
            opt_dict = {
                'key': opt.key,
                'text': opt.text,
                'is_correct': opt.is_correct,
                'explanation': opt.explanation,
                'images': [m.to_dict() for m in opt.media]
            }
            opts_data.append(opt_dict)

        v = QuestionVersion(
            question_id=self.id,
            version_number=self.version,
            text=self.text,
            explanation=self.explanation,
            difficulty=self.difficulty,
            options_json=opts_data,
            created_by_id=created_by_id
        )
        db.session.add(v)
        self.version += 1
        return v

    def to_dict(self, include_correct=False):
        return {
            'id': self.id,
            'subject_id': self.subject_id,
            'subject_name': self.subject.name if self.subject else None,
            'section_id': self.section_id,
            'section_name': self.section.name if self.section else None,
            'topic_id': self.topic_id,
            'topic_name': self.topic.name if self.topic else None,
            'question_type': self.question_type,
            'text': self.text,
            'explanation': self.explanation,
            'difficulty': self.difficulty,
            'points': float(self.points),
            'source': self.source,
            'tags': self.tags,
            'status': self.status,
            'is_approved': self.is_approved,
            'version': self.version,
            'images': [m.to_dict() for m in self.media],
            'image_url': self.first_image_url,
            'options': [opt.to_dict(include_correct=include_correct) for opt in self.options]
        }

class QuestionVersion(db.Model):
    __tablename__ = 'question_versions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, index=True)
    version_number = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.String(20), nullable=True)
    options_json = db.Column(db.JSON, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    question = db.relationship('Question', back_populates='versions')

class QuestionOption(db.Model):
    __tablename__ = 'question_options'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, index=True)
    key = db.Column(db.String(10), nullable=False) # A, B, C, D
    text = db.Column(db.Text, nullable=True) # Rasm mavjud bo'lsa matn bo'sh bo'lishi mumkin
    is_correct = db.Column(db.Boolean, default=False)
    order_num = db.Column(db.Integer, default=0)
    explanation = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    question = db.relationship('Question', back_populates='options')
    media = db.relationship('QuestionOptionMedia', back_populates='option', cascade='all, delete-orphan')

    @property
    def first_image_url(self):
        if self.media:
            first = self.media[0]
            if first.file_url:
                return first.file_url
            p = first.file_path.replace('\\', '/')
            return p if p.startswith(('http', '/')) else f"/{p}"
        return None

    def to_dict(self, include_correct=False):
        d = {
            'id': self.id,
            'key': self.key,
            'text': self.text or '',
            'explanation': self.explanation,
            'images': [m.to_dict() for m in self.media],
            'image_url': self.first_image_url,
            'has_image': len(self.media) > 0
        }
        if include_correct:
            d['is_correct'] = self.is_correct
        return d

class QuestionOptionMedia(db.Model):
    __tablename__ = 'question_option_media'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    option_id = db.Column(db.Integer, db.ForeignKey('question_options.id', ondelete='CASCADE'), nullable=False, index=True)
    file_path = db.Column(db.String(255), nullable=False)
    file_url = db.Column(db.String(255), nullable=True)
    original_name = db.Column(db.String(255), nullable=True)
    mime_type = db.Column(db.String(100), nullable=True)
    file_size = db.Column(db.Integer, nullable=True) # Baytlarda
    media_type = db.Column(db.String(20), default='IMAGE') # IMAGE, etc.
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    option = db.relationship('QuestionOption', back_populates='media')

    def to_dict(self):
        p = self.file_path.replace('\\', '/')
        url = self.file_url or (p if p.startswith(('http', '/')) else f"/{p}")
        return {
            'id': self.id,
            'option_id': self.option_id,
            'file_path': self.file_path,
            'file_url': url,
            'original_name': self.original_name,
            'mime_type': self.mime_type,
            'file_size': self.file_size,
            'media_type': self.media_type,
            'sort_order': self.sort_order
        }

class QuestionMedia(db.Model):
    __tablename__ = 'question_media'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, index=True)
    media_type = db.Column(db.String(20), nullable=False, default='IMAGE') # IMAGE, AUDIO, VIDEO
    file_path = db.Column(db.String(255), nullable=False)
    file_url = db.Column(db.String(255), nullable=True)
    original_name = db.Column(db.String(255), nullable=True)
    mime_type = db.Column(db.String(100), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    caption = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    question = db.relationship('Question', back_populates='media')

    def to_dict(self):
        p = self.file_path.replace('\\', '/')
        url = self.file_url or (p if p.startswith(('http', '/')) else f"/{p}")
        return {
            'id': self.id,
            'question_id': self.question_id,
            'media_type': self.media_type,
            'file_path': self.file_path,
            'file_url': url,
            'caption': self.caption
        }
