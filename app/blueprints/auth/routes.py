import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.user import User, UserRole, UserDocument
from app.services.audit_service import AuditService

auth_bp = Blueprint('auth', __name__)

ALLOWED_DOC_EXTS = {'pdf', 'png', 'jpg', 'jpeg'}

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

            if len(password) < 8:
                flash("Parol kamida 8 ta belgidan iborat bo'lishi shart.", "danger")
                return render_template('auth/register.html', step=1)

            if User.query.filter_by(email=email).first():
                flash("Ushbu elektron pochta manzili bilan allaqachon ro'yxatdan o'tilgan.", "danger")
                return render_template('auth/register.html', step=1)

            if User.query.filter_by(phone=phone).first():
                flash("Ushbu telefon raqami bilan allaqachon ro'yxatdan o'tilgan.", "danger")
                return render_template('auth/register.html', step=1)

            # Vaqtinchalik sessiyada saqlash
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
                flash("Avval 1-bosqichni to'ldiring.", "warning")
                return redirect(url_for('auth.register', step=1))

            birth_date_str = request.form.get('birth_date')
            gender = request.form.get('gender')
            region = request.form.get('region')
            organization = request.form.get('organization')
            position = request.form.get('position')
            specialty = request.form.get('specialty')
            experience = request.form.get('experience_years', 0)

            birth_date = None
            if birth_date_str:
                try:
                    birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass

            # Foydalanuvchini yaratish
            user = User(
                role=UserRole.FOYDALANUVCHI,
                email=step1_data['email'],
                phone=step1_data['phone'],
                first_name=step1_data['first_name'],
                last_name=step1_data['last_name'],
                middle_name=step1_data['middle_name'],
                birth_date=birth_date,
                gender=gender,
                region=region,
                organization=organization,
                position=position,
                specialty=specialty,
                experience_years=int(experience) if experience else 0,
                is_active=True,
                is_verified=False
            )
            user.set_password(step1_data['password'])
            db.session.add(user)
            db.session.commit()

            # Sessiyani tozalash va tizimga kirgizish
            session.pop('reg_step1', None)
            login_user(user)

            AuditService.log_action(
                user_id=user.id,
                action='REGISTER',
                entity='USER',
                entity_id=user.id
            )

            flash("Hisobingiz muvaffaqiyatli yaratildi! Endi kerakli hujjatlaringizni yuklashingiz mumkin.", "success")
            return redirect(url_for('auth.register', step=3))

        elif form_step == 3:
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))

            doc_file = request.files.get('document')
            doc_type = request.form.get('doc_type', 'PASSPORT')

            if doc_file and doc_file.filename:
                fname = secure_filename(doc_file.filename)
                ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
                if ext not in ALLOWED_DOC_EXTS:
                    flash("Faqat PDF, JPG yoki PNG fayllar qabul qilinadi.", "danger")
                    return redirect(url_for('auth.register', step=3))

                doc_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'documents')
                os.makedirs(doc_dir, exist_ok=True)
                saved_name = f"doc_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
                saved_path = os.path.join(doc_dir, saved_name)
                doc_file.save(saved_path)
                fsize = os.path.getsize(saved_path)

                doc = UserDocument(
                    user_id=current_user.id,
                    doc_type=doc_type,
                    file_name=fname,
                    file_path=f"uploads/documents/{saved_name}",
                    file_size=fsize,
                    mime_type=doc_file.mimetype or f"application/{ext}"
                )
                db.session.add(doc)
                db.session.commit()
                flash("Hujjat muvaffaqiyatli yuklandi!", "success")
            
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

        user = User.query.filter(
            (User.email == login_input.lower()) | (User.phone == login_input)
        ).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash("Hisobingiz ma'muriyat tomonidan bloklangan.", "danger")
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

            flash(f"Xush kelibsiz, {user.first_name}!", "success")
            
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
                
            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('user.dashboard'))

        flash("Login yoki parol noto'g'ri kiritildi.", "danger")

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    AuditService.log_action(
        user_id=current_user.id,
        action='LOGOUT',
        entity='USER',
        entity_id=current_user.id
    )
    logout_user()
    flash("Tizimdan muvaffaqiyatli chiqdingiz.", "info")
    return redirect(url_for('public.index'))
