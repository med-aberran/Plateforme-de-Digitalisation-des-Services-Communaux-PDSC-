# -*- coding: utf-8 -*-
"""
models.py
=========
Tous les modeles SQLAlchemy de la plateforme PDSC sont centralises dans ce
fichier unique, conformement au choix d'architecture simple du projet.

Les instances d'extensions qui doivent obligatoirement etre visibles a la
fois par les modeles et par le reste de l'application (SQLAlchemy,
LoginManager) sont egalement declarees ici.
"""

from datetime import datetime

from flask_login import LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------------------------------------------------------------------
# Constantes de workflow (utilisees par forms.py, routes.py et les templates)
# ---------------------------------------------------------------------------

# (code, libelle_fr, libelle_ar, classe_css_badge)
REQUEST_STATUSES = [
    ('brouillon', 'Brouillon', 'مسودة', 'secondary'),
    ('soumise', 'Soumise', 'مُقدَّمة', 'info'),
    ('en_attente', 'En attente', 'قيد الانتظار', 'warning'),
    ('affectee', 'Affectée', 'موكَّلة', 'info'),
    ('en_cours', 'En cours de traitement', 'قيد المعالجة', 'primary'),
    ('documents_manquants', 'Documents manquants', 'وثائق ناقصة', 'danger'),
    ('validee', 'Validée', 'مقبولة', 'success'),
    ('terminee', 'Terminée', 'منجزة', 'success'),
    ('refusee', 'Refusée', 'مرفوضة', 'danger'),
    ('archivee', 'Archivée', 'مؤرشفة', 'secondary'),
]
REQUEST_STATUS_CODES = [s[0] for s in REQUEST_STATUSES]

APPOINTMENT_STATUSES = [
    ('en_attente', 'En attente', 'قيد الانتظار', 'warning'),
    ('confirme', 'Confirmé', 'مؤكد', 'success'),
    ('annule', 'Annulé', 'ملغى', 'danger'),
    ('termine', 'Terminé', 'منتهي', 'secondary'),
]
APPOINTMENT_STATUS_CODES = [s[0] for s in APPOINTMENT_STATUSES]

COMPLAINT_STATUSES = [
    ('ouverte', 'Ouverte', 'مفتوحة', 'warning'),
    ('en_cours', 'En cours', 'قيد المعالجة', 'primary'),
    ('repondue', 'Répondue', 'تمت الإجابة عليها', 'info'),
    ('cloturee', 'Clôturée', 'مغلقة', 'secondary'),
]
COMPLAINT_STATUS_CODES = [s[0] for s in COMPLAINT_STATUSES]

DOCUMENT_CATEGORIES = [
    ('formulaire', 'Formulaire', 'استمارة'),
    ('reglement', 'Règlement', 'نظام'),
    ('document', 'Document', 'وثيقة'),
]


# ---------------------------------------------------------------------------
# Utilisateurs & roles
# ---------------------------------------------------------------------------

class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)  # admin | employee | citizen
    label_fr = db.Column(db.String(60), nullable=False)
    label_ar = db.Column(db.String(60), nullable=False)

    users = db.relationship('User', backref='role', lazy=True)

    def __repr__(self):
        return f'<Role {self.name}>'


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(20))
    avatar = db.Column(db.String(255))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    is_active_account = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    preferred_language = db.Column(db.String(5), default='fr')
    verify_token = db.Column(db.String(255))
    reset_token = db.Column(db.String(255))
    reset_token_expiry = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    citizen_profile = db.relationship(
        'Citizen', backref='user', uselist=False, cascade='all, delete-orphan')
    employee_profile = db.relationship(
        'Employee', backref='user', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship(
        'Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    # --- mots de passe ---
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # --- Flask-Login ---
    @property
    def is_active(self):  # noqa: overrides UserMixin default flag
        return self.is_active_account

    # --- helpers ---
    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def has_role(self, *role_names):
        return bool(self.role) and self.role.name in role_names

    def unread_notifications_count(self):
        return self.notifications.filter_by(is_read=False).count()

    def __repr__(self):
        return f'<User {self.email}>'


class Citizen(db.Model):
    __tablename__ = 'citizens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    cin = db.Column(db.String(20), unique=True)
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    birth_date = db.Column(db.Date)

    requests = db.relationship('ServiceRequest', backref='citizen', lazy='dynamic',
                                cascade='all, delete-orphan')
    appointments = db.relationship('Appointment', backref='citizen', lazy='dynamic',
                                    cascade='all, delete-orphan')
    complaints = db.relationship('Complaint', backref='citizen', lazy='dynamic',
                                  cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Citizen {self.cin}>'


class Employee(db.Model):
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    matricule = db.Column(db.String(30), unique=True)
    position = db.Column(db.String(120))

    assigned_requests = db.relationship('ServiceRequest', backref='employee', lazy='dynamic')

    def __repr__(self):
        return f'<Employee {self.matricule}>'


# ---------------------------------------------------------------------------
# Departements & services
# ---------------------------------------------------------------------------

class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    name_fr = db.Column(db.String(150), nullable=False)
    name_ar = db.Column(db.String(150), nullable=False)
    description_fr = db.Column(db.Text)
    description_ar = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employees = db.relationship('Employee', backref='department', lazy=True)
    services = db.relationship('Service', backref='department', lazy=True)
    complaints = db.relationship('Complaint', backref='department', lazy=True)

    def __repr__(self):
        return f'<Department {self.name_fr}>'


class Service(db.Model):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    name_fr = db.Column(db.String(150), nullable=False)
    name_ar = db.Column(db.String(150), nullable=False)
    description_fr = db.Column(db.Text)
    description_ar = db.Column(db.Text)
    image = db.Column(db.String(255))
    icon = db.Column(db.String(60), default='bi-briefcase')
    slug = db.Column(db.String(160), unique=True, nullable=False)
    order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    requests = db.relationship('ServiceRequest', backref='service', lazy='dynamic')
    appointments = db.relationship('Appointment', backref='service', lazy='dynamic')

    def __repr__(self):
        return f'<Service {self.slug}>'


# ---------------------------------------------------------------------------
# Demandes administratives
# ---------------------------------------------------------------------------

class ServiceRequest(db.Model):
    """Represente une demande administrative deposee par un citoyen.

    NB: la classe n'est pas nommee ``Request`` afin d'eviter tout conflit
    avec l'objet ``flask.request`` utilise partout ailleurs dans le projet.
    """
    __tablename__ = 'requests'

    id = db.Column(db.Integer, primary_key=True)
    tracking_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    citizen_id = db.Column(db.Integer, db.ForeignKey('citizens.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    status = db.Column(db.String(30), default='soumise', nullable=False)
    notes = db.Column(db.Text)
    qr_code = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = db.relationship('RequestDocument', backref='request', lazy='dynamic',
                                 cascade='all, delete-orphan')
    history = db.relationship('RequestHistory', backref='request', lazy='dynamic',
                               order_by='RequestHistory.created_at.desc()',
                               cascade='all, delete-orphan')
    comments = db.relationship('RequestComment', backref='request', lazy='dynamic',
                                order_by='RequestComment.created_at.asc()',
                                cascade='all, delete-orphan')

    def status_label(self, lang='fr'):
        for code, fr, ar, css in REQUEST_STATUSES:
            if code == self.status:
                return ar if lang == 'ar' else fr
        return self.status

    def status_css(self):
        for code, fr, ar, css in REQUEST_STATUSES:
            if code == self.status:
                return css
        return 'secondary'

    def __repr__(self):
        return f'<ServiceRequest {self.tracking_number}>'


class RequestDocument(db.Model):
    __tablename__ = 'request_documents'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<RequestDocument {self.filename}>'


class RequestHistory(db.Model):
    """Historique des changements de statut d'une demande."""
    __tablename__ = 'request_history'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.id'), nullable=False)
    status = db.Column(db.String(30), nullable=False)
    comment = db.Column(db.Text)
    changed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    changed_by = db.relationship('User')

    def __repr__(self):
        return f'<RequestHistory {self.request_id}:{self.status}>'


class RequestComment(db.Model):
    """Commentaires internes/echanges autour d'une demande."""
    __tablename__ = 'request_comments'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User')

    def __repr__(self):
        return f'<RequestComment {self.id}>'


# ---------------------------------------------------------------------------
# Rendez-vous & reclamations
# ---------------------------------------------------------------------------

class Appointment(db.Model):
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    citizen_id = db.Column(db.Integer, db.ForeignKey('citizens.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='en_attente', nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def status_label(self, lang='fr'):
        for code, fr, ar, css in APPOINTMENT_STATUSES:
            if code == self.status:
                return ar if lang == 'ar' else fr
        return self.status

    def status_css(self):
        for code, fr, ar, css in APPOINTMENT_STATUSES:
            if code == self.status:
                return css
        return 'secondary'

    def __repr__(self):
        return f'<Appointment {self.id}>'


class Complaint(db.Model):
    __tablename__ = 'complaints'

    id = db.Column(db.Integer, primary_key=True)
    citizen_id = db.Column(db.Integer, db.ForeignKey('citizens.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text)
    status = db.Column(db.String(20), default='ouverte', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = db.Column(db.DateTime)

    def status_label(self, lang='fr'):
        for code, fr, ar, css in COMPLAINT_STATUSES:
            if code == self.status:
                return ar if lang == 'ar' else fr
        return self.status

    def status_css(self):
        for code, fr, ar, css in COMPLAINT_STATUSES:
            if code == self.status:
                return css
        return 'secondary'

    def __repr__(self):
        return f'<Complaint {self.id}>'


# ---------------------------------------------------------------------------
# Contenus publics : actualites, documents, plans, galerie, videos
# ---------------------------------------------------------------------------

class News(db.Model):
    __tablename__ = 'news'

    id = db.Column(db.Integer, primary_key=True)
    title_fr = db.Column(db.String(200), nullable=False)
    title_ar = db.Column(db.String(200), nullable=False)
    content_fr = db.Column(db.Text, nullable=False)
    content_ar = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(255))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    active = db.Column(db.Boolean, default=True)
    published_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User')

    def __repr__(self):
        return f'<News {self.title_fr}>'


class PublicDocument(db.Model):
    __tablename__ = 'public_documents'

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'))
    title_fr = db.Column(db.String(200), nullable=False)
    title_ar = db.Column(db.String(200), nullable=False)
    reference = db.Column(db.String(50))
    category = db.Column(db.String(30), default='document')
    file_path = db.Column(db.String(255), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    service = db.relationship('Service', backref=db.backref('documents', lazy='dynamic'))

    def __repr__(self):
        return f'<PublicDocument {self.title_fr}>'


class UrbanPlan(db.Model):
    """Plan d'amenagement affiche via la visionneuse PDF de la page d'accueil."""
    __tablename__ = 'urban_plans'

    id = db.Column(db.Integer, primary_key=True)
    title_fr = db.Column(db.String(200), nullable=False)
    title_ar = db.Column(db.String(200), nullable=False)
    description_fr = db.Column(db.Text)
    description_ar = db.Column(db.Text)
    file_path = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<UrbanPlan {self.title_fr}>'


class GalleryImage(db.Model):
    __tablename__ = 'gallery_images'

    id = db.Column(db.Integer, primary_key=True)
    title_fr = db.Column(db.String(200))
    title_ar = db.Column(db.String(200))
    image_path = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(60))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<GalleryImage {self.id}>'


class Video(db.Model):
    __tablename__ = 'videos'

    id = db.Column(db.Integer, primary_key=True)
    title_fr = db.Column(db.String(200))
    title_ar = db.Column(db.String(200))
    url = db.Column(db.String(255), nullable=False)
    thumbnail = db.Column(db.String(255))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Video {self.id}>'


# ---------------------------------------------------------------------------
# Notifications, journalisation, parametres
# ---------------------------------------------------------------------------

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    link = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Notification {self.id}>'


class Log(db.Model):
    """Journal des actions (piste d'audit)."""
    __tablename__ = 'logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(150), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')

    def __repr__(self):
        return f'<Log {self.action}>'


class Setting(db.Model):
    """Parametres cle/valeur configurables depuis le tableau de bord admin."""
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.String(255))

    def __repr__(self):
        return f'<Setting {self.key}>'
