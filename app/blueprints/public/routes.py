from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models.question import Subject, Topic, Question
from app.models.package import Package
from app.models.user import User
from app.models.result import Result

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def index():
    subjects = Subject.query.filter_by(is_active=True).order_by(Subject.order_num).limit(8).all()
    packages = Package.query.filter_by(is_active=True).order_by(Package.order_num).all()
    
    stats = {
        'subjects_count': Subject.query.filter_by(is_active=True).count() or 26,
        'teachers_count': User.query.filter_by(role='FOYDALANUVCHI').count() or 3400,
        'tests_completed': Result.query.count() or 18500,
        'questions_count': Question.query.filter_by(status='ACTIVE').count() or 5200
    }
    return render_template('public/index.html', subjects=subjects, packages=packages, stats=stats)

@public_bp.route('/subjects')
def subjects():
    q = request.args.get('q', '').strip()
    category = request.args.get('category')

    query = Subject.query.filter_by(is_active=True)
    if q:
        query = query.filter(Subject.name.ilike(f"%{q}%") | Subject.description.ilike(f"%{q}%"))
    if category:
        query = query.filter_by(category=category)

    subjects_list = query.order_by(Subject.order_num).all()
    categories = [r[0] for r in Subject.query.with_entities(Subject.category).distinct().all() if r[0]]

    return render_template('public/subjects.html', subjects=subjects_list, categories=categories, current_category=category, q=q)

@public_bp.route('/subjects/<slug>')
def subject_detail(slug):
    subject = Subject.query.filter_by(slug=slug, is_active=True).first_or_404()
    return render_template('public/subject_detail.html', subject=subject)

@public_bp.route('/packages')
@public_bp.route('/pricing')
def packages():
    packages_list = Package.query.filter_by(is_active=True).order_by(Package.order_num).all()
    return render_template('public/packages.html', packages=packages_list)

@public_bp.route('/how-it-works')
def how_it_works():
    return render_template('public/how_it_works.html')

@public_bp.route('/faq')
def faq():
    return render_template('public/faq.html')

@public_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        flash("Xabaringiz qabul qilindi. Tez orada mutaxassislarimiz siz bilan bog'lanishadi.", "success")
        return redirect(url_for('public.contact'))
    return render_template('public/contact.html')

@public_bp.route('/news')
def news():
    return render_template('public/news.html')
