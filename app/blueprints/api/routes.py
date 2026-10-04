from flask import Blueprint, jsonify, request
from flask_login import current_user, login_user
from app.models.user import User
from app.models.question import Subject, Topic, Question
from app.models.test import Test
from app.models.session import TestSession
from app.models.result import Result
from app.models.system import Notification
from app.services.test_engine_service import TestEngineService
from app.services.payment_service import PaymentService

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

@api_bp.route('/subjects', methods=['GET'])
def api_subjects():
    subjects = Subject.query.filter_by(is_active=True).order_by(Subject.order_num).all()
    return jsonify({'success': True, 'data': [s.to_dict() for s in subjects]})

@api_bp.route('/topics', methods=['GET'])
def api_topics():
    subject_id = request.args.get('subject_id')
    query = Topic.query.filter_by(is_active=True)
    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    topics = query.order_by(Topic.order_num).all()
    return jsonify({'success': True, 'data': [t.to_dict() for t in topics]})

@api_bp.route('/tests', methods=['GET'])
def api_tests():
    subject_id = request.args.get('subject_id')
    query = Test.query.filter_by(status='ACTIVE')
    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    tests = query.all()
    return jsonify({'success': True, 'data': [t.to_dict() for t in tests]})

# ==================== TEST ISHLASH JARAYONI ====================

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
    return jsonify({
        'success': True,
        'result_id': result.id,
        'percentage': float(result.percentage),
        'is_passed': result.is_passed,
        'score': float(result.score)
    })

# ==================== CLICK TO'LOV CALLBACKLARI ====================

@api_bp.route('/payments/click/prepare', methods=['POST'])
def click_prepare():
    data = request.form.to_dict() if request.form else (request.get_json() or {})
    response_data = PaymentService.handle_click_prepare(data, ip_address=request.remote_addr)
    return jsonify(response_data)

@api_bp.route('/payments/click/complete', methods=['POST'])
def click_complete():
    data = request.form.to_dict() if request.form else (request.get_json() or {})
    response_data = PaymentService.handle_click_complete(data, ip_address=request.remote_addr)
    return jsonify(response_data)

@api_bp.route('/payments/click/callback', methods=['POST'])
def click_unified_callback():
    """Click yagona webhook (action = 0 yoki action = 1)"""
    data = request.form.to_dict() if request.form else (request.get_json() or {})
    action = str(data.get('action', '0'))
    if action == '1':
        response_data = PaymentService.handle_click_complete(data, ip_address=request.remote_addr)
    else:
        response_data = PaymentService.handle_click_prepare(data, ip_address=request.remote_addr)
    return jsonify(response_data)

# ==================== NATIJALAR VA BILDIRISHNOMALAR ====================

@api_bp.route('/results', methods=['GET'])
def api_user_results():
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': "Avtorizatsiya talab qilinadi"}), 401
    results = Result.query.filter_by(user_id=current_user.id).order_by(Result.created_at.desc()).all()
    return jsonify({'success': True, 'data': [r.to_dict() for r in results]})

@api_bp.route('/notifications', methods=['GET'])
def api_notifications():
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': "Avtorizatsiya talab qilinadi"}), 401
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(15).all()
    return jsonify({'success': True, 'data': [n.to_dict() for n in notifications]})
