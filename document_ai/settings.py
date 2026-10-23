import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
DATA_DIR = Path(os.environ.get('DOCUMENT_AI_DATA_DIR', str(BASE_DIR / '.data'))).expanduser().resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
_secret_path = DATA_DIR / '.secret_key'
if not os.environ.get('DJANGO_SECRET_KEY') and not _secret_path.exists():
    try:
        with open(_secret_path, 'x', opener=lambda path, flags: os.open(path, flags, 0o600)) as stream:
            stream.write(secrets.token_urlsafe(48))
    except FileExistsError:
        pass
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY') or _secret_path.read_text().strip()
DEBUG = os.environ.get('DJANGO_DEBUG', '0').lower() in {'1', 'true', 'yes'}
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1]').split(',')
INSTALLED_APPS = ['django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'documents']
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'documents.middleware.LocalOnlyMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'document_ai.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'document_ai.wsgi.application'
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': DATA_DIR / 'db.sqlite3', 'OPTIONS': {'timeout': 20}}}
LANGUAGE_CODE = 'it-it'
TIME_ZONE = 'Europe/Rome'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / '.static'
MEDIA_ROOT = DATA_DIR / 'originals'
FILE_UPLOAD_PERMISSIONS = 0o600
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o700
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_SAMESITE = 'Strict'
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
DOCUMENT_AI_MAX_UPLOAD_MB = int(os.environ.get('DOCUMENT_AI_MAX_UPLOAD_MB', '20'))
DOCUMENT_AI_ENDPOINT = os.environ.get('DOCUMENT_AI_ENDPOINT', 'http://127.0.0.1:8081/v1')
DOCUMENT_AI_MODEL = os.environ.get('DOCUMENT_AI_MODEL', 'local')
DOCUMENT_AI_TIMEOUT = int(os.environ.get('DOCUMENT_AI_TIMEOUT', '180'))
DOCUMENT_AI_CONTEXT_CHARS = int(os.environ.get('DOCUMENT_AI_CONTEXT_CHARS', '6500'))
DOCUMENT_AI_MAX_TOKENS = int(os.environ.get('DOCUMENT_AI_MAX_TOKENS', '1200'))
DOCUMENT_AI_OCR_LANGUAGE = os.environ.get('DOCUMENT_AI_OCR_LANGUAGE', 'ita+eng')
DOCUMENT_AI_MAX_PAGES = int(os.environ.get('DOCUMENT_AI_MAX_PAGES', '50'))
DOCUMENT_AI_MAX_CHARS = int(os.environ.get('DOCUMENT_AI_MAX_CHARS', '250000'))
