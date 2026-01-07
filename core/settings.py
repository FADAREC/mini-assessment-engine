import sys
import os
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))


# ==============================================
# SECURITY SETTINGS
# ==============================================
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())


# ==============================================
# APPLICATION DEFINITION
# ==============================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',
    'drf_spectacular',
    
    # Local apps
    'apps.assessments',
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

ROOT_URLCONF = 'core.urls'

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

WSGI_APPLICATION = 'core.wsgi.application'


# ==============================================
# DATABASE CONFIGURATION
# ==============================================
# I've made this flexible - supports MySQL, PostgreSQL and SQLite
DB_ENGINE = config('DB_ENGINE', default='django.db.backends.sqlite3')

    # PostgreSQL configuration
if DB_ENGINE == 'django.db.backends.postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='assessment_db'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }
elif DB_ENGINE == 'django.db.backends.mysql':
    # MySQL configuration (alternative)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME', default='assessment_db'),
            'USER': config('DB_USER', default='root'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='3306'),
        }
    }
else:
    # SQLite configuration
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / config('DB_NAME', default='db.sqlite3'),
        }
    }


# ==============================================
# PASSWORD VALIDATION
# ==============================================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# ==============================================
# AUTHENTICATION & AUTHORIZATION
# ==============================================
# I'm using a custom User model to allow future extensions
AUTH_USER_MODEL = 'assessments.User'

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}


# ==============================================
# API DOCUMENTATION (Swagger/OpenAPI)
# ==============================================
SPECTACULAR_SETTINGS = {
    'TITLE': 'Assessment Engine API',
    'DESCRIPTION': '''
    RESTful API for secure exam submission and automated grading.
    
    **Features:**
    - Token-based authentication
    - UUID-based IDs for security
    - Automated grading with both algorithmic and AI-powered options
    - Query-optimized endpoints
    - Comprehensive error handling
    
    **Authentication:**
    1. Register at `/api/auth/register/` or login at `/api/auth/login/`
    2. Include the token in all requests: `Authorization: Token <your-token>`
    
    **Quick Start:**
    1. Register/Login → Get token
    2. List exams → Choose one
    3. Get exam details → See questions
    4. Submit answers → Get graded
    5. View results → See detailed feedback
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/',
    'TAGS': [
        {'name': 'Authentication', 'description': 'User registration and login'},
        {'name': 'Exams', 'description': 'Browse and view available exams'},
        {'name': 'Submissions', 'description': 'Submit answers and view results'},
    ],
}


# ==============================================
# GRADING SERVICE CONFIGURATION
# ==============================================
# Switch between 'mock' (algorithmic) and 'gemini' (AI-powered)
GRADER_TYPE = config('GRADER_TYPE', default='mock')
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')


# ==============================================
# INTERNATIONALIZATION
# ==============================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ==============================================
# STATIC FILES (CSS, JavaScript, Images)
# ==============================================
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'


# ==============================================
# DEFAULT PRIMARY KEY FIELD TYPE
# ==============================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ==============================================
# PRODUCTION SECURITY SETTINGS
# ==============================================
# These are automatically enabled when DEBUG=False
if not DEBUG:
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'


# ==============================================
# LOGGING CONFIGURATION
# ==============================================
# I've set up basic logging for debugging and error tracking
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': config('DJANGO_LOG_LEVEL', default='INFO'),
        },
        'apps.assessments': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)


# ==============================================
# DEVELOPMENT TOOLS
# ==============================================
if DEBUG and config('ENABLE_DEBUG_TOOLBAR', default=False, cast=bool):
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1', 'localhost']