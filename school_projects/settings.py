"""
Django settings for school_projects project.
"""

from pathlib import Path
import os

import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-j&dd%7n6_&9*cn-*68^4x1d)ri$*6^u&$z771g27351j#4eerw",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = _env_bool("DEBUG", default=True)

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    ".onrender.com",
    ".ngrok-free.dev",
    ".ngrok.io",
    ".ngrok.app",
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

_extra_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
if _extra_hosts:
    ALLOWED_HOSTS.extend(h.strip() for h in _extra_hosts.split(",") if h.strip())

_extra_csrf = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
if _extra_csrf:
    CSRF_TRUSTED_ORIGINS.extend(o.strip() for o in _extra_csrf.split(",") if o.strip())

_primary_domain = os.environ.get("PRIMARY_DOMAIN", "").strip().lower()
if _primary_domain:
    _domain_hosts = {_primary_domain}
    if _primary_domain.startswith("www."):
        _domain_hosts.add(_primary_domain[4:])
    else:
        _domain_hosts.add(f"www.{_primary_domain}")
    for host in _domain_hosts:
        if host and host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)
        origin = f"https://{host}"
        if origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin)

_ngrok_origin = os.environ.get("NGROK_ORIGIN", "").strip()
if _ngrok_origin:
    CSRF_TRUSTED_ORIGINS.append(_ngrok_origin)
    host = _ngrok_origin.replace("https://", "").replace("http://", "").split("/")[0]
    if host and host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)

_render_external = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if _render_external:
    if _render_external not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_render_external)
    origin = f"https://{_render_external}"
    if origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)

# Authentication redirects
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

# When True, only platform superadmins can sign in; other users are signed out.
MAINTENANCE_MODE = _env_bool("MAINTENANCE_MODE", default=False)
MAINTENANCE_MESSAGE = os.environ.get(
    "MAINTENANCE_MESSAGE",
    "The system is temporarily unavailable while updates are applied. Please try again later.",
)


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.ActiveMembershipMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.MaintenanceMiddleware",
    "core.middleware.SchoolApprovalMiddleware",
    "core.middleware.MustChangePasswordMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "core.auth_backend.SchoolScopedBackend",
    "core.auth_backend.ModelBackend",
]

ROOT_URLCONF = "school_projects.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.navigation",
            ],
        },
    },
]

WSGI_APPLICATION = "school_projects.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
# Local default: SQLite. On Render: set DATABASE_URL to Postgres.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

if os.environ.get("DATABASE_URL"):
    DATABASES["default"] = dj_database_url.config(
        default=os.environ["DATABASE_URL"],
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=True,
    )


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ],
}


# Static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Media uploads (logos, evidence photos). On free Render these reset on redeploy
# unless you attach a persistent disk mounted at /var/data and set MEDIA_ROOT.
MEDIA_URL = "/media/"
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", str(BASE_DIR / "media"))

# Email (password reset)
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = os.environ.get(
    "DJANGO_DEFAULT_FROM_EMAIL",
    "ProjectTrack UG <noreply@projecttrack.local>",
)
EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("DJANGO_EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("DJANGO_EMAIL_USE_TLS", "true").lower() in ("1", "true", "yes")

# Production security (enabled when DEBUG is false)
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = _env_bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
