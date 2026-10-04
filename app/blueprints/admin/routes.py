import os
import re
from functools import wraps
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.user import User, UserRole
from app.models.question import Subject, SubjectSection, Topic, Subtopic, Question, QuestionOption, QuestionType, DifficultyLevel
from app.models.test import Test, TestType, TestBlueprint, TestBlueprintRule
from app.models.session import TestSession, SessionStatus
from app.models.result import Result
from app.models.package import Package, Order, Payment, Entitlement, OrderStatus, PaymentStatus
from app.models.system import AuditLog, Setting, TelegramUser
from app.services.audit_service import AuditService
from app.services.import_service import QuestionImportService
from app.services.ai_service import AIService
from app.services.telegram_service import TelegramService
from app.services.test_engine_service import TestEngineService

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# ==================== DASHBOARD ====================
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    today = date.today()
    start_today = datetime.combine(today, datetime.min.time())
    start_week = start_today - timedelta(days=7)
    start_month = start_today - timedelta(days=30)
    
    # Foydalanuvchilar
    total_users = User.query.filter_by(role=UserRole.FOYDALANUVCHI).count()
    today_users = User.query.filter_by(role=UserRole.FOYDALANUVCHI).filter(User.created_at >= start_today).count()
    active_users = User.query.filter_by(role=UserRole.FOYDALANUVCHI, is_active=True).count()
    
    # Testlar
    total_tests = Test.query.count()
    total_completed_tests = Result.query.count()
    today_tests = Result.query.filter(Result.created_at >= start_today).count()
    
    # Tushum (Click)
    paid_payments = Payment.query.filter_by(status=PaymentStatus.PAID).all()
    total_revenue = sum(p.amount for p in paid_payments)
    
    today_revenue = sum(p.amount for p in paid_payments if p.created_at >= start_today)
    week_revenue = sum(p.amount for p in paid_payments if p.created_at >= start_week)
    month_revenue = sum(p.amount for p in paid_payments if p.created_at >= start_month)
    
    pending_payments_count = Payment.query.filter_by(status=PaymentStatus.PENDING).count()
    active_sessions_count = TestSession.query.filter_by(status=SessionStatus.IN_PROGRESS).count()

    total_questions = Question.query.count()
    total_subjects = Subject.query.count()
    total_topics = Topic.query.count()

    recent_results = Result.query.order_by(Result.created_at.desc()).limit(8).all()
    recent_payments = Payment.query.order_by(Payment.created_at.desc()).limit(8).all()
    recent_audits = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()

    stats = {
        'total_users': total_users,
        'today_users': today_users,
        'active_users': active_users,
        'total_tests': total_tests,
        'total_completed_tests': total_completed_tests,
        'today_tests': today_tests,
        'total_questions': total_questions,
        'total_subjects': total_subjects,
        'total_topics': total_topics,
        'total_revenue': f"{total_revenue:,.0f} UZS".replace(',', ' '),
        'today_revenue': f"{today_revenue:,.0f} UZS".replace(',', ' '),
        'week_revenue': f"{week_revenue:,.0f} UZS".replace(',', ' '),
        'month_revenue': f"{month_revenue:,.0f} UZS".replace(',', ' '),
        'pending_payments': pending_payments_count,
        'active_sessions': active_sessions_count
    }

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_results=recent_results,
        recent_payments=recent_payments,
        recent_audits=recent_audits
    )

# ==================== FANLAR (SUBJECTS) ====================
@admin_bp.route('/subjects')
@admin_required
def subjects_list():
    subjects = Subject.query.order_by(Subject.order_num).all()
    return render_template('admin/subjects.html', subjects=subjects)

@admin_bp.route('/subjects/create', methods=['GET', 'POST'])
@admin_required
def subject_create():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        slug = request.form.get('slug', '').strip().lower()
        if not slug:
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

        if Subject.query.filter((Subject.name == name) | (Subject.slug == slug)).first():
            flash("Ushbu nomdagi yoki slugdagi fan allaqachon mavjud.", "danger")
            return render_template('admin/subject_form.html', subject=None)

        subject = Subject(
            name=name,
            slug=slug,
            code=request.form.get('code', '').strip(),
            category=request.form.get('category', 'Maktab fani').strip(),
            academic_year=request.form.get('academic_year', '2024-2025').strip(),
            order_num=int(request.form.get('order_num', 0)),
            is_active=bool(request.form.get('is_active', True)),
            description=request.form.get('description', '').strip()
        )
        db.session.add(subject)
        db.session.commit()

        AuditService.log_action(user_id=current_user.id, action='CREATE', entity='SUBJECT', entity_id=subject.id)
        flash("Fan muvaffaqiyatli qo'shildi.", "success")
        return redirect(url_for('admin.subjects_list'))

    return render_template('admin/subject_form.html', subject=None)

@admin_bp.route('/subjects/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def subject_edit(id):
    subject = Subject.query.get_or_404(id)
    if request.method == 'POST':
        subject.name = request.form.get('name', '').strip()
        subject.slug = request.form.get('slug', '').strip().lower()
        subject.code = request.form.get('code', '').strip()
        subject.category = request.form.get('category', 'Maktab fani').strip()
        subject.academic_year = request.form.get('academic_year', '2024-2025').strip()
        subject.order_num = int(request.form.get('order_num', 0))
        subject.is_active = bool(request.form.get('is_active'))
        subject.description = request.form.get('description', '').strip()
        
        db.session.commit()
        AuditService.log_action(user_id=current_user.id, action='UPDATE', entity='SUBJECT', entity_id=subject.id)
        flash("Fan muvaffaqiyatli tahrirlandi.", "success")
        return redirect(url_for('admin.subjects_list'))

    return render_template('admin/subject_form.html', subject=subject)

@admin_bp.route('/subjects/<int:id>/toggle-status', methods=['POST'])
@admin_required
def subject_toggle(id):
    subject = Subject.query.get_or_404(id)
    subject.is_active = not subject.is_active
    db.session.commit()
    AuditService.log_action(user_id=current_user.id, action='TOGGLE_STATUS', entity='SUBJECT', entity_id=subject.id)
    flash(f"'{subject.name}' holati yangilandi.", "success")
    return redirect(url_for('admin.subjects_list'))

# ==================== BO'LIMLAR VA MAVZULAR ====================
@admin_bp.route('/subjects/<int:subject_id>/topics')
@admin_required
def subject_topics(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    sections = SubjectSection.query.filter_by(subject_id=subject.id).order_by(SubjectSection.order_num).all()
    topics = Topic.query.filter_by(subject_id=subject.id).order_by(Topic.order_num).all()
    return render_template('admin/topics.html', subject=subject, sections=sections, topics=topics)

@admin_bp.route('/subjects/<int:subject_id>/topics/create', methods=['POST'])
@admin_required
def topic_create(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    name = request.form.get('name', '').strip()
    section_id = request.form.get('section_id')
    section_id = int(section_id) if section_id and section_id.isdigit() else None
    
    if name:
        topic = Topic(
            subject_id=subject.id,
            section_id=section_id,
            name=name,
            code=request.form.get('code', '').strip(),
            order_num=int(request.form.get('order_num', 0))
        )
        db.session.add(topic)
        db.session.commit()
        AuditService.log_action(user_id=current_user.id, action='CREATE', entity='TOPIC', entity_id=topic.id)
        flash("Mavzu muvaffaqiyatli qo'shildi.", "success")
    return redirect(url_for('admin.subject_topics', subject_id=subject.id))

@admin_bp.route('/subjects/<int:subject_id>/sections/create', methods=['POST'])
@admin_required
def section_create(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    name = request.form.get('name', '').strip()
    if name:
        sec = SubjectSection(
            subject_id=subject.id,
            name=name,
            order_num=int(request.form.get('order_num', 0))
        )
        db.session.add(sec)
        db.session.commit()
        flash("Bo'lim muvaffaqiyatli qo'shildi.", "success")
    return redirect(url_for('admin.subject_topics', subject_id=subject.id))

# ==================== SAVOLLAR BANKI ====================
@admin_bp.route('/questions')
@admin_required
def questions_list():
    q = request.args.get('q', '').strip()
    subject_id = request.args.get('subject_id')
    topic_id = request.args.get('topic_id')
    difficulty = request.args.get('difficulty')
    q_type = request.args.get('question_type')
    status_filter = request.args.get('status')

    query = Question.query
    if q:
        query = query.filter(Question.text.ilike(f"%{q}%"))
    if subject_id and subject_id.isdigit():
        query = query.filter_by(subject_id=int(subject_id))
    if topic_id and topic_id.isdigit():
        query = query.filter_by(topic_id=int(topic_id))
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    if q_type:
        query = query.filter_by(question_type=q_type)
    if status_filter:
        query = query.filter_by(status=status_filter)

    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(Question.created_at.desc()).paginate(page=page, per_page=20, error_out=False)

    subjects = Subject.query.filter_by(is_active=True).all()
    topics = Topic.query.filter_by(subject_id=int(subject_id)).all() if (subject_id and subject_id.isdigit()) else []

    return render_template(
        'admin/questions.html',
        questions=pagination.items,
        pagination=pagination,
        subjects=subjects,
        topics=topics,
        current_subject_id=subject_id,
        current_topic_id=topic_id,
        current_difficulty=difficulty,
        current_type=q_type,
        q=q
    )

@admin_bp.route('/questions/create', methods=['GET', 'POST'])
@admin_required
def question_create():
    if request.method == 'POST':
        subject_id = int(request.form.get('subject_id'))
        topic_id = int(request.form.get('topic_id'))
        q_type = request.form.get('question_type', QuestionType.SINGLE_CHOICE)
        text = request.form.get('text', '').strip()
        explanation = request.form.get('explanation', '').strip()
        difficulty = request.form.get('difficulty', DifficultyLevel.MEDIUM)
        source = request.form.get('source', '').strip()

        q_hash = Question.calculate_hash(text)
        existing = Question.query.filter_by(hash=q_hash).first()
        if existing:
            flash("Ogohlantirish: Ushbu savol matni bazada allaqachon mavjud!", "warning")

        question = Question(
            subject_id=subject_id,
            topic_id=topic_id,
            question_type=q_type,
            text=text,
            explanation=explanation,
            difficulty=difficulty,
            source=source,
            status='ACTIVE',
            is_approved=True,
            version=1,
            hash=q_hash
        )
        db.session.add(question)
        db.session.flush()

        # Variantlar
        option_texts = request.form.getlist('option_text[]')
        option_keys = request.form.getlist('option_key[]')
        correct_key = request.form.get('correct_option')
        correct_keys_multi = request.form.getlist('correct_options_multi[]')

        for key, opt_text in zip(option_keys, option_texts):
            if opt_text.strip():
                is_corr = (key == correct_key) if q_type == QuestionType.SINGLE_CHOICE else (key in correct_keys_multi)
                opt = QuestionOption(
                    question_id=question.id,
                    key=key,
                    text=opt_text.strip(),
                    is_correct=is_corr
                )
                db.session.add(opt)

        db.session.commit()
        AuditService.log_action(user_id=current_user.id, action='CREATE', entity='QUESTION', entity_id=question.id)
        flash("Savol muvaffaqiyatli saqlandi.", "success")
        return redirect(url_for('admin.questions_list'))

    subjects = Subject.query.filter_by(is_active=True).all()
    return render_template('admin/question_form.html', question=None, subjects=subjects)

@admin_bp.route('/questions/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def question_edit(id):
    question = Question.query.get_or_404(id)
    if request.method == 'POST':
        # 1. Eski versiyani arxivlash (Question Versioning)
        question.create_version_snapshot(created_by_id=current_user.id)

        question.subject_id = int(request.form.get('subject_id'))
        question.topic_id = int(request.form.get('topic_id'))
        question.question_type = request.form.get('question_type')
        question.text = request.form.get('text', '').strip()
        question.explanation = request.form.get('explanation', '').strip()
        question.difficulty = request.form.get('difficulty')
        question.source = request.form.get('source', '').strip()
        question.hash = Question.calculate_hash(question.text)

        # Variantlarni yangilash
        QuestionOption.query.filter_by(question_id=question.id).delete()

        option_texts = request.form.getlist('option_text[]')
        option_keys = request.form.getlist('option_key[]')
        correct_key = request.form.get('correct_option')
        correct_keys_multi = request.form.getlist('correct_options_multi[]')

        for key, opt_text in zip(option_keys, option_texts):
            if opt_text.strip():
                is_corr = (key == correct_key) if question.question_type == QuestionType.SINGLE_CHOICE else (key in correct_keys_multi)
                opt = QuestionOption(
                    question_id=question.id,
                    key=key,
                    text=opt_text.strip(),
                    is_correct=is_corr
                )
                db.session.add(opt)

        db.session.commit()
        AuditService.log_action(user_id=current_user.id, action='UPDATE', entity='QUESTION', entity_id=question.id)
        flash(f"Savol yangilandi (Yangi versiya: {question.version}).", "success")
        return redirect(url_for('admin.questions_list'))

    subjects = Subject.query.filter_by(is_active=True).all()
    topics = Topic.query.filter_by(subject_id=question.subject_id).all()
    return render_template('admin/question_form.html', question=question, subjects=subjects, topics=topics)

@admin_bp.route('/questions/batch', methods=['POST'])
@admin_required
def questions_batch_action():
    """Savollar ustida ommaviy amallar (Massive actions)"""
    action = request.form.get('batch_action')
    q_ids = request.form.getlist('question_ids[]')

    if not q_ids:
        flash("Hech qanday savol tanlanmadi.", "warning")
        return redirect(url_for('admin.questions_list'))

    q_ids = [int(i) for i in q_ids if i.isdigit()]

    if action == 'delete':
        Question.query.filter(Question.id.in_(q_ids)).delete(synchronize_session=False)
        db.session.commit()
        flash(f"{len(q_ids)} ta savol o'chirildi.", "success")
    elif action == 'activate':
        Question.query.filter(Question.id.in_(q_ids)).update({'status': 'ACTIVE'}, synchronize_session=False)
        db.session.commit()
        flash(f"{len(q_ids)} ta savol faollashtirildi.", "success")
    elif action == 'deactivate':
        Question.query.filter(Question.id.in_(q_ids)).update({'status': 'INACTIVE'}, synchronize_session=False)
        db.session.commit()
        flash(f"{len(q_ids)} ta savol faol emas holatga o'tkazildi.", "info")

    return redirect(url_for('admin.questions_list'))

# ==================== IMPORT MODULLARI ====================
@admin_bp.route('/import-excel', methods=['GET', 'POST'])
@admin_required
def import_excel():
    if request.method == 'POST':
        file = request.files.get('file') or request.files.get('excel_file')
        if not file or file.filename == '':
            flash("Iltimos, Excel faylni tanlang.", "danger")
            return redirect(url_for('admin.import_excel'))

        filename = secure_filename(file.filename)
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)

        parse_result = QuestionImportService.parse_excel(save_path)
        subjects = Subject.query.filter_by(is_active=True).all()
        return render_template('admin/import_excel_preview.html', result=parse_result, subjects=subjects, filename=filename)

    return render_template('admin/import_excel.html')

@admin_bp.route('/import-word', methods=['GET', 'POST'])
@admin_required
def import_word():
    if request.method == 'POST':
        file = request.files.get('file') or request.files.get('word_file')
        if not file or file.filename == '':
            flash("Iltimos, Word (.docx) faylni tanlang.", "danger")
            return redirect(url_for('admin.import_word'))

        filename = secure_filename(file.filename)
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)

        parse_result = QuestionImportService.parse_word(save_path)
        subjects = Subject.query.filter_by(is_active=True).all()
        return render_template('admin/import_word_preview.html', result=parse_result, subjects=subjects, filename=filename)

    return render_template('admin/import_word.html')

@admin_bp.route('/import-ai', methods=['GET', 'POST'])
@admin_required
def import_ai():
    if request.method == 'POST':
        text_content = request.form.get('raw_text', '').strip()
        file = request.files.get('file')

        if file and file.filename:
            filename = secure_filename(file.filename)
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            if filename.endswith('.docx'):
                from docx import Document
                doc = Document(save_path)
                text_content = "\n".join(p.text for p in doc.paragraphs)
            elif filename.endswith('.txt'):
                with open(save_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text_content = f.read()

        if not text_content:
            flash("Iltimos, tahlil qilish uchun matn kiriting yoki fayl yuklang.", "warning")
            return redirect(url_for('admin.import_ai'))

        parse_result = AIService.parse_unstructured_text(text_content)
        subjects = Subject.query.filter_by(is_active=True).all()
        return render_template('admin/import_ai_preview.html', result=parse_result, subjects=subjects)

    return render_template('admin/import_ai.html')

@admin_bp.route('/import/confirm', methods=['POST'])
@admin_required
def import_confirm():
    import json
    questions_json = request.form.get('questions_json')
    subject_id = request.form.get('default_subject_id')
    topic_id = request.form.get('default_topic_id')

    subject_id = int(subject_id) if subject_id and subject_id.isdigit() else None
    topic_id = int(topic_id) if topic_id and topic_id.isdigit() else None

    try:
        questions_list = json.loads(questions_json)
        res = QuestionImportService.save_imported_questions(questions_list, default_subject_id=subject_id, default_topic_id=topic_id)
        flash(f"Muvaffaqiyatli saqlandi: {res['imported']} ta savol. O'tkazib yuborildi (duplikat): {res['skipped']} ta.", "success")
    except Exception as e:
        flash(f"Saqlashda xatolik: {e}", "danger")

    return redirect(url_for('admin.questions_list'))

# ==================== TESTLAR VA BLUEPRINT ====================
@admin_bp.route('/tests')
@admin_required
def tests_list():
    tests = Test.query.all()
    subjects = Subject.query.filter_by(is_active=True).all()
    return render_template('admin/tests.html', tests=tests, subjects=subjects)

@admin_bp.route('/tests/create', methods=['POST'])
@admin_required
def test_create():
    title = request.form.get('title', '').strip()
    test_type = request.form.get('test_type', TestType.FAN)
    subject_id = request.form.get('subject_id')
    subject_id = int(subject_id) if subject_id and subject_id.isdigit() else None
    topic_id = request.form.get('topic_id')
    topic_id = int(topic_id) if topic_id and topic_id.isdigit() else None
    duration = int(request.form.get('duration_minutes', 60))
    passing_score = float(request.form.get('passing_score', 60.0))
    total_q = int(request.form.get('total_questions', 30))
    is_free = bool(request.form.get('is_free'))

    test = Test(
        title=title,
        test_type=test_type,
        subject_id=subject_id,
        topic_id=topic_id,
        duration_minutes=duration,
        passing_score=passing_score,
        total_questions=total_q,
        is_free=is_free,
        status='ACTIVE'
    )
    db.session.add(test)
    db.session.commit()
    AuditService.log_action(user_id=current_user.id, action='CREATE', entity='TEST', entity_id=test.id)
    flash("Test muvaffaqiyatli yaratildi.", "success")
    return redirect(url_for('admin.tests_list'))

@admin_bp.route('/tests/<int:id>/toggle-status', methods=['POST'])
@admin_required
def test_toggle(id):
    test = Test.query.get_or_404(id)
    test.status = 'INACTIVE' if test.status == 'ACTIVE' else 'ACTIVE'
    db.session.commit()
    AuditService.log_action(user_id=current_user.id, action='TOGGLE_STATUS', entity='TEST', entity_id=test.id)
    flash(f"'{test.title}' holati o'zgartirildi.", "success")
    return redirect(url_for('admin.tests_list'))

@admin_bp.route('/tests/<int:id>/delete', methods=['POST'])
@admin_required
def test_delete(id):
    test = Test.query.get_or_404(id)
    db.session.delete(test)
    db.session.commit()
    AuditService.log_action(user_id=current_user.id, action='DELETE', entity='TEST', entity_id=id)
    flash("Test o'chirildi.", "success")
    return redirect(url_for('admin.tests_list'))

# ==================== PAKETLAR (PACKAGES) ====================
@admin_bp.route('/packages')
@admin_required
def packages_list():
    packages = Package.query.order_by(Package.order_num).all()
    return render_template('admin/packages.html', packages=packages)

@admin_bp.route('/packages/create', methods=['GET', 'POST'])
@admin_required
def package_create():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        slug = request.form.get('slug', '').strip().lower()
        if not slug:
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

        price = float(request.form.get('price', 10000.0))
        duration = int(request.form.get('duration_days', 30))
        test_limit = request.form.get('test_limit')
        test_limit = int(test_limit) if test_limit and test_limit.isdigit() else None
        is_all = bool(request.form.get('is_all_subjects', True))
        features_str = request.form.get('features', '')
        features = [f.strip() for f in features_str.split('\n') if f.strip()]

        package = Package(
            name=name,
            slug=slug,
            description=request.form.get('description', '').strip(),
            price=price,
            duration_days=duration,
            test_limit=test_limit,
            is_all_subjects=is_all,
            features=features,
            is_active=bool(request.form.get('is_active', True))
        )
        db.session.add(package)
        db.session.commit()
        flash("Paket muvaffaqiyatli yaratildi.", "success")
        return redirect(url_for('admin.packages_list'))

    return render_template('admin/package_form.html', package=None)

# ==================== TO'LOVLAR VA BUYURTMALAR ====================
@admin_bp.route('/payments')
@admin_required
def payments_list():
    payments = Payment.query.order_by(Payment.created_at.desc()).all()
    return render_template('admin/payments.html', payments=payments)

# ==================== FOYDALANUVCHILAR ====================
@admin_bp.route('/users')
@admin_required
def users_list():
    q = request.args.get('q', '').strip()
    status_filter = request.args.get('status')

    query = User.query.filter_by(role=UserRole.FOYDALANUVCHI)
    if q:
        query = query.filter(
            User.first_name.ilike(f"%{q}%") |
            User.last_name.ilike(f"%{q}%") |
            User.email.ilike(f"%{q}%") |
            User.phone.ilike(f"%{q}%") |
            User.organization.ilike(f"%{q}%")
        )
    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'blocked':
        query = query.filter_by(is_active=False)

    users = query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users, q=q, status_filter=status_filter)

@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    AuditService.log_action(user_id=current_user.id, action='TOGGLE_STATUS', entity='USER', entity_id=user.id)
    flash(f"'{user.full_name}' foydalanuvchisi holati o'zgartirildi.", "success")
    return redirect(url_for('admin.users_list'))

# ==================== TELEGRAM SOZLAMALARI ====================
@admin_bp.route('/telegram', methods=['GET', 'POST'])
@admin_required
def telegram_settings():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'save_settings':
            Setting.set_val('telegram_bot_token', request.form.get('bot_token', '').strip())
            Setting.set_val('telegram_admin_chat_id', request.form.get('admin_chat_id', '').strip())
            flash("Telegram sozlamalari saqlandi.", "success")
        elif action == 'test_message':
            user = current_user
            pkg = Package.query.first()
            pmt = Payment.query.first()
            if pkg and pmt:
                ok = TelegramService.send_payment_notification(user, pkg, pmt)
                if ok:
                    flash("Sinov xabari Telegram guruhga/adminga muvaffaqiyatli yuborildi!", "success")
                else:
                    flash("Xabar yuborishda xatolik. Bot token va Chat ID ni tekshiring.", "warning")
            else:
                flash("Sinov uchun bazada paket yoki to'lov mavjud emas.", "info")
        return redirect(url_for('admin.telegram_settings'))

    bot_token = Setting.get_val('telegram_bot_token', current_app.config.get('TELEGRAM_BOT_TOKEN', ''))
    chat_id = Setting.get_val('telegram_admin_chat_id', current_app.config.get('TELEGRAM_ADMIN_CHAT_ID', ''))
    return render_template('admin/telegram.html', bot_token=bot_token, chat_id=chat_id)

# ==================== AUDIT VA SOZLAMALAR ====================
@admin_bp.route('/audit-logs')
@admin_required
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()
    return render_template('admin/audit_logs.html', logs=logs)

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings_page():
    if request.method == 'POST':
        for key in ['site_name', 'support_phone', 'support_email', 'click_merchant_id', 'click_service_id', 'click_secret_key']:
            val = request.form.get(key, '').strip()
            Setting.set_val(key, val)
        flash("Sozlamalar muvaffaqiyatli saqlandi.", "success")
        return redirect(url_for('admin.settings_page'))

    settings = {s.key_name: s.value_text for s in Setting.query.all()}
    return render_template('admin/settings.html', settings=settings)
