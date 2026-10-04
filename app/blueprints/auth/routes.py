from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User, UserRole
from app.services.audit_service import AuditService

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))

    step = int(request.args.get('step', 1))

    if request.method == 'POST':
        form_step = int(request.form.get('current_step', 1))

        if form_step == 1:
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            middle_name = request.form.get('middle_name', '').strip()
            email = request.form.get('email', '').strip().lower()
            phone = request.form.get('phone', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not all([first_name, last_name, email, phone, password]):
                flash("Iltimos, barcha majburiy maydonlarni to'ldiring.", "danger")
                return render_template('auth/register.html', step=1)

            if password != confirm_password:
                flash("Kiritilgan parollar bir-biriga mos kelmadi.", "danger")
                return render_template('auth/register.html', step=1)

            if len(password) < 6:
                flash("Parol kamida 6 ta belgidan iborat bo'lishi kerak.", "danger")
                return render_template('auth/register.html', step=1)

            if User.query.filter_by(email=email).first():
                flash("Ushbu elektron pochta manzili allaqachon ro'yxatdan o'tgan.", "danger")
                return render_template('auth/register.html', step=1)

            if User.query.filter_by(phone=phone).first():
                flash("Ushbu telefon raqami allaqachon ro'yxatdan o'tgan.", "danger")
                return render_template('auth/register.html', step=1)

            session['reg_step1'] = {
                'first_name': first_name,
                'last_name': last_name,
                'middle_name': middle_name,
                'email': email,
                'phone': phone,
                'password': password
            }
            return redirect(url_for('auth.register', step=2))

        elif form_step == 2:
            step1_data = session.get('reg_step1')
            if not step1_data:
                flash("Iltimos, avval 1-bosqichni to'ldiring.", "warning")
                return redirect(url_for('auth.register', step=1))

            region = request.form.get('region', '').strip()
            organization = request.form.get('organization', '').strip()
            position = request.form.get('position', '').strip()
            specialty = request.form.get('specialty', '').strip()
            experience = request.form.get('experience_years', 0)

            # Foydalanuvchini yaratish
            user = User(
                role=UserRole.FOYDALANUVCHI,
                email=step1_data['email'],
                phone=step1_data['phone'],
                first_name=step1_data['first_name'],
                last_name=step1_data['last_name'],
                middle_name=step1_data['middle_name'],
                region=region,
                organization=organization,
                position=position,
                specialty=specialty,
                experience_years=int(experience) if experience else 0,
                is_active=True,
                is_verified=True
            )
            user.set_password(step1_data['password'])

            db.session.add(user)
            db.session.commit()

            session.pop('reg_step1', None)
            login_user(user)

            AuditService.log_action(
                user_id=user.id,
                action='REGISTER',
                entity='USER',
                entity_id=user.id,
                new_values={'email': user.email, 'full_name': user.full_name}
            )

            flash("Muvaffaqiyatli ro'yxatdan o'tdingiz! Tayyorgarlik platformasiga xush kelibsiz.", "success")
            return redirect(url_for('user.dashboard'))

    return render_template('auth/register.html', step=step)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))

    if request.method == 'POST':
        login_input = request.form.get('login', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not login_input or not password:
            flash("Iltimos, login va parolni kiriting.", "danger")
            return render_template('auth/login.html')

        user = User.query.filter(
            (User.email == login_input.lower()) | (User.phone == login_input)
        ).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash("Hisobingiz ma'muriyat tomonidan vaqtincha bloklangan.", "danger")
                return render_template('auth/login.html')

            user.last_login_at = datetime.utcnow()
            user.last_login_ip = request.remote_addr
            db.session.commit()

            login_user(user, remember=remember)

            AuditService.log_action(
                user_id=user.id,
                action='LOGIN',
                entity='USER',
                entity_id=user.id
            )

            next_page = request.args.get('next')
            if current_user.is_admin:
                return redirect(next_page or url_for('admin.dashboard'))
            return redirect(next_page or url_for('user.dashboard'))
        else:
            flash("Telefon/Email yoki parol noto'g'ri kiritildi.", "danger")

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Tizimdan muvaffaqiyatli chiqdingiz.", "info")
    return redirect(url_for('public.index'))
