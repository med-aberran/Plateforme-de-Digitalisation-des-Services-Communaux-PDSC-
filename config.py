# -*- coding: utf-8 -*-
"""
config.py
=========
Configuration centralisée de l'application PDSC.
Les informations sensibles doivent être fournies
via des variables d'environnement.
"""

import os
from datetime import timedelta


BASE_DIR = os.path.abspath(os.path.dirname(__file__))


# ============================================================
# .env - développement local
# ============================================================

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, '.env'))
except ImportError:
    pass


class Config:
    """Configuration commune à tous les environnements."""

    # ========================================================
    # Sécurité
    # ========================================================

    SECRET_KEY = os.environ.get(
        'SECRET_KEY',
        'change-this-secret-key-in-production'
    )

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

    # ========================================================
    # PostgreSQL
    # ========================================================

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql://pdsc_user:pdsc_password@localhost:5432/pdsc_db'
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True
    }

    # ========================================================
    # Internationalisation
    # ========================================================

    LANGUAGES = ['fr', 'ar']

    BABEL_DEFAULT_LOCALE = 'fr'

    BABEL_DEFAULT_TIMEZONE = 'Africa/Casablanca'

    BABEL_TRANSLATION_DIRECTORIES = os.path.join(
        BASE_DIR,
        'translations'
    )

    # ========================================================
    # Upload de fichiers
    # ========================================================

    # Utilisé principalement en développement local.
    # En production Vercel, utiliser Supabase Storage.
    UPLOAD_FOLDER = os.path.join(
        BASE_DIR,
        'static',
        'uploads'
    )

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 Mo

    ALLOWED_DOCUMENT_EXTENSIONS = {
        'pdf',
        'doc',
        'docx',
        'jpg',
        'jpeg',
        'png'
    }

    ALLOWED_IMAGE_EXTENSIONS = {
        'jpg',
        'jpeg',
        'png',
        'gif',
        'webp'
    }

    # ========================================================
    # Flask-Mail
    # ========================================================

    MAIL_SERVER = os.environ.get(
        'MAIL_SERVER',
        'smtp.gmail.com'
    )

    MAIL_PORT = int(
        os.environ.get('MAIL_PORT', 587)
    )

    MAIL_USE_TLS = (
        os.environ.get(
            'MAIL_USE_TLS',
            'true'
        ).lower() == 'true'
    )

    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')

    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    MAIL_DEFAULT_SENDER = os.environ.get(
        'MAIL_DEFAULT_SENDER',
        'contact@commune.ma'
    )

    # ========================================================
    # JWT
    # ========================================================

    JWT_SECRET_KEY = os.environ.get(
        'JWT_SECRET_KEY',
        'change-this-jwt-secret-in-production'
    )

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)

    JWT_TOKEN_LOCATION = ['headers']

    # ========================================================
    # Application
    # ========================================================

    ITEMS_PER_PAGE = 10

    COMMUNE_NAME_FR = os.environ.get(
        'COMMUNE_NAME_FR',
        'Commune de Zinat'
    )

    COMMUNE_NAME_AR = os.environ.get(
        'COMMUNE_NAME_AR',
        'جماعة زينات'
    )

    SECURITY_PASSWORD_SALT = os.environ.get(
        'SECURITY_PASSWORD_SALT',
        'change-this-salt'
    )


# ============================================================
# Développement
# ============================================================

class DevelopmentConfig(Config):

    DEBUG = True

    SQLALCHEMY_ECHO = False


# ============================================================
# Production - Vercel
# ============================================================

class ProductionConfig(Config):

    DEBUG = False

    SESSION_COOKIE_SECURE = True

    REMEMBER_COOKIE_SECURE = True

    SESSION_COOKIE_HTTPONLY = True


# ============================================================
# Tests
# ============================================================

class TestingConfig(Config):

    TESTING = True

    WTF_CSRF_ENABLED = False

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'TEST_DATABASE_URL',
        'postgresql://pdsc_user:pdsc_password@localhost:5432/pdsc_test_db'
    )


# ============================================================
# Configuration selon l'environnement
# ============================================================

config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': ProductionConfig,
}


def get_config():
    """
    Retourne la configuration correspondant à l'environnement.
    Production est utilisée par défaut pour Vercel.
    """

    env = os.environ.get(
        'FLASK_ENV',
        'production'
    )

    return config_by_name.get(
        env,
        ProductionConfig
    )