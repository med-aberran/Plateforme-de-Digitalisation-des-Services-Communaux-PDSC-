# PDSC — Plateforme de Digitalisation des Services Communaux

Plateforme web bilingue (Français / العربية) permettant à une commune
territoriale marocaine de digitaliser ses services : dépôt et suivi de
demandes administratives, rendez-vous, réclamations, actualités, documents
publics, et administration complète depuis un tableau de bord.

Construite avec **Flask**, dans une architecture volontairement simple :
un seul fichier par responsabilité (`models.py`, `forms.py`, `routes.py`,
`utils.py`), un seul CSS, un seul JS, aucun Blueprint.

---

## 1. Stack technique

| Domaine | Technologie |
|---|---|
| Backend | Python 3.11+, Flask 3 |
| ORM / migrations | Flask-SQLAlchemy, Flask-Migrate (Alembic) |
| Authentification | Flask-Login, Werkzeug (hash des mots de passe) |
| Formulaires | Flask-WTF (protection CSRF incluse) |
| E-mail | Flask-Mail |
| Internationalisation | Flask-Babel (fr / ar, RTL automatique) |
| API | Flask-JWT-Extended |
| Documents | ReportLab (PDF), OpenPyXL (Excel), qrcode (QR codes) |
| Base de données | PostgreSQL |
| Frontend | HTML5, CSS3, JavaScript ES6, Bootstrap 5 (CDN) |

Aucun framework frontend (React/Vue/Angular) n'est utilisé.

---

## 2. Structure du projet

```text
pdsc/
├── app.py            # Création de l'app, extensions, contexte global, erreurs, CLI
├── models.py          # Tous les modèles SQLAlchemy (20 tables)
├── forms.py            # Tous les formulaires Flask-WTF
├── routes.py           # Toutes les routes (site public, auth, dashboards, API)
├── utils.py            # Fonctions utilitaires (upload, PDF, Excel, QR, e-mail…)
├── config.py            # Configuration (dev / prod / test)
├── run.py                # Point d'entrée du serveur de développement
├── babel.cfg              # Configuration d'extraction des traductions
├── requirements.txt
├── templates/              # 17 templates + base.html
├── static/
│   ├── css/style.css         # Feuille de style unique
│   ├── js/script.js           # Script unique
│   └── uploads/                 # Fichiers déposés par les utilisateurs
├── translations/
│   ├── fr/LC_MESSAGES/            # Catalogue français (source)
│   └── ar/LC_MESSAGES/             # Catalogue arabe (traduit et compilé)
└── migrations/                       # Généré par Flask-Migrate
```

### Approche bilingue

Deux mécanismes complémentaires assurent la bilinguisme complet du site :

1. **Contenu dynamique** (services, actualités, documents…) : chaque table
   possède des colonnes `*_fr` / `*_ar` dédiées, remplies depuis le tableau
   de bord administrateur.
2. **Texte d'interface statique** (menus, boutons, titres) : la majorité est
   gérée directement dans les templates via une sélection conditionnelle
   selon `current_lang`. Les **libellés de formulaires** et les **messages
   flash / notifications** générés côté serveur utilisent Flask-Babel
   (`gettext` / `lazy_gettext`) avec un catalogue déjà extrait, traduit et
   compilé dans `translations/`. Pour ajouter de nouvelles chaînes après
   modification du code, régénérez le catalogue (section 6).

Le passage en arabe active automatiquement l'affichage RTL (`dir="rtl"`),
la police Tajawal et la feuille Bootstrap RTL.

---

## 3. Installation

### 3.1 Prérequis

- Python 3.11 ou supérieur
- PostgreSQL 13 ou supérieur
- pip / venv

### 3.2 Étapes

```bash
# 1. Cloner / copier le projet puis se placer dedans
cd pdsc

# 2. Créer et activer un environnement virtuel
python3 -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Copier le fichier d'environnement et le personnaliser
cp .env.example .env
# → renseignez SECRET_KEY, DATABASE_URL, les identifiants SMTP, etc.

# 5. Créer la base de données PostgreSQL
createdb pdsc_db
# ou, depuis psql :
#   CREATE DATABASE pdsc_db;
#   CREATE USER pdsc_user WITH PASSWORD 'pdsc_password';
#   GRANT ALL PRIVILEGES ON DATABASE pdsc_db TO pdsc_user;

# 6. Initialiser les migrations et créer les tables
flask db init          # une seule fois
flask db migrate -m "Initial schema"
flask db upgrade

# 7. Initialiser les données de base (rôles, compte admin, services)
flask seed-db
# → crée le compte administrateur : admin@commune.ma / Admin@2026
#   (à changer immédiatement en production)

# 8. Lancer le serveur de développement
python run.py
# → http://127.0.0.1:5000
```

---

## 3bis. Mise à jour depuis une version précédente du projet

Si vous remplacez les fichiers d'un projet déjà installé (nouvelle livraison),
la base de données existante ne connaît pas encore les nouvelles colonnes
(ex. `service_id` et `reference` sur `public_documents`). Après avoir copié
les nouveaux fichiers dans votre dossier `pdsc/` :

```bash
flask db migrate -m "Ajout service_id et reference sur public_documents"
flask db upgrade
```

Vos données existantes (utilisateurs, demandes…) sont conservées ; seule la
structure des tables est mise à jour.

---

## 4. Comptes et rôles

| Rôle | Description |
|---|---|
| **Administrateur** | Gère utilisateurs, départements, services, contenus, paramètres |
| **Employé** | Traite les demandes, rendez-vous et réclamations de son département |
| **Citoyen** | Dépose des demandes, prend rendez-vous, suit ses démarches |
| **Visiteur** | Consultation publique (non connecté) |

Le compte administrateur par défaut (créé par `flask seed-db`) :

```
Email     : admin@commune.ma
Mot de passe : Admin@2026
```

Pour créer des employés, utilisez le tableau de bord administrateur
(onglet **Utilisateurs**), en sélectionnant le rôle *Employé* et un
département de rattachement.

---

## 5. Fonctionnalités principales

- **Site public** : présentation, services (avec documents liés), actualités,
  page dédiée **Documents publics** (`/documents`) avec recherche par titre,
  référence, service et catégorie, galerie, vidéos, plan d'aménagement
  (visionneuse PDF avec zoom / impression / plein écran / téléchargement),
  carte Google Maps, formulaire de contact, recherche globale, suivi de
  demande par numéro ou QR code (sans connexion).
- **Citoyen** : inscription, vérification e-mail, dépôt de demandes
  multi-documents, suivi avec historique et commentaires, rendez-vous,
  réclamations, notifications, profil, mot de passe oublié.
- **Employé** : traitement des demandes (changement de statut, commentaires,
  affectation), génération de récépissés PDF avec QR code, export Excel,
  gestion des rendez-vous et réclamations.
- **Administrateur** : gestion complète des utilisateurs, départements,
  services, actualités, **documents publics (ajout, modification, suppression,
  rattachement à un service, référence, recherche instantanée dans le
  tableau)**, plan d'aménagement, galerie, vidéos, paramètres du site,
  journal d'audit (Logs).
- **Sécurité** : hachage Werkzeug, protection CSRF (Flask-WTF), contrôle
  d'accès par rôle (décorateurs `admin_required` / `employee_required` /
  `citizen_required`), validation des types de fichiers uploadés,
  journalisation des actions sensibles.
- **API JWT** (`/api/login`, `/api/mes-demandes`, `/api/suivi/<numero>`) :
  point d'entrée pour une éventuelle application mobile ou intégration
  tierce.

---

## 6. Traductions (Flask-Babel)

Après toute modification de texte traduisible (nouveau `_l()` / `_()`,
nouveau champ de formulaire) :

```bash
pybabel extract -F babel.cfg -k _l -k _ -o messages.pot .
pybabel update -i messages.pot -d translations
# → éditez translations/ar/LC_MESSAGES/messages.po pour traduire les
#   nouvelles chaînes (repérables par un msgstr vide ou "fuzzy")
pybabel compile -d translations
```

---

## 7. Déploiement en production

- Définir `FLASK_ENV=production` et un `SECRET_KEY` / `JWT_SECRET_KEY`
  robustes et uniques.
- Servir l'application via un serveur WSGI (ex. Gunicorn) derrière un
  reverse proxy (Nginx) :
  ```bash
  gunicorn -w 4 -b 0.0.0.0:8000 run:app
  ```
- Activer HTTPS et les cookies sécurisés (`SESSION_COOKIE_SECURE`, déjà
  activé dans `ProductionConfig`).
- Configurer des sauvegardes régulières de PostgreSQL (`pg_dump`).
- Restreindre `MAX_CONTENT_LENGTH` et les extensions autorisées si
  nécessaire (`config.py`).

---

## 8. Notes de développement

- Le projet suit PEP8 et privilégie la lisibilité à la fragmentation :
  chaque type de fichier (modèles, formulaires, routes, utilitaires) est
  centralisé dans un unique module.
- Le tableau de bord administrateur est une page unique à onglets
  (Bootstrap `nav-tabs`) plutôt que des pages séparées par entité, afin de
  respecter la contrainte de minimisation des fichiers.
- Les statuts (demandes, rendez-vous, réclamations) sont définis une seule
  fois, de façon bilingue, dans `models.py` (`REQUEST_STATUSES`,
  `APPOINTMENT_STATUSES`, `COMPLAINT_STATUSES`) et réutilisés partout
  (formulaires, templates, badges).
- En développement (`FLASK_ENV=development`), les liens de vérification
  d'e-mail et de réinitialisation de mot de passe sont aussi affichés dans
  un message flash, pour tester sans configurer de serveur SMTP.
