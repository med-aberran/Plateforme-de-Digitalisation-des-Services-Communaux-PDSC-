# -*- coding: utf-8 -*-
"""
routes.py
=========
Toutes les routes de l'application PDSC sont regroupees dans ce fichier
unique, organise en sections : site public, authentification, compte,
demandes / rendez-vous / reclamations (partages citoyen-employe-admin),
tableau de bord employe, tableau de bord administrateur, notifications et
API JWT.
"""

from datetime import datetime

from flask import (
    abort, flash, jsonify, redirect, render_template, request, send_file,
    session, url_for,
)
from flask_babel import gettext as _
from flask_jwt_extended import (
    create_access_token, get_jwt_identity, jwt_required,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_

from app import app, db
from forms import (
    AppointmentForm, AppointmentStatusForm, AssignEmployeeForm,
    ChangePasswordForm, ComplaintForm, ComplaintResponseForm, ContactForm,
    DepartmentForm, ForgotPasswordForm, GalleryImageForm, LoginForm,
    NewsForm, ProfileForm, PublicDocumentForm, RegisterForm,
    RequestCommentForm, ResetPasswordForm, ServiceForm, ServiceRequestForm,
    SettingForm, UpdateRequestStatusForm, UrbanPlanForm, UserAdminForm,
    VideoForm,
)
from models import (
    Appointment, APPOINTMENT_STATUSES, Citizen, Complaint, COMPLAINT_STATUSES,
    Department, DOCUMENT_CATEGORIES, Employee, GalleryImage, Log, News,
    Notification, PublicDocument, REQUEST_STATUSES, RequestComment,
    RequestDocument, RequestHistory, Role, Service, ServiceRequest, Setting,
    UrbanPlan, User, Video, db,
)
from utils import (
    admin_required, citizen_required, confirm_token, create_notification,
    delete_uploaded_file, employee_required, export_requests_to_excel,
    flash_errors, generate_qr_code, generate_request_pdf, generate_token,
    generate_tracking_number, get_locale, log_action, request_schema,
    requests_schema, save_uploaded_file, send_email,
)

ITEMS_PER_PAGE = 10


# ---------------------------------------------------------------------------
# Redirection selon le role apres connexion
# ---------------------------------------------------------------------------

def _dashboard_url_for(user):
    if user.has_role('admin'):
        return url_for('dashboard_admin')
    if user.has_role('employee'):
        return url_for('dashboard_employee')
    return url_for('dashboard_citizen')


def _status_choices(status_tuples):
    """Construit une liste de choix (code, libelle) dans la langue active a
    partir des tuples bilingues definis dans models.py."""
    lang = get_locale()
    return [(code, ar if lang == 'ar' else fr) for code, fr, ar, _css in status_tuples]


# ===========================================================================
# SITE PUBLIC
# ===========================================================================

@app.route('/')
def index():
    services = Service.query.filter_by(active=True).order_by(Service.order).all()
    news_items = News.query.filter_by(active=True).order_by(News.published_at.desc()).limit(6).all()
    documents = PublicDocument.query.order_by(PublicDocument.uploaded_at.desc()).limit(6).all()
    gallery_images = GalleryImage.query.order_by(GalleryImage.uploaded_at.desc()).limit(12).all()
    videos = Video.query.order_by(Video.uploaded_at.desc()).limit(6).all()
    urban_plan = UrbanPlan.query.filter_by(active=True).order_by(UrbanPlan.uploaded_at.desc()).first()
    contact_form = ContactForm()

    return render_template(
        'index.html',
        services=services,
        news_items=news_items,
        documents=documents,
        gallery_images=gallery_images,
        videos=videos,
        urban_plan=urban_plan,
        contact_form=contact_form,
        search_results=None,
    )


@app.route('/recherche')
def search():
    query = request.args.get('q', '').strip()
    results = {'services': [], 'news': [], 'documents': []}

    if query:
        like = f'%{query}%'
        results['services'] = Service.query.filter(
            Service.active.is_(True),
            or_(Service.name_fr.ilike(like), Service.name_ar.ilike(like),
                Service.description_fr.ilike(like))
        ).all()
        results['news'] = News.query.filter(
            News.active.is_(True),
            or_(News.title_fr.ilike(like), News.title_ar.ilike(like), News.content_fr.ilike(like))
        ).all()
        results['documents'] = PublicDocument.query.filter(
            or_(PublicDocument.title_fr.ilike(like), PublicDocument.title_ar.ilike(like))
        ).all()

    return render_template('index.html', search_results=results, search_query=query,
                            services=[], news_items=[], documents=[], gallery_images=[],
                            videos=[], urban_plan=None, contact_form=ContactForm())


@app.route('/contact', methods=['POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        send_email(
            subject=f'[Contact PDSC] {form.subject.data}',
            recipients=[app.config['MAIL_DEFAULT_SENDER']],
            body=f'De : {form.name.data} <{form.email.data}>\n\n{form.message.data}',
        )
        flash(_('Votre message a bien été envoyé. Nous vous répondrons rapidement.'), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('index') + '#contact')


@app.route('/services')
def services_list():
    services = Service.query.filter_by(active=True).order_by(Service.order).all()
    return render_template('services.html', services=services, service=None)


@app.route('/services/<slug>')
def service_detail(slug):
    service = Service.query.filter_by(slug=slug, active=True).first_or_404()
    related = Service.query.filter(
        Service.active.is_(True), Service.id != service.id).order_by(Service.order).limit(4).all()
    service_documents = service.documents.order_by(PublicDocument.uploaded_at.desc()).all()
    return render_template('services.html', service=service, services=related,
                            service_documents=service_documents)


@app.route('/documents')
def documents_list():
    query_text = request.args.get('q', '').strip()
    service_id = request.args.get('service', type=int)
    category = request.args.get('category', '')
    page = request.args.get('page', 1, type=int)

    query = PublicDocument.query
    if query_text:
        like = f'%{query_text}%'
        query = query.filter(or_(
            PublicDocument.title_fr.ilike(like), PublicDocument.title_ar.ilike(like),
            PublicDocument.reference.ilike(like)))
    if service_id:
        query = query.filter(PublicDocument.service_id == service_id)
    if category:
        query = query.filter(PublicDocument.category == category)

    pagination = query.order_by(PublicDocument.uploaded_at.desc()).paginate(
        page=page, per_page=ITEMS_PER_PAGE, error_out=False)

    return render_template(
        'documents.html', pagination=pagination, documents=pagination.items,
        query_text=query_text, service_id=service_id, category=category,
        services=Service.query.filter_by(active=True).order_by(Service.order).all(),
        categories=DOCUMENT_CATEGORIES)


@app.route('/actualites')
def news_list():
    page = request.args.get('page', 1, type=int)
    pagination = News.query.filter_by(active=True).order_by(
        News.published_at.desc()).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    return render_template('news.html', pagination=pagination, news_items=pagination.items, news_item=None)


@app.route('/actualites/<int:news_id>')
def news_detail(news_id):
    news_item = News.query.filter_by(id=news_id, active=True).first_or_404()
    others = News.query.filter(News.active.is_(True), News.id != news_id).order_by(
        News.published_at.desc()).limit(4).all()
    return render_template('news.html', news_item=news_item, news_items=others, pagination=None)


@app.route('/suivi', methods=['GET', 'POST'])
def track_request_form():
    if request.method == 'POST':
        tracking_number = request.form.get('tracking_number', '').strip()
        if tracking_number:
            return redirect(url_for('track_request', tracking_number=tracking_number))
        flash(_('Veuillez saisir un numéro de suivi valide.'), 'warning')
    return render_template('request_details.html', public_view=True, service_request=None)


@app.route('/suivi/<tracking_number>')
def track_request(tracking_number):
    service_request = ServiceRequest.query.filter_by(tracking_number=tracking_number).first()
    if not service_request:
        flash(_("Aucune demande ne correspond à ce numéro de suivi."), 'warning')
        return redirect(url_for('track_request_form'))
    return render_template('request_details.html', public_view=True, service_request=service_request)


@app.route('/langue/<lang_code>')
def set_language(lang_code):
    if lang_code in app.config['LANGUAGES']:
        session['lang'] = lang_code
        if current_user.is_authenticated:
            current_user.preferred_language = lang_code
            db.session.commit()
    return redirect(request.referrer or url_for('index'))


# ===========================================================================
# AUTHENTIFICATION
# ===========================================================================

@app.route('/inscription', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(_dashboard_url_for(current_user))

    form = RegisterForm()
    if form.validate_on_submit():
        citizen_role = Role.query.filter_by(name='citizen').first()
        user = User(
            email=form.email.data.lower().strip(),
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            phone=form.phone.data,
            role_id=citizen_role.id,
            is_active_account=True,
            is_verified=False,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        citizen = Citizen(user_id=user.id, cin=form.cin.data.strip())
        db.session.add(citizen)
        db.session.commit()

        token = generate_token(user.email, salt='email-verify')
        verify_url = url_for('verify_email', token=token, _external=True)
        send_email(
            subject='Vérifiez votre adresse e-mail - PDSC',
            recipients=[user.email],
            body=f'Bonjour {user.first_name},\n\nVeuillez confirmer votre e-mail : {verify_url}',
        )
        log_action('inscription', f'Nouveau citoyen : {user.email}', user=user)

        flash(_("Inscription réussie ! Un e-mail de vérification vous a été envoyé."), 'success')
        if app.debug:
            flash(_('[Développement] Lien de vérification : %(url)s', url=verify_url), 'info')
        return redirect(url_for('login'))

    flash_errors(form)
    return render_template('register.html', form=form)


@app.route('/verifier-email/<token>')
def verify_email(token):
    email = confirm_token(token, salt='email-verify')
    if not email:
        flash(_('Le lien de vérification est invalide ou expiré.'), 'danger')
        return redirect(url_for('login'))

    user = User.query.filter_by(email=email).first_or_404()
    user.is_verified = True
    db.session.commit()
    flash(_('Votre adresse e-mail a été vérifiée. Vous pouvez maintenant vous connecter.'), 'success')
    return redirect(url_for('login'))


@app.route('/connexion', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(_dashboard_url_for(current_user))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            if not user.is_active_account:
                flash(_('Votre compte a été désactivé. Contactez l\'administration.'), 'danger')
                return render_template('login.html', form=form)
            login_user(user, remember=form.remember_me.data)
            log_action('connexion', user=user)
            next_page = request.args.get('next')
            return redirect(next_page or _dashboard_url_for(user))
        flash(_('Adresse e-mail ou mot de passe incorrect.'), 'danger')

    return render_template('login.html', form=form)


@app.route('/deconnexion')
@login_required
def logout():
    log_action('deconnexion')
    logout_user()
    flash(_('Vous avez été déconnecté avec succès.'), 'info')
    return redirect(url_for('index'))


@app.route('/mot-de-passe-oublie', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user:
            token = generate_token(user.email, salt='password-reset')
            reset_url = url_for('reset_password', token=token, _external=True)
            send_email(
                subject='Réinitialisation de votre mot de passe - PDSC',
                recipients=[user.email],
                body=f'Bonjour {user.first_name},\n\nCliquez ici pour réinitialiser votre mot de passe : {reset_url}',
            )
            if app.debug:
                flash(_('[Développement] Lien de réinitialisation : %(url)s', url=reset_url), 'info')
        flash(_("Si un compte existe avec cette adresse, un e-mail a été envoyé."), 'info')
        return redirect(url_for('login'))
    return render_template('login.html', forgot_form=form, show_forgot=True)


@app.route('/reinitialiser-mot-de-passe/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = confirm_token(token, salt='password-reset', max_age=3600)
    if not email:
        flash(_('Le lien de réinitialisation est invalide ou expiré.'), 'danger')
        return redirect(url_for('forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=email).first_or_404()
        user.set_password(form.password.data)
        db.session.commit()
        log_action('reinitialisation-mot-de-passe', user=user)
        flash(_('Votre mot de passe a été réinitialisé. Vous pouvez vous connecter.'), 'success')
        return redirect(url_for('login'))

    return render_template('login.html', reset_form=form, show_reset=True, reset_token=token)


# ===========================================================================
# COMPTE (commun a tous les roles authentifies)
# ===========================================================================

@app.route('/profil', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if request.method == 'GET':
        form.preferred_language.data = current_user.preferred_language or 'fr'
        if current_user.citizen_profile:
            form.address.data = current_user.citizen_profile.address
            form.city.data = current_user.citizen_profile.city

    if form.validate_on_submit():
        current_user.first_name = form.first_name.data.strip()
        current_user.last_name = form.last_name.data.strip()
        current_user.phone = form.phone.data
        current_user.preferred_language = form.preferred_language.data

        if form.avatar.data:
            delete_uploaded_file(current_user.avatar)
            current_user.avatar = save_uploaded_file(form.avatar.data, 'avatars')

        if current_user.citizen_profile:
            current_user.citizen_profile.address = form.address.data
            current_user.citizen_profile.city = form.city.data

        db.session.commit()
        flash(_('Votre profil a été mis à jour avec succès.'), 'success')
        return redirect(url_for('profile'))

    flash_errors(form)
    return render_template('profile.html', form=form)


@app.route('/parametres', methods=['GET', 'POST'])
@login_required
def account_settings():
    password_form = ChangePasswordForm()
    if password_form.validate_on_submit():
        if not current_user.check_password(password_form.current_password.data):
            flash(_('Le mot de passe actuel est incorrect.'), 'danger')
        else:
            current_user.set_password(password_form.password.data)
            db.session.commit()
            log_action('changement-mot-de-passe')
            flash(_('Votre mot de passe a été modifié avec succès.'), 'success')
            return redirect(url_for('account_settings'))
    flash_errors(password_form)
    return render_template('settings.html', password_form=password_form)


# ===========================================================================
# TABLEAUX DE BORD
# ===========================================================================

@app.route('/citoyen/tableau-de-bord')
@citizen_required
def dashboard_citizen():
    citizen = current_user.citizen_profile
    recent_requests = citizen.requests.order_by(ServiceRequest.created_at.desc()).limit(5).all() if citizen else []
    upcoming_appointments = citizen.appointments.filter(
        Appointment.appointment_date >= datetime.utcnow().date()
    ).order_by(Appointment.appointment_date).limit(5).all() if citizen else []
    open_complaints = citizen.complaints.filter(
        Complaint.status != 'cloturee').order_by(Complaint.created_at.desc()).limit(5).all() if citizen else []
    recent_notifications = current_user.notifications.order_by(Notification.created_at.desc()).limit(8).all()

    stats = {
        'total_requests': citizen.requests.count() if citizen else 0,
        'pending_requests': citizen.requests.filter(
            ServiceRequest.status.notin_(['terminee', 'refusee', 'archivee'])).count() if citizen else 0,
        'total_appointments': citizen.appointments.count() if citizen else 0,
        'total_complaints': citizen.complaints.count() if citizen else 0,
    }

    return render_template(
        'dashboard_citizen.html', stats=stats, recent_requests=recent_requests,
        upcoming_appointments=upcoming_appointments, open_complaints=open_complaints,
        recent_notifications=recent_notifications,
    )


@app.route('/employe/tableau-de-bord')
@employee_required
def dashboard_employee():
    employee = current_user.employee_profile
    base_query = ServiceRequest.query
    if employee and current_user.has_role('employee'):
        base_query = ServiceRequest.query.join(Service).filter(
            or_(ServiceRequest.employee_id == employee.id,
                Service.department_id == employee.department_id))

    stats = {
        'total_requests': base_query.count(),
        'pending_requests': base_query.filter(
            ServiceRequest.status.in_(['soumise', 'en_attente', 'affectee', 'en_cours'])).count(),
        'completed_requests': base_query.filter(ServiceRequest.status == 'terminee').count(),
        'upcoming_appointments': Appointment.query.filter(
            Appointment.appointment_date >= datetime.utcnow().date(),
            Appointment.status == 'confirme').count(),
        'open_complaints': Complaint.query.filter(Complaint.status != 'cloturee').count(),
    }
    recent_requests = base_query.order_by(ServiceRequest.created_at.desc()).limit(8).all()
    recent_notifications = current_user.notifications.order_by(Notification.created_at.desc()).limit(8).all()

    return render_template('dashboard_employee.html', stats=stats, recent_requests=recent_requests,
                            recent_notifications=recent_notifications)


@app.route('/admin/tableau-de-bord')
@admin_required
def dashboard_admin():
    stats = {
        'total_users': User.query.count(),
        'total_citizens': Citizen.query.count(),
        'total_employees': Employee.query.count(),
        'total_requests': ServiceRequest.query.count(),
        'pending_requests': ServiceRequest.query.filter(
            ServiceRequest.status.in_(['soumise', 'en_attente', 'affectee', 'en_cours'])).count(),
        'total_appointments': Appointment.query.count(),
        'total_complaints': Complaint.query.count(),
        'open_complaints': Complaint.query.filter(Complaint.status != 'cloturee').count(),
    }

    departments = Department.query.order_by(Department.name_fr).all()
    roles = Role.query.all()
    all_services = Service.query.order_by(Service.order).all()
    active_services = [s for s in all_services if s.active]

    user_form = UserAdminForm()
    user_form.role_id.choices = [(r.id, r.label_fr) for r in roles]
    user_form.department_id.choices = [(0, '-')] + [(d.id, d.name_fr) for d in departments]

    service_form = ServiceForm()
    service_form.department_id.choices = [(0, '-')] + [(d.id, d.name_fr) for d in departments]

    document_form = PublicDocumentForm()
    document_form.service_id.choices = [(0, '-')] + [(s.id, s.name_fr) for s in active_services]

    context = dict(
        stats=stats,
        users=User.query.order_by(User.created_at.desc()).all(),
        roles=roles,
        departments=departments,
        services=all_services,
        news_items=News.query.order_by(News.published_at.desc()).all(),
        documents=PublicDocument.query.order_by(PublicDocument.uploaded_at.desc()).all(),
        urban_plans=UrbanPlan.query.order_by(UrbanPlan.uploaded_at.desc()).all(),
        gallery_images=GalleryImage.query.order_by(GalleryImage.uploaded_at.desc()).all(),
        videos=Video.query.order_by(Video.uploaded_at.desc()).all(),
        settings=Setting.query.order_by(Setting.key).all(),
        logs=Log.query.order_by(Log.created_at.desc()).limit(50).all(),
        recent_notifications=current_user.notifications.order_by(Notification.created_at.desc()).limit(8).all(),
        user_form=user_form,
        department_form=DepartmentForm(),
        service_form=service_form,
        news_form=NewsForm(),
        document_form=document_form,
        urban_plan_form=UrbanPlanForm(),
        gallery_form=GalleryImageForm(),
        video_form=VideoForm(),
    )
    return render_template('dashboard_admin.html', **context)


# ===========================================================================
# DEMANDES ADMINISTRATIVES (citoyen, employe, admin)
# ===========================================================================

def _visible_requests_query():
    """Retourne la requete SQLAlchemy des demandes visibles selon le role
    de l'utilisateur connecte."""
    if current_user.has_role('admin'):
        return ServiceRequest.query
    if current_user.has_role('employee'):
        employee = current_user.employee_profile
        return ServiceRequest.query.join(Service).filter(
            or_(ServiceRequest.employee_id == employee.id,
                Service.department_id == employee.department_id))
    return ServiceRequest.query.filter_by(citizen_id=current_user.citizen_profile.id)


def _can_view_request(service_request):
    if current_user.has_role('admin'):
        return True
    if current_user.has_role('employee'):
        employee = current_user.employee_profile
        return (service_request.employee_id == employee.id or
                service_request.service.department_id == employee.department_id)
    return (current_user.citizen_profile and
            service_request.citizen_id == current_user.citizen_profile.id)


@app.route('/demandes')
@login_required
def requests_list():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    query = _visible_requests_query()
    if status_filter:
        query = query.filter(ServiceRequest.status == status_filter)
    pagination = query.order_by(ServiceRequest.created_at.desc()).paginate(
        page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    return render_template('requests.html', pagination=pagination, requests=pagination.items,
                            status_filter=status_filter)


@app.route('/demandes/nouvelle', methods=['GET', 'POST'])
@citizen_required
def request_create():
    form = ServiceRequestForm()
    form.service_id.choices = [
        (s.id, s.name_fr) for s in Service.query.filter_by(active=True).order_by(Service.order)]

    if form.validate_on_submit():
        tracking_number = generate_tracking_number()
        service_request = ServiceRequest(
            tracking_number=tracking_number,
            citizen_id=current_user.citizen_profile.id,
            service_id=form.service_id.data,
            notes=form.notes.data,
            status='soumise',
        )
        db.session.add(service_request)
        db.session.flush()

        qr_data = url_for('track_request', tracking_number=tracking_number, _external=True)
        service_request.qr_code = generate_qr_code(qr_data)

        for file_storage in request.files.getlist('documents'):
            if file_storage and file_storage.filename:
                saved_path = save_uploaded_file(file_storage, 'requests')
                if saved_path:
                    db.session.add(RequestDocument(
                        request_id=service_request.id, filename=saved_path,
                        original_filename=file_storage.filename, uploaded_by_id=current_user.id))

        db.session.add(RequestHistory(
            request_id=service_request.id, status='soumise',
            comment='Demande créée par le citoyen.', changed_by_id=current_user.id))
        db.session.commit()

        log_action('creation-demande', tracking_number)
        flash(_('Votre demande a été soumise avec succès. Numéro de suivi : %(num)s', num=tracking_number), 'success')
        return redirect(url_for('request_detail', request_id=service_request.id))

    flash_errors(form)
    return render_template('requests.html', form=form, create_mode=True, requests=[], pagination=None)


@app.route('/demandes/<int:request_id>')
@login_required
def request_detail(request_id):
    service_request = ServiceRequest.query.get_or_404(request_id)
    if not _can_view_request(service_request):
        abort(403)

    status_form = UpdateRequestStatusForm(status=service_request.status)
    status_form.status.choices = _status_choices(REQUEST_STATUSES)
    comment_form = RequestCommentForm()
    assign_form = AssignEmployeeForm()
    if service_request.service.department_id:
        assign_form.employee_id.choices = [
            (e.id, e.user.full_name) for e in Employee.query.filter_by(
                department_id=service_request.service.department_id)]
    else:
        assign_form.employee_id.choices = [(e.id, e.user.full_name) for e in Employee.query.all()]

    return render_template(
        'request_details.html', service_request=service_request, status_form=status_form,
        comment_form=comment_form, assign_form=assign_form, public_view=False)


@app.route('/demandes/<int:request_id>/statut', methods=['POST'])
@employee_required
def update_request_status(request_id):
    service_request = ServiceRequest.query.get_or_404(request_id)
    if not _can_view_request(service_request):
        abort(403)

    form = UpdateRequestStatusForm()
    form.status.choices = _status_choices(REQUEST_STATUSES)
    if form.validate_on_submit():
        service_request.status = form.status.data
        db.session.add(RequestHistory(
            request_id=service_request.id, status=form.status.data,
            comment=form.comment.data, changed_by_id=current_user.id))
        db.session.commit()

        create_notification(
            service_request.citizen.user,
            title=_('Mise à jour de votre demande %(num)s', num=service_request.tracking_number),
            message=_('Nouveau statut : %(status)s', status=service_request.status_label(get_locale())),
            link=url_for('request_detail', request_id=service_request.id))
        log_action('changement-statut-demande', f'{service_request.tracking_number} -> {form.status.data}')
        flash(_('Le statut de la demande a été mis à jour.'), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('request_detail', request_id=request_id))


@app.route('/demandes/<int:request_id>/commentaire', methods=['POST'])
@login_required
def add_request_comment(request_id):
    service_request = ServiceRequest.query.get_or_404(request_id)
    if not _can_view_request(service_request):
        abort(403)

    form = RequestCommentForm()
    if form.validate_on_submit():
        db.session.add(RequestComment(
            request_id=service_request.id, user_id=current_user.id, comment=form.comment.data))
        db.session.commit()
        if current_user.has_role('employee', 'admin'):
            create_notification(
                service_request.citizen.user, title=_('Nouveau commentaire sur votre demande'),
                message=form.comment.data[:200], link=url_for('request_detail', request_id=request_id))
        flash(_('Votre commentaire a été publié.'), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('request_detail', request_id=request_id))


@app.route('/demandes/<int:request_id>/affecter', methods=['POST'])
@employee_required
def assign_request(request_id):
    service_request = ServiceRequest.query.get_or_404(request_id)
    form = AssignEmployeeForm()
    form.employee_id.choices = [(e.id, e.user.full_name) for e in Employee.query.all()]

    if form.validate_on_submit():
        service_request.employee_id = form.employee_id.data
        if service_request.status in ('soumise', 'en_attente'):
            service_request.status = 'affectee'
        db.session.add(RequestHistory(
            request_id=service_request.id, status=service_request.status,
            comment='Demande affectée à un employé.', changed_by_id=current_user.id))
        db.session.commit()
        flash(_('La demande a été affectée avec succès.'), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('request_detail', request_id=request_id))


@app.route('/demandes/<int:request_id>/pdf')
@login_required
def request_pdf(request_id):
    service_request = ServiceRequest.query.get_or_404(request_id)
    if not _can_view_request(service_request):
        abort(403)
    buffer = generate_request_pdf(service_request)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True,
                      download_name=f'recepisse-{service_request.tracking_number}.pdf')


@app.route('/employe/export-excel')
@employee_required
def export_requests_excel():
    requests_qs = _visible_requests_query().order_by(ServiceRequest.created_at.desc()).all()
    buffer = export_requests_to_excel(requests_qs)
    return send_file(buffer, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                      as_attachment=True, download_name='demandes.xlsx')


# ===========================================================================
# RENDEZ-VOUS (citoyen, employe, admin)
# ===========================================================================

def _visible_appointments_query():
    if current_user.has_role('admin'):
        return Appointment.query
    if current_user.has_role('employee'):
        employee = current_user.employee_profile
        return Appointment.query.join(Service).filter(
            or_(Appointment.employee_id == employee.id,
                Service.department_id == employee.department_id))
    return Appointment.query.filter_by(citizen_id=current_user.citizen_profile.id)


@app.route('/rendez-vous', methods=['GET', 'POST'])
@login_required
def appointments_list():
    form = AppointmentForm()
    form.service_id.choices = [
        (s.id, s.name_fr) for s in Service.query.filter_by(active=True).order_by(Service.order)]

    if request.method == 'POST' and current_user.has_role('citizen'):
        if form.validate_on_submit():
            appointment = Appointment(
                citizen_id=current_user.citizen_profile.id,
                service_id=form.service_id.data,
                appointment_date=form.appointment_date.data,
                appointment_time=form.appointment_time.data,
                notes=form.notes.data,
                status='en_attente',
            )
            db.session.add(appointment)
            db.session.commit()
            log_action('creation-rendez-vous', str(appointment.id))
            flash(_('Votre demande de rendez-vous a été enregistrée.'), 'success')
            return redirect(url_for('appointments_list'))
        flash_errors(form)

    page = request.args.get('page', 1, type=int)
    pagination = _visible_appointments_query().order_by(
        Appointment.appointment_date.desc()).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    status_form = AppointmentStatusForm()
    status_form.status.choices = _status_choices(APPOINTMENT_STATUSES)

    return render_template('appointments.html', form=form, pagination=pagination,
                            appointments=pagination.items, status_form=status_form)


@app.route('/rendez-vous/<int:appointment_id>/statut', methods=['POST'])
@employee_required
def appointment_update_status(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    form = AppointmentStatusForm()
    form.status.choices = _status_choices(APPOINTMENT_STATUSES)
    if form.validate_on_submit():
        appointment.status = form.status.data
        db.session.commit()
        create_notification(
            appointment.citizen.user, title=_('Mise à jour de votre rendez-vous'),
            message=_('Nouveau statut : %(status)s', status=appointment.status_label(get_locale())),
            link=url_for('appointments_list'))
        flash(_('Le statut du rendez-vous a été mis à jour.'), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('appointments_list'))


@app.route('/rendez-vous/<int:appointment_id>/annuler', methods=['POST'])
@login_required
def appointment_cancel(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    is_owner = (current_user.citizen_profile and
                appointment.citizen_id == current_user.citizen_profile.id)
    if not (is_owner or current_user.has_role('employee', 'admin')):
        abort(403)
    appointment.status = 'annule'
    db.session.commit()
    flash(_('Le rendez-vous a été annulé.'), 'info')
    return redirect(url_for('appointments_list'))


# ===========================================================================
# RECLAMATIONS (citoyen, employe, admin)
# ===========================================================================

def _visible_complaints_query():
    if current_user.has_role('admin'):
        return Complaint.query
    if current_user.has_role('employee'):
        employee = current_user.employee_profile
        return Complaint.query.filter(
            or_(Complaint.department_id == employee.department_id, Complaint.department_id.is_(None)))
    return Complaint.query.filter_by(citizen_id=current_user.citizen_profile.id)


@app.route('/reclamations', methods=['GET', 'POST'])
@login_required
def complaints_list():
    form = ComplaintForm()
    form.department_id.choices = [(0, 'Non spécifié')] + [
        (d.id, d.name_fr) for d in Department.query.order_by(Department.name_fr)]

    if request.method == 'POST' and current_user.has_role('citizen'):
        if form.validate_on_submit():
            complaint = Complaint(
                citizen_id=current_user.citizen_profile.id,
                department_id=form.department_id.data or None,
                subject=form.subject.data,
                description=form.description.data,
                status='ouverte',
            )
            db.session.add(complaint)
            db.session.commit()
            log_action('creation-reclamation', str(complaint.id))
            flash(_('Votre réclamation a été envoyée. Nous la traiterons rapidement.'), 'success')
            return redirect(url_for('complaints_list'))
        flash_errors(form)

    page = request.args.get('page', 1, type=int)
    pagination = _visible_complaints_query().order_by(
        Complaint.created_at.desc()).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)

    empty_response_form = ComplaintResponseForm()
    empty_response_form.status.choices = _status_choices(
        [s for s in COMPLAINT_STATUSES if s[0] != 'ouverte'])

    return render_template('complaints.html', form=form, pagination=pagination,
                            complaints=pagination.items, complaint=None, response_form=empty_response_form)


@app.route('/reclamations/<int:complaint_id>')
@login_required
def complaint_detail(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    is_owner = (current_user.citizen_profile and complaint.citizen_id == current_user.citizen_profile.id)
    if not (is_owner or current_user.has_role('employee', 'admin')):
        abort(403)
    response_form = ComplaintResponseForm(status=complaint.status)
    response_form.status.choices = _status_choices(
        [s for s in COMPLAINT_STATUSES if s[0] != 'ouverte'])
    return render_template('complaints.html', complaint=complaint, complaints=[], pagination=None,
                            form=None, response_form=response_form)


@app.route('/reclamations/<int:complaint_id>/repondre', methods=['POST'])
@employee_required
def complaint_respond(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    form = ComplaintResponseForm()
    form.status.choices = _status_choices([s for s in COMPLAINT_STATUSES if s[0] != 'ouverte'])
    if form.validate_on_submit():
        complaint.response = form.response.data
        complaint.status = form.status.data
        if form.status.data == 'cloturee':
            complaint.closed_at = datetime.utcnow()
        db.session.commit()
        create_notification(
            complaint.citizen.user, title=_('Réponse à votre réclamation'),
            message=form.response.data[:200], link=url_for('complaint_detail', complaint_id=complaint.id))
        log_action('reponse-reclamation', str(complaint.id))
        flash(_('Votre réponse a été envoyée au citoyen.'), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('complaint_detail', complaint_id=complaint_id))


# ===========================================================================
# NOTIFICATIONS
# ===========================================================================

@app.route('/notifications/<int:notification_id>/lue', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        abort(403)
    notification.is_read = True
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'unread_count': current_user.unread_notifications_count()})
    return redirect(request.referrer or url_for('index'))


@app.route('/notifications/tout-lire', methods=['POST'])
@login_required
def mark_all_notifications_read():
    current_user.notifications.filter_by(is_read=False).update({'is_read': True})
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    return redirect(request.referrer or url_for('index'))


# ===========================================================================
# ADMINISTRATION : UTILISATEURS
# ===========================================================================

@app.route('/admin/utilisateurs', methods=['POST'])
@admin_required
def admin_user_create():
    form = UserAdminForm()
    form.role_id.choices = [(r.id, r.label_fr) for r in Role.query.all()]
    form.department_id.choices = [(0, '-')] + [(d.id, d.name_fr) for d in Department.query.all()]

    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower().strip()).first():
            flash(_('Cette adresse e-mail est déjà utilisée.'), 'danger')
            return redirect(url_for('dashboard_admin') + '#utilisateurs')

        role = Role.query.get(form.role_id.data)
        user = User(
            email=form.email.data.lower().strip(), first_name=form.first_name.data,
            last_name=form.last_name.data, phone=form.phone.data, role_id=role.id,
            is_active_account=form.is_active_account.data, is_verified=True,
        )
        user.set_password(form.password.data or 'Pdsc@2026')
        db.session.add(user)
        db.session.flush()

        if role.name == 'citizen':
            db.session.add(Citizen(user_id=user.id, cin=f'ADMIN-{user.id}'))
        elif role.name == 'employee':
            dept_id = form.department_id.data if form.department_id.data else None
            db.session.add(Employee(user_id=user.id, department_id=dept_id, matricule=f'EMP-{user.id}'))

        db.session.commit()
        log_action('creation-utilisateur', user.email)
        flash(_('Utilisateur créé avec succès.'), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('dashboard_admin') + '#utilisateurs')


@app.route('/admin/utilisateurs/<int:user_id>/modifier', methods=['POST'])
@admin_required
def admin_user_edit(user_id):
    user = User.query.get_or_404(user_id)
    form = UserAdminForm()
    form.role_id.choices = [(r.id, r.label_fr) for r in Role.query.all()]
    form.department_id.choices = [(0, '-')] + [(d.id, d.name_fr) for d in Department.query.all()]

    if form.validate_on_submit():
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.phone = form.phone.data
        user.role_id = form.role_id.data
        user.is_active_account = form.is_active_account.data
        if form.password.data:
            user.set_password(form.password.data)
        if user.employee_profile and form.department_id.data:
            user.employee_profile.department_id = form.department_id.data
        db.session.commit()
        log_action('modification-utilisateur', user.email)
        flash(_('Utilisateur mis à jour avec succès.'), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('dashboard_admin') + '#utilisateurs')


@app.route('/admin/utilisateurs/<int:user_id>/activer-desactiver', methods=['POST'])
@admin_required
def admin_user_toggle_active(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active_account = not user.is_active_account
    db.session.commit()
    log_action('activation-desactivation-utilisateur', user.email)
    flash(_('Le statut du compte a été mis à jour.'), 'success')
    return redirect(url_for('dashboard_admin') + '#utilisateurs')


@app.route('/admin/utilisateurs/<int:user_id>/supprimer', methods=['POST'])
@admin_required
def admin_user_delete(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash(_('Vous ne pouvez pas supprimer votre propre compte.'), 'danger')
        return redirect(url_for('dashboard_admin') + '#utilisateurs')
    db.session.delete(user)
    db.session.commit()
    log_action('suppression-utilisateur', user.email)
    flash(_('Utilisateur supprimé avec succès.'), 'success')
    return redirect(url_for('dashboard_admin') + '#utilisateurs')


# ===========================================================================
# ADMINISTRATION : DEPARTEMENTS
# ===========================================================================

@app.route('/admin/departements', methods=['POST'])
@admin_required
def admin_department_create():
    form = DepartmentForm()
    if form.validate_on_submit():
        db.session.add(Department(
            name_fr=form.name_fr.data, name_ar=form.name_ar.data,
            description_fr=form.description_fr.data, description_ar=form.description_ar.data))
        db.session.commit()
        flash(_('Département créé avec succès.'), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('dashboard_admin') + '#departements')


@app.route('/admin/departements/<int:department_id>/modifier', methods=['POST'])
@admin_required
def admin_department_edit(department_id):
    department = Department.query.get_or_404(department_id)
    form = DepartmentForm()
    if form.validate_on_submit():
        department.name_fr = form.name_fr.data
        department.name_ar = form.name_ar.data
        department.description_fr = form.description_fr.data
        department.description_ar = form.description_ar.data
        db.session.commit()
        flash(_('Département mis à jour avec succès.'), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('dashboard_admin') + '#departements')


@app.route('/admin/departements/<int:department_id>/supprimer', methods=['POST'])
@admin_required
def admin_department_delete(department_id):
    department = Department.query.get_or_404(department_id)
    db.session.delete(department)
    db.session.commit()
    flash(_('Département supprimé avec succès.'), 'success')
    return redirect(url_for('dashboard_admin') + '#departements')


# ===========================================================================
# ADMINISTRATION : SERVICES
# ===========================================================================

def _slugify(text):
    import re
    import unicodedata
    normalized = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', normalized).strip('-').lower()
    return slug or 'service'


@app.route('/admin/services', methods=['POST'])
@admin_required
def admin_service_create():
    form = ServiceForm()
    form.department_id.choices = [(0, '-')] + [(d.id, d.name_fr) for d in Department.query.all()]

    if form.validate_on_submit():
        slug = _slugify(form.name_fr.data)
        if Service.query.filter_by(slug=slug).first():
            slug = f'{slug}-{Service.query.count() + 1}'
        image_path = save_uploaded_file(form.image.data, 'services') if form.image.data else None
        db.session.add(Service(
            department_id=form.department_id.data or None, name_fr=form.name_fr.data,
            name_ar=form.name_ar.data, description_fr=form.description_fr.data,
            description_ar=form.description_ar.data, icon=form.icon.data or 'bi-briefcase',
            image=image_path, slug=slug, order=form.order.data or 0, active=form.active.data))
        db.session.commit()
        flash(_('Service créé avec succès.'), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('dashboard_admin') + '#services')


@app.route('/admin/services/<int:service_id>/modifier', methods=['POST'])
@admin_required
def admin_service_edit(service_id):
    service = Service.query.get_or_404(service_id)
    form = ServiceForm()
    form.department_id.choices = [(0, '-')] + [(d.id, d.name_fr) for d in Department.query.all()]

    if form.validate_on_submit():
        service.department_id = form.department_id.data or None
        service.name_fr = form.name_fr.data
        service.name_ar = form.name_ar.data
        service.description_fr = form.description_fr.data
        service.description_ar = form.description_ar.data
        service.icon = form.icon.data or service.icon
        service.order = form.order.data or 0
        service.active = form.active.data
        if form.image.data:
            delete_uploaded_file(service.image)
            service.image = save_uploaded_file(form.image.data, 'services')
        db.session.commit()
        flash(_('Service mis à jour avec succès.'), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('dashboard_admin') + '#services')


@app.route('/admin/services/<int:service_id>/supprimer', methods=['POST'])
@admin_required
def admin_service_delete(service_id):
    service = Service.query.get_or_404(service_id)
    delete_uploaded_file(service.image)
    db.session.delete(service)
    db.session.commit()
    flash(_('Service supprimé avec succès.'), 'success')
    return redirect(url_for('dashboard_admin') + '#services')


# ===========================================================================
# ADMINISTRATION : ACTUALITES
# ===========================================================================

@app.route('/admin/actualites', methods=['POST'])
@admin_required
def admin_news_create():
    form = NewsForm()
    if form.validate_on_submit():
        image_path = save_uploaded_file(form.image.data, 'news') if form.image.data else None
        db.session.add(News(
            title_fr=form.title_fr.data, title_ar=form.title_ar.data,
            content_fr=form.content_fr.data, content_ar=form.content_ar.data,
            image=image_path, author_id=current_user.id, active=form.active.data))
        db.session.commit()
        flash(_('Actualité publiée avec succès.'), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('dashboard_admin') + '#actualites')


@app.route('/admin/actualites/<int:news_id>/modifier', methods=['POST'])
@admin_required
def admin_news_edit(news_id):
    news_item = News.query.get_or_404(news_id)
    form = NewsForm()
    if form.validate_on_submit():
        news_item.title_fr = form.title_fr.data
        news_item.title_ar = form.title_ar.data
        news_item.content_fr = form.content_fr.data
        news_item.content_ar = form.content_ar.data
        news_item.active = form.active.data
        if form.image.data:
            delete_uploaded_file(news_item.image)
            news_item.image = save_uploaded_file(form.image.data, 'news')
        db.session.commit()
        flash(_('Actualité mise à jour avec succès.'), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('dashboard_admin') + '#actualites')


@app.route('/admin/actualites/<int:news_id>/supprimer', methods=['POST'])
@admin_required
def admin_news_delete(news_id):
    news_item = News.query.get_or_404(news_id)
    delete_uploaded_file(news_item.image)
    db.session.delete(news_item)
    db.session.commit()
    flash(_('Actualité supprimée avec succès.'), 'success')
    return redirect(url_for('dashboard_admin') + '#actualites')


# ===========================================================================
# ADMINISTRATION : DOCUMENTS PUBLICS & PLAN D'AMENAGEMENT
# ===========================================================================

@app.route('/admin/documents', methods=['POST'])
@admin_required
def admin_document_create():
    form = PublicDocumentForm()
    form.service_id.choices = [(0, '-')] + [
        (s.id, s.name_fr) for s in Service.query.filter_by(active=True).order_by(Service.order)]

    if form.validate_on_submit() and form.file.data:
        file_path = save_uploaded_file(form.file.data, 'documents')
        db.session.add(PublicDocument(
            service_id=form.service_id.data or None, title_fr=form.title_fr.data,
            title_ar=form.title_ar.data, reference=form.reference.data,
            category=form.category.data, file_path=file_path, uploaded_by_id=current_user.id))
        db.session.commit()
        flash(_('Document publié avec succès.'), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('dashboard_admin') + '#documents')


@app.route('/admin/documents/<int:document_id>/modifier', methods=['POST'])
@admin_required
def admin_document_edit(document_id):
    document = PublicDocument.query.get_or_404(document_id)
    form = PublicDocumentForm()
    form.service_id.choices = [(0, '-')] + [
        (s.id, s.name_fr) for s in Service.query.filter_by(active=True).order_by(Service.order)]

    if form.validate_on_submit():
        document.service_id = form.service_id.data or None
        document.title_fr = form.title_fr.data
        document.title_ar = form.title_ar.data
        document.reference = form.reference.data
        document.category = form.category.data
        if form.file.data:
            delete_uploaded_file(document.file_path)
            document.file_path = save_uploaded_file(form.file.data, 'documents')
        db.session.commit()
        flash(_('Document mis à jour avec succès.'), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('dashboard_admin') + '#documents')


@app.route('/admin/documents/<int:document_id>/supprimer', methods=['POST'])
@admin_required
def admin_document_delete(document_id):
    document = PublicDocument.query.get_or_404(document_id)
    delete_uploaded_file(document.file_path)
    db.session.delete(document)
    db.session.commit()
    flash(_('Document supprimé avec succès.'), 'success')
    return redirect(url_for('dashboard_admin') + '#documents')


@app.route('/admin/plans-amenagement', methods=['POST'])
@admin_required
def admin_urban_plan_create():
    form = UrbanPlanForm()
    if form.validate_on_submit() and form.file.data:
        file_path = save_uploaded_file(form.file.data, 'urban_plans')
        db.session.add(UrbanPlan(
            title_fr=form.title_fr.data, title_ar=form.title_ar.data,
            description_fr=form.description_fr.data, description_ar=form.description_ar.data,
            file_path=file_path, active=form.active.data))
        db.session.commit()
        flash(_("Plan d'aménagement ajouté avec succès."), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('dashboard_admin') + '#plans')


@app.route('/admin/plans-amenagement/<int:plan_id>/activer', methods=['POST'])
@admin_required
def admin_urban_plan_activate(plan_id):
    UrbanPlan.query.update({'active': False})
    plan = UrbanPlan.query.get_or_404(plan_id)
    plan.active = True
    db.session.commit()
    flash(_("Le plan d'aménagement affiché sur le site a été mis à jour."), 'success')
    return redirect(url_for('dashboard_admin') + '#plans')


@app.route('/admin/plans-amenagement/<int:plan_id>/supprimer', methods=['POST'])
@admin_required
def admin_urban_plan_delete(plan_id):
    plan = UrbanPlan.query.get_or_404(plan_id)
    delete_uploaded_file(plan.file_path)
    db.session.delete(plan)
    db.session.commit()
    flash(_("Plan d'aménagement supprimé avec succès."), 'success')
    return redirect(url_for('dashboard_admin') + '#plans')


# ===========================================================================
# ADMINISTRATION : GALERIE & VIDEOS
# ===========================================================================

@app.route('/admin/galerie', methods=['POST'])
@admin_required
def admin_gallery_add():
    form = GalleryImageForm()
    if form.validate_on_submit():
        image_path = save_uploaded_file(form.image.data, 'gallery')
        db.session.add(GalleryImage(
            title_fr=form.title_fr.data, title_ar=form.title_ar.data,
            category=form.category.data, image_path=image_path))
        db.session.commit()
        flash(_('Image ajoutée à la galerie avec succès.'), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('dashboard_admin') + '#galerie')


@app.route('/admin/galerie/<int:image_id>/supprimer', methods=['POST'])
@admin_required
def admin_gallery_delete(image_id):
    image = GalleryImage.query.get_or_404(image_id)
    delete_uploaded_file(image.image_path)
    db.session.delete(image)
    db.session.commit()
    flash(_('Image supprimée avec succès.'), 'success')
    return redirect(url_for('dashboard_admin') + '#galerie')


@app.route('/admin/videos', methods=['POST'])
@admin_required
def admin_video_add():
    form = VideoForm()
    if form.validate_on_submit():
        db.session.add(Video(title_fr=form.title_fr.data, title_ar=form.title_ar.data, url=form.url.data))
        db.session.commit()
        flash(_('Vidéo ajoutée avec succès.'), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('dashboard_admin') + '#videos')


@app.route('/admin/videos/<int:video_id>/supprimer', methods=['POST'])
@admin_required
def admin_video_delete(video_id):
    video = Video.query.get_or_404(video_id)
    db.session.delete(video)
    db.session.commit()
    flash(_('Vidéo supprimée avec succès.'), 'success')
    return redirect(url_for('dashboard_admin') + '#videos')


# ===========================================================================
# ADMINISTRATION : PARAMETRES DU SITE
# ===========================================================================

@app.route('/admin/parametres/<key>', methods=['POST'])
@admin_required
def admin_setting_update(key):
    form = SettingForm()
    setting = Setting.query.filter_by(key=key).first()
    if form.validate_on_submit():
        if not setting:
            setting = Setting(key=key)
            db.session.add(setting)
        setting.value = form.value.data
        db.session.commit()
        flash(_('Paramètre mis à jour avec succès.'), 'success')
    else:
        flash_errors(form)
    return redirect(url_for('dashboard_admin') + '#parametres')


# ===========================================================================
# API (Flask-JWT-Extended) - integration mobile / tiers
# ===========================================================================

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').lower().strip()
    password = data.get('password') or ''

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password) or not user.is_active_account:
        return jsonify({'error': 'Identifiants invalides.'}), 401

    access_token = create_access_token(identity=str(user.id))
    return jsonify({'access_token': access_token, 'user': {
        'id': user.id, 'email': user.email, 'full_name': user.full_name, 'role': user.role.name,
    }})


@app.route('/api/mes-demandes')
@jwt_required()
def api_my_requests():
    user = User.query.get_or_404(int(get_jwt_identity()))
    if not user.citizen_profile:
        return jsonify({'error': "Cet utilisateur n'a pas de profil citoyen."}), 403

    items = user.citizen_profile.requests.order_by(ServiceRequest.created_at.desc()).all()
    return jsonify(requests_schema.dump(items))


@app.route('/api/suivi/<tracking_number>')
def api_track_request(tracking_number):
    service_request = ServiceRequest.query.filter_by(tracking_number=tracking_number).first()
    if not service_request:
        return jsonify({'error': 'Numéro de suivi introuvable.'}), 404
    return jsonify(request_schema.dump(service_request))
