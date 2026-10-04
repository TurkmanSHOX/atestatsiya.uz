import os
from flask import Flask, render_template
from app.config import config
from app.extensions import db, migrate, login_manager, csrf
from app.models.system import Setting, Notification
from flask_login import current_user

def create_app(config_name=None):
    if not config_name:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))

    # Extensions initialization
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Exempt REST API from CSRF token (uses session or custom tokens)
    # We will exempt API blueprint specifically

    # Register blueprints
    from app.blueprints.public.routes import public_bp
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.user.routes import user_bp
    from app.blueprints.admin.routes import admin_bp
    from app.blueprints.api.routes import api_bp

    csrf.exempt(api_bp)

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Global context processor
    @app.context_processor
    def inject_global_data():
        unread_notifications_count = 0
        if current_user.is_authenticated:
            unread_notifications_count = Notification.query.filter_by(
                user_id=current_user.id,
                is_read=False
            ).count()

        return {
            'site_name': Setting.get_val('site_name', 'Attestatsiya.uz'),
            'support_phone': Setting.get_val('support_phone', app.config.get('SUPPORT_PHONE')),
            'support_email': Setting.get_val('support_email', app.config.get('SUPPORT_EMAIL')),
            'unread_notifications_count': unread_notifications_count,
            'current_year': 2026
        }

    # Error handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app
