from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# ──────────────────────────────────────────────
# Security
# ──────────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
#ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*', cast=Csv())
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# ──────────────────────────────────────────────
# Applications
# ──────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'admin_panel',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'shop_admin.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'shop_admin.wsgi.application'

# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='shop_admin_db'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# ──────────────────────────────────────────────
# Password validation
# ──────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ──────────────────────────────────────────────
# Internationalization
# ──────────────────────────────────────────────
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# ──────────────────────────────────────────────
# Cache
# ──────────────────────────────────────────────
# Используется фильтром TopPublisherFilter (admin.py), чтобы не считать
# агрегат по 726 тыс. строк на каждый рендер сайдбара админки.
# Кэш локальный для процесса: у каждого воркера gunicorn свой, поэтому список
# издательств пересчитывается не чаще раза в CACHE_TTL на воркер.
# Для перехода на Redis достаточно поменять BACKEND и LOCATION — код не меняется.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'ready-admin-cache',
        'TIMEOUT': 300,
    }
}

# ──────────────────────────────────────────────
# Static & Media
# ──────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_BASE_URL = config('MEDIA_BASE_URL', default=MEDIA_URL)

# ──────────────────────────────────────────────
# Yandex Object Storage (S3-совместимый) — фото книг
# ──────────────────────────────────────────────
# Бакет в Яндекс Облаке: анонимное чтение объектов разрешено (требование Ozon),
# запись — только по статическим ключам сервисного аккаунта.
# Пока PHOTO_S3_ENABLED=False, фото сохраняются локально, как раньше.
# Ключи читаются только из .env: в репозитории их быть не должно.
PHOTO_S3_ENABLED = config('PHOTO_S3_ENABLED', default=False, cast=bool)
YC_S3_BUCKET = config('YC_S3_BUCKET', default='')
YC_S3_ACCESS_KEY = config('YC_S3_ACCESS_KEY', default='')
YC_S3_SECRET_KEY = config('YC_S3_SECRET_KEY', default='')
# Эндпоинт S3 API Яндекс Облака (не путать с публичным URL бакета).
YC_S3_ENDPOINT = config('YC_S3_ENDPOINT', default='https://storage.yandexcloud.net')
YC_S3_REGION = config('YC_S3_REGION', default='ru-central1')
# База для публичных ссылок вида https://<bucket>.storage.yandexcloud.net/<key>.
# Вынесена в настройку, чтобы при смене бакета/эндпоинта править только .env.
YC_S3_PUBLIC_BASE_URL = config(
    'YC_S3_PUBLIC_BASE_URL',
    default=f'{YC_S3_ENDPOINT}/{YC_S3_BUCKET}' if YC_S3_BUCKET else '',
)
# Таймаут одного запроса и число повторов — сеть до облака не должна вешать админку.
YC_S3_TIMEOUT = config('YC_S3_TIMEOUT', default=15, cast=int)
YC_S3_MAX_ATTEMPTS = config('YC_S3_MAX_ATTEMPTS', default=3, cast=int)

# ──────────────────────────────────────────────
# Ozon (закомментировано — интеграция с Ozon Seller API отключена)
# ──────────────────────────────────────────────
# OZON_SHOP_ID = config('OZON_SHOP_ID', default='')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
