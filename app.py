# -*- coding: utf-8 -*-
"""
app.py
======
Point central de création et de configuration de l'application Flask PDSC.
"""

import os
from datetime import datetime

from flask import Flask, render_template
from flask_babel import Babel
from flask_jwt_extended import JWTManager
from flask_login import current_user
from flask_mail import Mail
from flask_migrate import Migrate
from flask_wtf import CSRFProtect

from config import get_config
from models import (
    Department, Notification, Role, Service, User, db, login_manager,
)
from utils import get_locale


# ---------------------------------------------------------------------------
# Création de l'application
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.config.from_object(get_config())


# ---------------------------------------------------------------------------
# Initialisation des extensions
# ---------------------------------------------------------------------------

db.init_app(app)

migrate = Migrate(app, db)

login_manager.init_app(app)

mail = Mail(app)

babel = Babel(app, locale_selector=get_locale)

jwt = JWTManager(app)

csrf = CSRFProtect(app)


# ---------------------------------------------------------------------------
# Contexte global des templates
# ---------------------------------------------------------------------------

@app.context_processor
def inject_globals():

    unread_count = 0
    recent_notifications = []
    dashboard_url = ''

    if current_user.is_authenticated:

        unread_count = current_user.unread_notifications_count()

        recent_notifications = (
            current_user.notifications
            .order_by(Notification.created_at.desc())
            .limit(6)
            .all()
        )

        if current_user.has_role('admin'):
            dashboard_url = '/admin/tableau-de-bord'

        elif current_user.has_role('employee'):
            dashboard_url = '/employe/tableau-de-bord'

        else:
            dashboard_url = '/citoyen/tableau-de-bord'

    return {
        'current_year': datetime.utcnow().year,
        'commune_name_fr': app.config['COMMUNE_NAME_FR'],
        'commune_name_ar': app.config['COMMUNE_NAME_AR'],
        'current_lang': get_locale(),
        'languages': app.config['LANGUAGES'],
        'unread_notifications_count': unread_count,
        'recent_notifications': recent_notifications,
        'dashboard_url': dashboard_url,

        'nav_services': (
            Service.query
            .filter_by(active=True)
            .order_by(Service.order)
            .limit(8)
            .all()
        ),
    }


# ---------------------------------------------------------------------------
# Headers de sécurité
# ---------------------------------------------------------------------------

@app.after_request
def set_response_headers(response):

    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'

    return response


# ---------------------------------------------------------------------------
# Gestion des erreurs
# ---------------------------------------------------------------------------

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('403.html'), 403


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):

    db.session.rollback()

    return render_template('500.html'), 500


# ---------------------------------------------------------------------------
# Commande CLI
# ---------------------------------------------------------------------------

@app.cli.command('seed-db')
def seed_db():

    from werkzeug.security import generate_password_hash

    if Role.query.count() == 0:

        roles = [
            Role(
                name='admin',
                label_fr='Administrateur',
                label_ar='مسؤول'
            ),
            Role(
                name='employee',
                label_fr='Employé',
                label_ar='موظف'
            ),
            Role(
                name='citizen',
                label_fr='Citoyen',
                label_ar='مواطن'
            ),
        ]

        db.session.add_all(roles)
        db.session.commit()

    admin_role = Role.query.filter_by(name='admin').first()

    if not User.query.filter_by(email='admin@commune.ma').first():

        admin = User(
            email='admin@commune.ma',
            first_name='Admin',
            last_name='PDSC',
            role_id=admin_role.id,
            is_active_account=True,
            is_verified=True,
        )

        admin.password_hash = generate_password_hash('Admin@2026')

        db.session.add(admin)
        db.session.commit()

    dept = Department.query.first()

    if not dept:

        dept = Department(
            name_fr='Administration Générale',
            name_ar='الإدارة العامة'
        )

        db.session.add(dept)
        db.session.commit()

    default_services = [
        ('etat-civil', 'État Civil', 'الحالة المدنية'),
        (
            'legalisation-signatures',
            'Légalisation des Signatures',
            'مصادقة على الإمضاءات'
        ),
        (
            'taxes-communales',
            'Taxes Communales',
            'الضرائب الجماعية'
        ),
        (
            'assiette-fiscale',
            'Assiette Fiscale',
            'الوعاء الضريبي'
        ),
        (
            'marches-publics',
            'Marchés Publics',
            'الصفقات العمومية'
        ),
        (
            'bureau-ordre',
            'Bureau d’Ordre',
            'مكتب الضبط'
        ),
        (
            'service-technique',
            'Service Technique',
            'المصلحة التقنية'
        ),
        (
            'urbanisme',
            'Urbanisme',
            'التعمير'
        ),
        (
            'patrimoine-communal',
            'Patrimoine Communal',
            'الممتلكات الجماعية'
        ),
        (
            'ressources-humaines',
            'Ressources Humaines',
            'الموارد البشرية'
        ),
        (
            'secretariat-general',
            'Secrétariat Général',
            'الكتابة العامة'
        ),
        (
            'gestion-depenses',
            'Gestion des Dépenses',
            'تدبير النفقات'
        ),
        (
            'direction-services',
            'Directeur des Services',
            'مدير المصالح'
        ),
        (
            'administration',
            'Administration',
            'الإدارة'
        ),
    ]

    if Service.query.count() == 0:

        for i, (slug, fr, ar) in enumerate(default_services):

            db.session.add(
                Service(
                    department_id=dept.id,
                    slug=slug,
                    name_fr=fr,
                    name_ar=ar,
                    description_fr=f'Service : {fr}',
                    description_ar=ar,
                    icon='bi-briefcase',
                    order=i,
                    active=True,
                )
            )

        db.session.commit()

    print('Initialisation terminée.')


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

import routes  # noqa: E402,F401