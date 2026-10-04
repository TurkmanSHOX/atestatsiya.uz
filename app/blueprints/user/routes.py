import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort, send_file
from flask_login import login_required, current_user
from app.extensions import db
from app.models.attestation import Attestation, AttestationRegistration, RegistrationStep, AttestationStatus
from app.models.payment import Payment, PaymentStatus
from app.models.test import Test
from app.models.session import TestSession, SessionStatus
from app.models.result import Result
from app.models.certificate import Certificate
from app.models.system import Notification
from app.services.payment_service import PaymentService
from app.services.test_engine_service import TestEngineService

user_bp = Blueprint('user', __name__)

@user_bp.route('/dashboard')
@login_required
def dashboard():
    registrations = AttestationRegistration.query.filter_by(user_id=current_user.id).order_by(AttestationRegistration.created_at.desc()).all()
    results = Result.query.filter_by(user_id=current_user.id).order_by(Result.created_at.desc()).limit(5).all()
    certificates = Certificate.query.filter_by(user_id=current_user.id).all()
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(10).all()

    # Mark notifications as read
    for n in notifications:
        n.is_read = True
    db.session.commit()

    return render_template(
        'user/dashboard.html',
        registrations=registrations,
        results=results,
        certificates=certificates,
        notifications=notifications
    )

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
                flash("Yangi parollar mos kelmadi.", "danger")
            elif len(new_pass) < 8:
                flash("Yangi parol kamida 8 ta belgidan iborat bo'lishi lozim.", "danger")
            else:
                current_user.set_password(new_pass)
                db.session.commit()
                flash("Parolingiz muvaffaqiyatli almashtirildi.", "success")
        return redirect(url_for('user.profile'))

    return render_template('user/profile.html')

@user_bp.route('/my-attestations')
@login_required
def my_attestations():
    registrations = AttestationRegistration.query.filter_by(user_id=current_user.id).order_by(AttestationRegistration.created_at.desc()).all()
    return render_template('user/my_attestations.html', registrations=registrations)

@user_bp.route('/attestation/<int:attestation_id>/apply', methods=['POST'])
@login_required
def apply_attestation(attestation_id):
    attestation = Attestation.query.get_or_404(attestation_id)
    
    # Allaqachon ariza bormi tekshirish
    existing = AttestationRegistration.query.filter_by(
        user_id=current_user.id,
        attestation_id=attestation.id
    ).filter(AttestationRegistration.step.notin_([RegistrationStep.COMPLETED, RegistrationStep.REJECTED])).first()

    if existing:
        flash("Sizda ushbu attestatsiya bo'yicha faol ariza mavjud.", "info")
        return redirect(url_for('user.attestation_payment', reg_id=existing.id))

    # Yangi ariza yaratish
    reg_number = f"REG-{datetime.utcnow().year}-{uuid.uuid4().hex[:6].upper()}"
    reg = AttestationRegistration(
        registration_number=reg_number,
        user_id=current_user.id,
        attestation_id=attestation.id,
        step=RegistrationStep.DOCUMENTS
    )
    db.session.add(reg)
    db.session.commit()

    flash("Attestatsiyaga arizangiz qabul qilindi. Endi to'lovni amalga oshiring.", "success")
    return redirect(url_for('user.attestation_payment', reg_id=reg.id))

@user_bp.route('/attestation/<int:reg_id>/payment', methods=['GET', 'POST'])
@login_required
def attestation_payment(reg_id):
    reg = AttestationRegistration.query.get_or_404(reg_id)
    if reg.user_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        receipt_file = request.files.get('receipt')
        if not receipt_file or not receipt_file.filename:
            flash("Iltimos, to'lov cheki faylini tanlang.", "danger")
            return redirect(url_for('user.attestation_payment', reg_id=reg.id))

        res = PaymentService.process_manual_receipt(
            registration_id=reg.id,
            user_id=current_user.id,
            amount=float(reg.attestation.price),
            file_obj=receipt_file,
            upload_folder=current_app.config['UPLOAD_FOLDER']
        )

        if res['success']:
            flash("To'lov cheki muvaffaqiyatli yuklandi! Administrator tekshiruvidan so'ng imtihonga ruxsat beriladi.", "success")
            return redirect(url_for('user.my_attestations'))
        else:
            flash(res['message'], "danger")

    return render_template('user/payment.html', reg=reg)

@user_bp.route('/attestation/<int:reg_id>/device-check')
@login_required
def device_check(reg_id):
    reg = AttestationRegistration.query.get_or_404(reg_id)
    if reg.user_id != current_user.id:
        abort(403)
    return render_template('user/device_check.html', reg=reg)

@user_bp.route('/attestation/<int:reg_id>/instructions')
@login_required
def exam_instructions(reg_id):
    reg = AttestationRegistration.query.get_or_404(reg_id)
    if reg.user_id != current_user.id:
        abort(403)
    return render_template('user/exam_instructions.html', reg=reg)

@user_bp.route('/attestation/<int:reg_id>/start-exam', methods=['POST'])
@login_required
def start_exam(reg_id):
    reg = AttestationRegistration.query.get_or_404(reg_id)
    if reg.user_id != current_user.id:
        abort(403)

    try:
        session = TestEngineService.start_session(
            user_id=current_user.id,
            registration_id=reg.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            device_fingerprint=request.form.get('device_fingerprint')
        )
        return redirect(url_for('user.exam_room', session_id=session.id))
    except Exception as e:
        flash(f"Imtihonni boshlab bo'lmadi: {str(e)}", "danger")
        return redirect(url_for('user.my_attestations'))

@user_bp.route('/exam/<session_id>')
@login_required
def exam_room(session_id):
    session = TestSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(403)

    if session.status != SessionStatus.IN_PROGRESS or session.is_expired:
        res = session.result or TestEngineService.finish_session(session.id, auto_expire=True)
        return redirect(url_for('user.result_detail', result_id=res.id))

    return render_template('user/exam_room.html', session=session)

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

@user_bp.route('/certificates')
@login_required
def certificates_list():
    certificates = Certificate.query.filter_by(user_id=current_user.id).order_by(Certificate.issue_date.desc()).all()
    return render_template('user/certificates.html', certificates=certificates)
