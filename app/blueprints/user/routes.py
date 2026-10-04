import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.question import Subject, Topic, Question
from app.models.test import Test, TestType
from app.models.session import TestSession, SessionStatus
from app.models.result import Result, UserQuestionStat, UserTopicStat
from app.models.package import Package, Order, Payment
from app.services.analytics_service import AnalyticsService
from app.services.test_engine_service import TestEngineService
from app.services.payment_service import PaymentService

user_bp = Blueprint('user', __name__)

@user_bp.route('/dashboard')
@login_required
def dashboard():
    stats = AnalyticsService.get_user_dashboard_stats(current_user.id)
    return render_template('user/dashboard.html', stats=stats)

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_profile':
            current_user.first_name = request.form.get('first_name', current_user.first_name).strip()
            current_user.last_name = request.form.get('last_name', current_user.last_name).strip()
            current_user.middle_name = request.form.get('middle_name', '').strip()
            current_user.organization = request.form.get('organization', '').strip()
            current_user.position = request.form.get('position', '').strip()
            current_user.specialty = request.form.get('specialty', '').strip()
            current_user.region = request.form.get('region', '').strip()
            db.session.commit()
            flash("Profilingiz muvaffaqiyatli yangilandi.", "success")
        elif action == 'change_password':
            old_pass = request.form.get('old_password')
            new_pass = request.form.get('new_password')
            confirm = request.form.get('confirm_password')

            if not current_user.check_password(old_pass):
                flash("Amaldagi parol noto'g'ri kiritildi.", "danger")
            elif new_pass != confirm:
                flash("Yangi parollar bir-biriga mos kelmadi.", "danger")
            elif len(new_pass) < 6:
                flash("Yangi parol kamida 6 ta belgidan iborat bo'lishi lozim.", "danger")
            else:
                current_user.set_password(new_pass)
                db.session.commit()
                flash("Parolingiz muvaffaqiyatli yangilandi.", "success")
        return redirect(url_for('user.profile'))

    return render_template('user/profile.html')

# ==================== TESTLAR KATALOGI VA ISHLASH ====================

@user_bp.route('/tests')
@login_required
def tests_catalog():
    subjects = Subject.query.filter_by(is_active=True).order_by(Subject.order_num).all()
    tests = Test.query.filter_by(status='ACTIVE').all()
    return render_template('user/tests.html', subjects=subjects, tests=tests)

@user_bp.route('/tests/subject/<int:subject_id>')
@login_required
def subject_tests(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    tests = Test.query.filter_by(subject_id=subject.id, status='ACTIVE').all()
    topics = Topic.query.filter_by(subject_id=subject.id, is_active=True).order_by(Topic.order_num).all()
    
    # Har bir mavzu bo'yicha foydalanuvchi statistikasini olish
    topic_stats = {ts.topic_id: ts for ts in current_user.topic_stats if ts.topic.subject_id == subject.id}
    
    return render_template('user/subject_tests.html', subject=subject, tests=tests, topics=topics, topic_stats=topic_stats)

@user_bp.route('/tests/start/<int:test_id>', methods=['POST', 'GET'])
@login_required
def start_test(test_id):
    test = Test.query.get_or_404(test_id)

    try:
        session = TestEngineService.start_session(
            user_id=current_user.id,
            test_id=test.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        return redirect(url_for('user.exam_room', session_id=session.id))
    except ValueError as e:
        flash(str(e), "warning")
        if "paket" in str(e).lower() or "obuna" in str(e).lower():
            return redirect(url_for('user.packages_list'))
        return redirect(url_for('user.tests_catalog'))

@user_bp.route('/tests/simulation/<int:subject_id>', methods=['POST'])
@login_required
def start_simulation(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    
    # Simulyatsiya testi bormi yoki yangi yaratish
    sim_test = Test.query.filter_by(subject_id=subject.id, test_type=TestType.SIMULYATSIYA, status='ACTIVE').first()
    if not sim_test:
        sim_test = Test(
            title=f"{subject.name} - Attestatsiya simulyatsiyasi",
            test_type=TestType.SIMULYATSIYA,
            subject_id=subject.id,
            duration_minutes=90,
            passing_score=60.0,
            total_questions=50,
            shuffle_questions=True,
            shuffle_options=True,
            is_free=False,
            status='ACTIVE'
        )
        db.session.add(sim_test)
        db.session.commit()

    return redirect(url_for('user.start_test', test_id=sim_test.id))

@user_bp.route('/tests/mistakes')
@login_required
def mistakes_view():
    mistakes = UserQuestionStat.query.filter_by(user_id=current_user.id, is_last_correct=False).all()
    return render_template('user/mistakes.html', mistakes=mistakes)

@user_bp.route('/tests/mistakes/create-test', methods=['POST'])
@login_required
def create_mistakes_test():
    mistakes_count = UserQuestionStat.query.filter_by(user_id=current_user.id, is_last_correct=False).count()
    if mistakes_count == 0:
        flash("Sizda xato ishlangan savollar mavjud emas. Ajoyib natija!", "info")
        return redirect(url_for('user.dashboard'))

    # Xatolarim testi yaratish
    test = Test(
        title="Xatolarim ustida ishlash testi",
        test_type=TestType.XATOLAR,
        duration_minutes=min(60, max(15, mistakes_count * 2)),
        passing_score=70.0,
        total_questions=min(mistakes_count, 30),
        shuffle_questions=True,
        shuffle_options=True,
        is_free=True, # Xatolarni qayta ishlash bepul
        status='ACTIVE'
    )
    db.session.add(test)
    db.session.commit()

    return redirect(url_for('user.start_test', test_id=test.id))

@user_bp.route('/tests/weak-topics')
@login_required
def weak_topics_view():
    weak_topics = AnalyticsService.get_weak_topics(current_user.id)
    return render_template('user/weak_topics.html', weak_topics=weak_topics)

@user_bp.route('/tests/weak-topics/create-test', methods=['POST'])
@login_required
def create_weak_topics_test():
    weak_topics = AnalyticsService.get_weak_topics(current_user.id)
    if not weak_topics:
        flash("Sizda zaif mavzular aniqlanmadi!", "info")
        return redirect(url_for('user.dashboard'))

    test = Test(
        title="Zaif mavzularni mustahkamlash testi",
        test_type=TestType.ZAIF_MAVZULAR,
        duration_minutes=45,
        passing_score=65.0,
        total_questions=25,
        shuffle_questions=True,
        shuffle_options=True,
        is_free=True,
        status='ACTIVE'
    )
    db.session.add(test)
    db.session.commit()

    return redirect(url_for('user.start_test', test_id=test.id))

@user_bp.route('/exam/<session_id>')
@login_required
def exam_room(session_id):
    session = TestSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(403)

    if session.status != SessionStatus.IN_PROGRESS or session.is_expired:
        res = TestEngineService.finish_session(session.id, auto_expire=True)
        return redirect(url_for('user.result_detail', result_id=res.id))

    return render_template('user/exam_room.html', session=session)

# ==================== NATIJALAR ====================

@user_bp.route('/results')
@login_required
def results_list():
    results = Result.query.filter_by(user_id=current_user.id).order_by(Result.created_at.desc()).all()
    return render_template('user/results.html', results=results)

@user_bp.route('/results/<int:result_id>')
@login_required
def result_detail(result_id):
    result = Result.query.get_or_404(result_id)
    if result.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    return render_template('user/result_detail.html', result=result)

# ==================== PAKETLAR VA TO'LOV ====================

@user_bp.route('/packages')
@login_required
def packages_list():
    packages = Package.query.filter_by(is_active=True).order_by(Package.order_num).all()
    entitlement = current_user.get_active_entitlement()
    return render_template('user/packages.html', packages=packages, active_entitlement=entitlement)

@user_bp.route('/packages/buy/<int:package_id>', methods=['POST', 'GET'])
@login_required
def buy_package(package_id):
    package = Package.query.get_or_404(package_id)

    order = PaymentService.create_order(
        user_id=current_user.id,
        package_id=package.id
    )

    # Click to'lov URL manzilini yaratish
    click_url = PaymentService.generate_click_url(order.id)
    return render_template('user/checkout.html', package=package, order=order, click_url=click_url)
