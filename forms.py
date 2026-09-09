# -*- coding: utf-8 -*-
"""
forms.py
========
Tous les formulaires Flask-WTF de la plateforme PDSC sont regroupes dans ce
fichier unique. Les libelles utilisent flask_babel.lazy_gettext afin d'etre
traduits dynamiquement selon la langue active (voir translations/).
"""

from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, MultipleFileField
from wtforms import (
    BooleanField, DateField, IntegerField, PasswordField, SelectField,
    StringField, SubmitField, TextAreaField, TimeField,
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, Optional, ValidationError,
)

from models import DOCUMENT_CATEGORIES, User

IMAGE_EXT = ('jpg', 'jpeg', 'png', 'gif', 'webp')
DOC_EXT = ('pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png')


# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------

class RegisterForm(FlaskForm):
    first_name = StringField(_l('Prénom'), validators=[DataRequired(), Length(max=80)])
    last_name = StringField(_l('Nom'), validators=[DataRequired(), Length(max=80)])
    email = StringField(_l('Adresse e-mail'), validators=[DataRequired(), Email(), Length(max=150)])
    phone = StringField(_l('Téléphone'), validators=[Optional(), Length(max=20)])
    cin = StringField(_l('CIN'), validators=[DataRequired(), Length(max=20)])
    password = PasswordField(_l('Mot de passe'), validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        _l('Confirmer le mot de passe'),
        validators=[DataRequired(), EqualTo('password', message=_l('Les mots de passe ne correspondent pas.'))])
    accept_terms = BooleanField(
        _l("J'accepte les conditions d'utilisation"), validators=[DataRequired()])
    submit = SubmitField(_l("S'inscrire"))

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower().strip()).first():
            raise ValidationError(_l('Cette adresse e-mail est déjà utilisée.'))


class LoginForm(FlaskForm):
    email = StringField(_l('Adresse e-mail'), validators=[DataRequired(), Email()])
    password = PasswordField(_l('Mot de passe'), validators=[DataRequired()])
    remember_me = BooleanField(_l('Se souvenir de moi'))
    submit = SubmitField(_l('Se connecter'))


class ForgotPasswordForm(FlaskForm):
    email = StringField(_l('Adresse e-mail'), validators=[DataRequired(), Email()])
    submit = SubmitField(_l('Envoyer le lien de réinitialisation'))


class ResetPasswordForm(FlaskForm):
    password = PasswordField(_l('Nouveau mot de passe'), validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        _l('Confirmer le mot de passe'),
        validators=[DataRequired(), EqualTo('password', message=_l('Les mots de passe ne correspondent pas.'))])
    submit = SubmitField(_l('Réinitialiser le mot de passe'))


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(_l('Mot de passe actuel'), validators=[DataRequired()])
    password = PasswordField(_l('Nouveau mot de passe'), validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        _l('Confirmer le mot de passe'),
        validators=[DataRequired(), EqualTo('password', message=_l('Les mots de passe ne correspondent pas.'))])
    submit = SubmitField(_l('Changer le mot de passe'))


# ---------------------------------------------------------------------------
# Profil citoyen
# ---------------------------------------------------------------------------

class ProfileForm(FlaskForm):
    first_name = StringField(_l('Prénom'), validators=[DataRequired(), Length(max=80)])
    last_name = StringField(_l('Nom'), validators=[DataRequired(), Length(max=80)])
    phone = StringField(_l('Téléphone'), validators=[Optional(), Length(max=20)])
    address = StringField(_l('Adresse'), validators=[Optional(), Length(max=255)])
    city = StringField(_l('Ville'), validators=[Optional(), Length(max=100)])
    avatar = FileField(_l('Photo de profil'), validators=[Optional(), FileAllowed(IMAGE_EXT, _l('Images uniquement.'))])
    preferred_language = SelectField(_l('Langue préférée'), choices=[('fr', 'Français'), ('ar', 'العربية')])
    submit = SubmitField(_l('Enregistrer'))


# ---------------------------------------------------------------------------
# Demandes, rendez-vous, reclamations (citoyen)
# ---------------------------------------------------------------------------

class ServiceRequestForm(FlaskForm):
    service_id = SelectField(_l('Service concerné'), coerce=int, validators=[DataRequired()])
    notes = TextAreaField(_l('Description de la demande'), validators=[Optional(), Length(max=2000)])
    documents = MultipleFileField(
        _l('Pièces jointes'),
        validators=[Optional(), FileAllowed(DOC_EXT, _l('Formats autorisés : PDF, DOC, DOCX, JPG, PNG.'))])
    submit = SubmitField(_l('Soumettre la demande'))


class AppointmentForm(FlaskForm):
    service_id = SelectField(_l('Service concerné'), coerce=int, validators=[DataRequired()])
    appointment_date = DateField(_l('Date souhaitée'), validators=[DataRequired()])
    appointment_time = TimeField(_l('Heure souhaitée'), validators=[DataRequired()])
    notes = TextAreaField(_l('Motif du rendez-vous'), validators=[Optional(), Length(max=1000)])
    submit = SubmitField(_l('Réserver'))


class ComplaintForm(FlaskForm):
    department_id = SelectField(_l('Département concerné'), coerce=int, validators=[Optional()])
    subject = StringField(_l('Objet'), validators=[DataRequired(), Length(max=200)])
    description = TextAreaField(_l('Description'), validators=[DataRequired(), Length(max=3000)])
    submit = SubmitField(_l('Envoyer la réclamation'))


class ContactForm(FlaskForm):
    name = StringField(_l('Nom complet'), validators=[DataRequired(), Length(max=150)])
    email = StringField(_l('Adresse e-mail'), validators=[DataRequired(), Email()])
    subject = StringField(_l('Objet'), validators=[DataRequired(), Length(max=200)])
    message = TextAreaField(_l('Message'), validators=[DataRequired(), Length(max=2000)])
    submit = SubmitField(_l('Envoyer'))


# ---------------------------------------------------------------------------
# Traitement des demandes / rendez-vous / reclamations (employe)
# Les choix de statut sont peuples dynamiquement dans routes.py a partir des
# tuples bilingues definis dans models.py (REQUEST_STATUSES, etc.) afin de
# refleter la langue active sans dependre du catalogue de traduction.
# ---------------------------------------------------------------------------

class UpdateRequestStatusForm(FlaskForm):
    status = SelectField(_l('Nouveau statut'), validators=[DataRequired()])
    comment = TextAreaField(_l('Commentaire (visible par le citoyen)'), validators=[Optional(), Length(max=1000)])
    submit = SubmitField(_l('Mettre à jour'))


class RequestCommentForm(FlaskForm):
    comment = TextAreaField(_l('Ajouter un commentaire'), validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField(_l('Publier'))


class AssignEmployeeForm(FlaskForm):
    employee_id = SelectField(_l("Affecter à l'employé"), coerce=int, validators=[DataRequired()])
    submit = SubmitField(_l('Affecter'))


class AppointmentStatusForm(FlaskForm):
    status = SelectField(_l('Statut'), validators=[DataRequired()])
    submit = SubmitField(_l('Mettre à jour'))


class ComplaintResponseForm(FlaskForm):
    response = TextAreaField(_l('Réponse'), validators=[DataRequired(), Length(max=3000)])
    status = SelectField(_l('Statut'), validators=[DataRequired()])
    submit = SubmitField(_l('Répondre'))


# ---------------------------------------------------------------------------
# Administration : utilisateurs, departements, services
# ---------------------------------------------------------------------------

class UserAdminForm(FlaskForm):
    first_name = StringField(_l('Prénom'), validators=[DataRequired(), Length(max=80)])
    last_name = StringField(_l('Nom'), validators=[DataRequired(), Length(max=80)])
    email = StringField(_l('Adresse e-mail'), validators=[DataRequired(), Email()])
    phone = StringField(_l('Téléphone'), validators=[Optional(), Length(max=20)])
    role_id = SelectField(_l('Rôle'), coerce=int, validators=[DataRequired()])
    department_id = SelectField(_l('Département (employé)'), coerce=int, validators=[Optional()])
    is_active_account = BooleanField(_l('Compte actif'), default=True)
    password = PasswordField(
        _l('Mot de passe (laisser vide pour ne pas modifier)'),
        validators=[Optional(), Length(min=8)])
    submit = SubmitField(_l('Enregistrer'))


class DepartmentForm(FlaskForm):
    name_fr = StringField(_l('Nom (Français)'), validators=[DataRequired(), Length(max=150)])
    name_ar = StringField(_l('Nom (Arabe)'), validators=[DataRequired(), Length(max=150)])
    description_fr = TextAreaField(_l('Description (Français)'), validators=[Optional()])
    description_ar = TextAreaField(_l('Description (Arabe)'), validators=[Optional()])
    submit = SubmitField(_l('Enregistrer'))


class ServiceForm(FlaskForm):
    department_id = SelectField(_l('Département'), coerce=int, validators=[Optional()])
    name_fr = StringField(_l('Nom (Français)'), validators=[DataRequired(), Length(max=150)])
    name_ar = StringField(_l('Nom (Arabe)'), validators=[DataRequired(), Length(max=150)])
    description_fr = TextAreaField(_l('Description (Français)'), validators=[Optional()])
    description_ar = TextAreaField(_l('Description (Arabe)'), validators=[Optional()])
    icon = StringField(_l('Icône (classe Bootstrap Icons)'), validators=[Optional(), Length(max=60)])
    image = FileField(_l('Image'), validators=[Optional(), FileAllowed(IMAGE_EXT, _l('Images uniquement.'))])
    order = IntegerField(_l("Ordre d'affichage"), default=0, validators=[Optional()])
    active = BooleanField(_l('Actif'), default=True)
    submit = SubmitField(_l('Enregistrer'))


# ---------------------------------------------------------------------------
# Administration : contenus publics
# ---------------------------------------------------------------------------

class NewsForm(FlaskForm):
    title_fr = StringField(_l('Titre (Français)'), validators=[DataRequired(), Length(max=200)])
    title_ar = StringField(_l('Titre (Arabe)'), validators=[DataRequired(), Length(max=200)])
    content_fr = TextAreaField(_l('Contenu (Français)'), validators=[DataRequired()])
    content_ar = TextAreaField(_l('Contenu (Arabe)'), validators=[DataRequired()])
    image = FileField(_l('Image'), validators=[Optional(), FileAllowed(IMAGE_EXT, _l('Images uniquement.'))])
    active = BooleanField(_l('Publiée'), default=True)
    submit = SubmitField(_l('Enregistrer'))


class PublicDocumentForm(FlaskForm):
    service_id = SelectField(_l('Service concerné'), coerce=int, validators=[Optional()])
    title_fr = StringField(_l('Titre (Français)'), validators=[DataRequired(), Length(max=200)])
    title_ar = StringField(_l('Titre (Arabe)'), validators=[DataRequired(), Length(max=200)])
    reference = StringField(_l('Référence / Numéro'), validators=[Optional(), Length(max=50)])
    category = SelectField(_l('Catégorie'), choices=[(c[0], c[1]) for c in DOCUMENT_CATEGORIES],
                            validators=[DataRequired()])
    file = FileField(_l('Fichier'), validators=[Optional(), FileAllowed(DOC_EXT, _l('Formats autorisés : PDF, DOC, DOCX.'))])
    submit = SubmitField(_l('Enregistrer'))


class UrbanPlanForm(FlaskForm):
    title_fr = StringField(_l('Titre (Français)'), validators=[DataRequired(), Length(max=200)])
    title_ar = StringField(_l('Titre (Arabe)'), validators=[DataRequired(), Length(max=200)])
    description_fr = TextAreaField(_l('Description (Français)'), validators=[Optional()])
    description_ar = TextAreaField(_l('Description (Arabe)'), validators=[Optional()])
    file = FileField(_l('Fichier PDF'), validators=[Optional(), FileAllowed(('pdf',), _l('PDF uniquement.'))])
    active = BooleanField(_l('Actif'), default=True)
    submit = SubmitField(_l('Enregistrer'))


class GalleryImageForm(FlaskForm):
    title_fr = StringField(_l('Titre (Français)'), validators=[Optional(), Length(max=200)])
    title_ar = StringField(_l('Titre (Arabe)'), validators=[Optional(), Length(max=200)])
    category = StringField(_l('Catégorie'), validators=[Optional(), Length(max=60)])
    image = FileField(_l('Image'), validators=[DataRequired(), FileAllowed(IMAGE_EXT, _l('Images uniquement.'))])
    submit = SubmitField(_l('Ajouter'))


class VideoForm(FlaskForm):
    title_fr = StringField(_l('Titre (Français)'), validators=[Optional(), Length(max=200)])
    title_ar = StringField(_l('Titre (Arabe)'), validators=[Optional(), Length(max=200)])
    url = StringField(_l('URL de la vidéo (YouTube/Vimeo)'), validators=[DataRequired(), Length(max=255)])
    submit = SubmitField(_l('Ajouter'))


class SettingForm(FlaskForm):
    value = StringField(_l('Valeur'), validators=[Optional(), Length(max=1000)])
    submit = SubmitField(_l('Enregistrer'))


class SearchForm(FlaskForm):
    q = StringField(_l('Rechercher'), validators=[DataRequired(), Length(max=200)])
    submit = SubmitField(_l('Rechercher'))
