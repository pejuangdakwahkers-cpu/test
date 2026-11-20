"""
Pengaturan Django untuk proyek Absensi RFID Sekolah.
"""

import os
from pathlib import Path

# Direktori dasar proyek
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY: Ganti secret key ini di production!
SECRET_KEY = 'django-insecure-ganti-ini-di-production-absensi-rfid-2024'

# Mode debug — matikan di production
DEBUG = True

ALLOWED_HOSTS = ['*']

# CSRF Trusted Origins untuk Hugging Face Spaces & localhost
CSRF_TRUSTED_ORIGINS = [
    'https://*.hf.space',
    'https://*.huggingface.co',
    'http://localhost:7860',
    'http://127.0.0.1:7860',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# ============================================================
# Aplikasi terinstal
# ============================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    # Aplikasi lokal
    'absensi',
]

# ============================================================
# Middleware
# ============================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'absensi_project.urls'

# ============================================================
# Template
# ============================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'absensi_project.wsgi.application'

# ============================================================
# Database — SQLite default, ganti PostgreSQL di production
# ============================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ============================================================
# Validasi password
# ============================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ============================================================
# Internasionalisasi
# ============================================================
LANGUAGE_CODE = 'id'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ============================================================
# File statis
# ============================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
# Penyimpanan file statis dengan kompresi untuk production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ============================================================
# Default primary key
# ============================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================
# Autentikasi — URL login/redirect
# ============================================================
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'

# ============================================================
# Django REST Framework
# ============================================================
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
}
