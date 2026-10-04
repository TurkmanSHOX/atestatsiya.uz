from flask import Blueprint, jsonify, request
from flask_login import current_user, login_user
from app.models.user import User
from app.models.attestation import Attestation
from app.models.session import TestSession
from app.services.test_engine_service import TestEngineService
from app.services.proctoring_service import ProctoringService
from app.services.certificate_service import CertificateService

api_bp = Blueprint('api', __name__)

@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    login_id = data.get('login', '').strip()
    password = data.get('password', '')

    user = User.query.filter((User.email == login_id.lower()) | (User.phone == login_id)).first()
    if user and user.check_password(password):
        if not user.is_active:
            return jsonify({'success': False, 'message': "Hisob bloklangan"}), 403
        login_user(user)
        return jsonify({'success': True, 'user': user.to_dict()})
    return jsonify({'success': False, 'message': "Noto'g'ri login yoki parol"}), 401

@api_bp.route('/attestations', methods=['GET'])
def api_attestations():
    attestations = Attestation.query.filter_by(status='ACTIVE').all()
    return jsonify({'success': True, 'data': [a.to_dict() for a in attestations]})

@api_bp.route('/exam/session/<session_id>', methods=['GET'])
def api_exam_session(session_id):
    payload = TestEngineService.get_session_payload(session_id)
    if not payload:
        return jsonify({'success': False, 'message': "Sessiya topilmadi"}), 404
    return jsonify({'success': True, 'data': payload})

@api_bp.route('/exam/session/<session_id>/answer', methods=['POST'])
def api_save_answer(session_id):
    data = request.get_json() or {}
    q_id = data.get('question_id')
    selected_option_ids = data.get('selected_option_ids', [])
    text_answer = data.get('text_answer', '')
    is_flagged = data.get('is_flagged', False)
    time_spent = int(data.get('time_spent', 0))

    res = TestEngineService.save_answer(
        session_id=session_id,
        question_id=q_id,
        selected_option_ids=selected_option_ids,
        text_answer=text_answer,
        is_flagged=is_flagged,
        time_spent=time_spent
    )
    return jsonify(res)

@api_bp.route('/exam/session/<session_id>/heartbeat', methods=['POST'])
def api_heartbeat(session_id):
    session = TestSession.query.get(session_id)
    if not session:
        return jsonify({'success': False, 'message': "Sessiya topilmadi"}), 404
    
    if session.is_expired:
        res = TestEngineService.finish_session(session_id, auto_expire=True)
        return jsonify({'success': True, 'status': 'EXPIRED', 'result_id': res.id})

    return jsonify({'success': True, 'remaining_seconds': session.remaining_seconds})

@api_bp.route('/exam/session/<session_id>/finish', methods=['POST'])
def api_finish_exam(session_id):
    result = TestEngineService.finish_session(session_id, auto_expire=False)
    if not result:
        return jsonify({'success': False, 'message': "Xatolik yuz berdi"}), 400
    return jsonify({'success': True, 'result_id': result.id, 'percentage': float(result.percentage), 'is_passed': result.is_passed})

@api_bp.route('/exam/session/<session_id>/security-event', methods=['POST'])
def api_security_event(session_id):
    data = request.get_json() or {}
    event_type = data.get('event_type', 'UNKNOWN')
    severity = data.get('severity', 'LOW')
    details = data.get('details', {})

    session = TestSession.query.get(session_id)
    if not session:
        return jsonify({'success': False, 'message': "Sessiya topilmadi"}), 404

    ev = ProctoringService.log_event(
        session_id=session.id,
        user_id=session.user_id,
        event_type=event_type,
        severity=severity,
        details=details
    )
    return jsonify({'success': True, 'event_id': ev.id if ev else None})

@api_bp.route('/public/verify/<cert_no>', methods=['GET'])
def api_verify_certificate(cert_no):
    res = CertificateService.verify(cert_no, ip_address=request.remote_addr, user_agent=request.headers.get('User-Agent'))
    return jsonify(res)
