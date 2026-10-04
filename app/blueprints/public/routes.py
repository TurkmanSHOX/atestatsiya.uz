from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models.attestation import Attestation, AttestationStatus
from app.models.user import User
from app.models.result import Result
from app.models.certificate import Certificate
from app.services.certificate_service import CertificateService

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def index():
    active_attestations = Attestation.query.filter_by(status=AttestationStatus.ACTIVE).limit(6).all()
    stats = {
        'attestations_count': Attestation.query.filter_by(status=AttestationStatus.ACTIVE).count() or 12,
        'candidates_count': User.query.filter_by(role='FOYDALANUVCHI').count() or 1450,
        'passed_count': Result.query.filter_by(is_passed=True).count() or 980,
        'certificates_issued': Certificate.query.count() or 850
    }
    return render_template('public/index.html', attestations=active_attestations, stats=stats)

@public_bp.route('/attestations')
def attestations():
    query = Attestation.query.filter(Attestation.status.in_([AttestationStatus.ACTIVE, AttestationStatus.PAUSED]))
    
    # Filtrlash
    field = request.args.get('field')
    search = request.args.get('q')
    max_price = request.args.get('price')

    if field:
        query = query.filter_by(field_name=field)
    if search:
        query = query.filter(Attestation.title.ilike(f"%{search}%") | Attestation.short_description.ilike(f"%{search}%"))
    if max_price:
        try:
            query = query.filter(Attestation.price <= float(max_price))
        except ValueError:
            pass

    attestation_list = query.order_by(Attestation.created_at.desc()).all()
    fields = [r[0] for r in Attestation.query.with_entities(Attestation.field_name).distinct().all()]

    return render_template('public/attestations.html', attestations=attestation_list, fields=fields, current_field=field, search=search)

@public_bp.route('/attestations/<slug>')
def attestation_detail(slug):
    attestation = Attestation.query.filter_by(slug=slug).first_or_404()
    return render_template('public/attestation_detail.html', attestation=attestation)

@public_bp.route('/exam-rules')
def exam_rules():
    return render_template('public/exam_rules.html')

@public_bp.route('/pricing')
def pricing():
    attestations = Attestation.query.filter_by(status=AttestationStatus.ACTIVE).all()
    return render_template('public/pricing.html', attestations=attestations)

@public_bp.route('/news')
def news():
    return render_template('public/news.html')

@public_bp.route('/faq')
def faq():
    return render_template('public/faq.html')

@public_bp.route('/help')
def help_page():
    return render_template('public/help.html')

@public_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        flash("Murojaatingiz qabul qilindi. Tez orada mutaxassislarimiz siz bilan bog'lanishadi.", "success")
        return redirect(url_for('public.contact'))
    return render_template('public/contact.html')

@public_bp.route('/verify-certificate/<cert_no>')
def verify_certificate(cert_no):
    result = CertificateService.verify(
        cert_no,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    return render_template('public/verify_certificate.html', result=result, query=cert_no)
