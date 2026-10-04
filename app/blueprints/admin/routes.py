import os
import uuid
from functools import wraps
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort, jsonify, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.user import User, UserRole
from app.models.attestation import Attestation, AttestationStatus, AttestationRegistration, RegistrationStep
from app.models.payment import Payment, PaymentStatus
from app.models.question import Subject, Topic, Question, QuestionOption, QuestionType, DifficultyLevel
from app.models.test import Test, TestBlueprint, TestBlueprintRule
from app.models.session import TestSession, SessionStatus, ProctoringEvent
from app.models.result import Result
from app.models.certificate import Certificate, CertificateStatus
from app.models.system import AuditLog, Setting
from app.services.audit_service import AuditService
from app.services.import_service import QuestionImportService
from app.services.payment_service import PaymentService
from app.services.test_engine_service import TestEngineService
from app.services.ai_service import AIService

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    today = date.today()
    
    total_users = User.query.filter_by(role=UserRole.FOYDALANUVCHI).count()
    active_attestations = Attestation.query.filter_by(status=AttestationStatus.ACTIVE).count()
    
    total_payments = Payment.query.filter_by(status=PaymentStatus.PAID).all()
    total_revenue = sum(p.amount for p in total_payments)
    
    pending_payments_count = Payment.query.filter_by(status=PaymentStatus.PENDING).count()
    active_sessions_count = TestSession.query.filter_by(status=SessionStatus.IN_PROGRESS).count()
    
    passed_count = Result.query.filter_by(is_passed=True).count()
    failed_count = Result.query.filter_by(is_passed=False).count()

    recent_sessions = TestSession.query.order_by(TestSession.started_at.desc()).limit(8).all()
    recent_payments = Payment.query.order_by(Payment.created_at.desc()).limit(8).all()
    recent_audits = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()

    stats = {
        'total_users': total_users,
        'active_attestations': active_attestations,
        'total_revenue': f"{total_revenue:,.0f} UZS".replace(',', ' '),
        'pending_payments': pending_payments_count,
        'active_sessions': active_sessions_count,
        'passed_count': passed_count,
        'failed_count': failed_count
    }

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_sessions=recent_sessions,
        recent_payments=recent_payments,
        recent_audits=recent_audits
    )

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
            User.phone.ilike(f"%{q}%")
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

    action = 'USER_ACTIVATED' if user.is_active else 'USER_BLOCKED'
    AuditService.log_action(user_id=current_user.id, action=action, entity='USER', entity_id=user.id)
    flash(f"Foydalanuvchi holati o'zgartirildi: {'Faol' if user.is_active else 'Bloklangan'}.", "success")
    return redirect(url_for('admin.users_list'))

# ==================== ATTESTATSIYALAR ====================
@admin_bp.route('/attestations')
@admin_required
def attestations_list():
    attestations = Attestation.query.order_by(Attestation.created_at.desc()).all()
    return render_template('admin/attestations.html', attestations=attestations)

@admin_bp.route('/attestations/create', methods=['GET', 'POST'])
@admin_required
def create_attestation():
    if request.method == 'POST':
        title = request.form.get('title')
        slug = request.form.get('slug') or title.lower().replace(' ', '-').replace("'", '')
        short_desc = request.form.get('short_description')
        full_desc = request.form.get('full_description')
        field_name = request.form.get('field_name')
        price = float(request.form.get('price', 0))
        duration = int(request.form.get('duration_minutes', 60))
        q_count = int(request.form.get('questions_count', 40))
        passing_score = float(request.form.get('passing_score', 60))
        status = request.form.get('status', AttestationStatus.ACTIVE)

        att = Attestation(
            title=title,
            slug=slug,
            short_description=short_desc,
            full_description=full_desc,
            field_name=field_name,
            price=price,
            duration_minutes=duration,
            questions_count=q_count,
            passing_score=passing_score,
            status=status
        )
        db.session.add(att)
        db.session.commit()

        AuditService.log_action(user_id=current_user.id, action='CREATE_ATTESTATION', entity='ATTESTATION', entity_id=att.id)
        flash("Yangi attestatsiya muvaffaqiyatli yaratildi!", "success")
        return redirect(url_for('admin.attestations_list'))

    return render_template('admin/attestation_form.html')

# ==================== SAVOLLAR BANKI ====================
@admin_bp.route('/questions')
@admin_required
def questions_list():
    subj_filter = request.args.get('subject_id')
    type_filter = request.args.get('type')
    diff_filter = request.args.get('difficulty')
    q_search = request.args.get('q', '').strip()

    query = Question.query
    if subj_filter:
        query = query.filter_by(subject_id=int(subj_filter))
    if type_filter:
        query = query.filter_by(question_type=type_filter)
    if diff_filter:
        query = query.filter_by(difficulty=diff_filter)
    if q_search:
        query = query.filter(Question.text.ilike(f"%{q_search}%"))

    questions = query.order_by(Question.created_at.desc()).limit(100).all()
    subjects = Subject.query.all()

    return render_template(
        'admin/questions.html',
        questions=questions,
        subjects=subjects,
        question_types=QuestionType.CHOICES,
        diff_choices=DifficultyLevel.CHOICES,
        current_subj=subj_filter,
        current_type=type_filter,
        current_diff=diff_filter,
        q_search=q_search
    )

@admin_bp.route('/questions/create', methods=['GET', 'POST'])
@admin_required
def create_question():
    subjects = Subject.query.all()
    topics = Topic.query.all()

    if request.method == 'POST':
        subj_id = int(request.form.get('subject_id'))
        top_id = int(request.form.get('topic_id'))
        q_type = request.form.get('question_type', QuestionType.SINGLE_CHOICE)
        text = request.form.get('text', '').strip()
        explanation = request.form.get('explanation', '').strip()
        difficulty = request.form.get('difficulty', DifficultyLevel.MEDIUM)
        points = float(request.form.get('points', 1.0))

        q_hash = Question.calculate_hash(text)
        if Question.query.filter_by(hash=q_hash).first():
            flash("Ushbu savol allaqachon savollar bankida mavjud (takroriylik aniqlandi).", "warning")
            return redirect(url_for('admin.create_question'))

        q = Question(
            subject_id=subj_id,
            topic_id=top_id,
            question_type=q_type,
            text=text,
            explanation=explanation,
            difficulty=difficulty,
            points=points,
            status='ACTIVE',
            hash=q_hash
        )
        db.session.add(q)
        db.session.flush()

        # Variantlar
        opt_texts = request.form.getlist('opt_text')
        correct_idx = request.form.get('correct_opt')

        for idx, ot in enumerate(opt_texts):
            if ot.strip():
                is_corr = (str(idx) == str(correct_idx))
                opt = QuestionOption(
                    question_id=q.id,
                    option_key=chr(65 + idx),
                    text=ot.strip(),
                    is_correct=is_corr,
                    order_index=idx
                )
                db.session.add(opt)

        db.session.commit()
        AuditService.log_action(user_id=current_user.id, action='CREATE_QUESTION', entity='QUESTION', entity_id=q.id)
        flash("Savol muvaffaqiyatli saqlandi!", "success")
        return redirect(url_for('admin.questions_list'))

    return render_template('admin/question_form.html', subjects=subjects, topics=topics, q_types=QuestionType.CHOICES)

# ==================== EXCEL VA WORD IMPORT ====================
@admin_bp.route('/import-excel', methods=['GET', 'POST'])
@admin_bp.route('/questions/import-excel', methods=['GET', 'POST'])
@admin_required
def import_excel():
    if request.method == 'POST':
        file = request.files.get('excel_file')
        if not file or not file.filename:
            flash("Iltimos, Excel faylini tanlang.", "danger")
            return redirect(url_for('admin.import_excel'))

        temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp_import.xlsx')
        file.save(temp_path)

        result = QuestionImportService.parse_excel(temp_path)
        if os.path.exists(temp_path):
            os.remove(temp_path)

        if not result['success']:
            flash(result['message'], "danger")
            return render_template('admin/import_excel.html')

        # Agar to'g'ridan to'g'ri commit berilsa yoki preview ko'rsatilsa
        if request.form.get('action') == 'commit':
            commit_res = QuestionImportService.commit_questions(result['questions'])
            flash(f"Muvaffaqiyatli import qilindi: {commit_res['imported_count']} ta savol. O'tkazib yuborilgan takroriylar: {commit_res['skipped_duplicates']} ta.", "success")
            return redirect(url_for('admin.questions_list'))

        return render_template('admin/import_excel.html', preview=result)

    return render_template('admin/import_excel.html')

@admin_bp.route('/import-word', methods=['GET', 'POST'])
@admin_bp.route('/questions/import-word', methods=['GET', 'POST'])
@admin_required
def import_word():
    if request.method == 'POST':
        file = request.files.get('word_file')
        if not file or not file.filename:
            flash("Iltimos, Word (.docx) faylini tanlang.", "danger")
            return redirect(url_for('admin.import_word'))

        temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp_import.docx')
        file.save(temp_path)

        result = QuestionImportService.parse_word(temp_path)
        if os.path.exists(temp_path):
            os.remove(temp_path)

        if not result['success']:
            flash(result['message'], "danger")
            return render_template('admin/import_word.html')

        if request.form.get('action') == 'commit':
            commit_res = QuestionImportService.commit_questions(result['questions'])
            flash(f"Word faylidan {commit_res['imported_count']} ta savol muvaffaqiyatli import qilindi.", "success")
            return redirect(url_for('admin.questions_list'))

        return render_template('admin/import_word.html', preview=result)

    return render_template('admin/import_word.html')

@admin_bp.route('/import-ai', methods=['GET', 'POST'])
@admin_bp.route('/questions/import-ai', methods=['GET', 'POST'])
@admin_required
def import_ai():
    preview = None
    if request.method == 'POST':
        raw_text = request.form.get('raw_text', '')
        action = request.form.get('action')

        if action == 'parse':
            preview = AIService.parse_unstructured_text(raw_text)
        elif action == 'commit':
            # JSON savollarni bazaga saqlash
            questions_json = request.form.get('questions_json')
            if questions_json:
                import json
                questions_data = json.loads(questions_json)
                commit_res = QuestionImportService.commit_questions(questions_data)
                flash(f"AI orqali {commit_res['imported_count']} ta savol tasdiqlandi va bazaga yozildi.", "success")
                return redirect(url_for('admin.questions_list'))

    return render_template('admin/import_ai.html', preview=preview)

# ==================== TO'LOVLAR NAZORATI ====================
@admin_bp.route('/payments')
@admin_required
def payments_list():
    status = request.args.get('status', 'PENDING')
    query = Payment.query
    if status != 'ALL':
        query = query.filter_by(status=status)
    payments = query.order_by(Payment.created_at.desc()).all()
    return render_template('admin/payments.html', payments=payments, current_status=status)

@admin_bp.route('/payments/<int:payment_id>/action', methods=['POST'])
@admin_required
def payment_action(payment_id):
    action = request.form.get('action')
    reason = request.form.get('reason', '')

    if action == 'approve':
        res = PaymentService.approve_payment(payment_id, current_user.id)
        flash(res['message'], "success" if res['success'] else "danger")
    elif action == 'reject':
        res = PaymentService.reject_payment(payment_id, current_user.id, reason)
        flash(res['message'], "warning" if res['success'] else "danger")

    return redirect(url_for('admin.payments_list'))

# ==================== TESTLAR VA BLUEPRINT ====================
@admin_bp.route('/tests')
@admin_required
def tests_list():
    tests = Test.query.order_by(Test.created_at.desc()).all()
    attestations = Attestation.query.all()
    subjects = Subject.query.all()
    return render_template('admin/tests.html', tests=tests, attestations=attestations, subjects=subjects)

@admin_bp.route('/tests/<int:test_id>/validate')
@admin_required
def test_validate(test_id):
    res = TestEngineService.validate_test(test_id)
    return jsonify(res)

@admin_bp.route('/tests/<int:test_id>/activate', methods=['POST'])
@admin_required
def activate_test(test_id):
    test = Test.query.get_or_404(test_id)
    val = TestEngineService.validate_test(test_id)
    if not val['valid']:
        flash(f"Testni faollashtirib bo'lmaydi: {'; '.join(val['reasons'])}", "danger")
    else:
        test.status = 'ACTIVE'
        db.session.commit()
        AuditService.log_action(user_id=current_user.id, action='ACTIVATE_TEST', entity='TEST', entity_id=test.id)
        flash("Test muvaffaqiyatli faollashtirildi!", "success")
    return redirect(url_for('admin.tests_list'))

# ==================== MONITORING, AUDIT VA SOZLAMALAR ====================
@admin_bp.route('/exam-sessions')
@admin_required
def exam_sessions():
    sessions = TestSession.query.order_by(TestSession.started_at.desc()).limit(50).all()
    return render_template('admin/exam_sessions.html', sessions=sessions)

@admin_bp.route('/results')
@admin_required
def results_list():
    results = Result.query.order_by(Result.created_at.desc()).all()
    return render_template('admin/results.html', results=results)

@admin_bp.route('/certificates')
@admin_required
def certificates_list():
    certificates = Certificate.query.order_by(Certificate.issue_date.desc()).all()
    return render_template('admin/certificates.html', certificates=certificates)

@admin_bp.route('/certificates/<int:cert_id>/revoke', methods=['POST'])
@admin_required
def revoke_certificate(cert_id):
    cert = Certificate.query.get_or_404(cert_id)
    reason = request.form.get('reason', 'Ma\'muriyat tomonidan bekor qilindi.')
    cert.status = CertificateStatus.REVOKED
    cert.revocation_reason = reason
    db.session.commit()
    AuditService.log_action(user_id=current_user.id, action='REVOKE_CERTIFICATE', entity='CERTIFICATE', entity_id=cert.id, new_values={'reason': reason})
    flash("Sertifikat bekor qilindi.", "warning")
    return redirect(url_for('admin.certificates_list'))

@admin_bp.route('/proctoring-events')
@admin_required
def proctoring_events():
    events = ProctoringEvent.query.order_by(ProctoringEvent.created_at.desc()).limit(100).all()
    return render_template('admin/proctoring_events.html', events=events)

@admin_bp.route('/audit-logs')
@admin_required
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(150).all()
    return render_template('admin/audit_logs.html', logs=logs)

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings_page():
    if request.method == 'POST':
        for key in ['site_name', 'support_phone', 'support_email', 'card_number', 'card_holder', 'bank_name', 'bank_account', 'mfo', 'inn']:
            val = request.form.get(key)
            if val is not None:
                Setting.set_val(key, val)
        flash("Sozlamalar saqlandi.", "success")
        return redirect(url_for('admin.settings_page'))

    return render_template('admin/settings.html')
