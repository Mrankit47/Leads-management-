"""
Django settings for leadgen project.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-leadgen-dev-key-change-in-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'leads.apps.LeadsConfig',
    'subscriptions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'leads.middleware.LogoutSecurityMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'subscriptions.middleware.SubscriptionMiddleware',
]

ROOT_URLCONF = 'leadgen.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'leadgen.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login URLs
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Subject filter for emails that should become leads/tickets
# Used by the Gmail IMAP reader
# Any of these keywords (case-insensitive) appearing in the subject will be treated as an inquiry.
EMAIL_SUBJECT_FILTER = ['inquiry', 'enquiry']  # Emails must contain one of these words in subject

# Gmail IMAP Configuration (for reading inquiry emails from Gmail inbox)
GMAIL_IMAP_HOST = 'imap.gmail.com'
GMAIL_IMAP_PORT = 993
GMAIL_EMAIL = 'eic.developer.testing@gmail.com'  # Your Gmail address
# IMPORTANT: Set GMAIL_APP_PASSWORD in your environment for security:
#   export GMAIL_APP_PASSWORD='your-app-password-here'
# For production you should use the env var version; here it's hard-coded for development only.
# GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD', '')
GMAIL_APP_PASSWORD = 'tyoxjiqcigxjbiut'

# Outgoing email via Gmail SMTP
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = GMAIL_EMAIL
EMAIL_HOST_PASSWORD = GMAIL_APP_PASSWORD
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = GMAIL_EMAIL

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'leads.views': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# Session Security Configuration
# Auto-logout after 30 minutes of inactivity (1800 seconds)
SESSION_COOKIE_AGE =1800
# Auto-logout when the browser is closed
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
