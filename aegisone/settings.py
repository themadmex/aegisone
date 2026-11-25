"""Django settings for AegisOne Open.

Configuration comes from environment variables only. Development defaults apply
when DJANGO_DEBUG=1; production refuses to start without required secrets.
"""

import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise ImproperlyConfigured(f"Environment variable {name} is required")
    return value


def env_bool(name, default=False):
    return env(name, "1" if default else "0").strip().lower() in {"1", "true", "yes", "on"}


DEBUG = env_bool("DJANGO_DEBUG", False)

SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-insecure-key" if DEBUG else None, required=not DEBUG)
ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]
APP_BASE_URL = env("APP_BASE_URL", "http://localhost:8000").rstrip("/")
DNS_CHECKS_ENABLED = env_bool("DNS_CHECKS_ENABLED")
DNS_PUBLIC_RESOLVER = env("DNS_PUBLIC_RESOLVER", "1.1.1.1")
PUBLIC_LANDING_ENABLED = env_bool("PUBLIC_LANDING_ENABLED")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "apps.core",
    "apps.accounts",
    "apps.workspaces",
    "apps.posture",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "apps.core.middleware.SessionPolicyMiddleware",
    "apps.core.middleware.SecurityHeadersMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "aegisone.urls"
WSGI_APPLICATION = "aegisone.wsgi.application"

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
            ],
        },
    },
]

# --- Database -----------------------------------------------------------------
# The runtime connects as a role that owns nothing and cannot bypass row-level
# security. Migrations run with DJANGO_DB_ROLE=owner, which switches to the
# schema-owning role. Every request runs in one transaction so tenant context
# set with SET LOCAL never leaks between pooled connections.
_use_owner = env("DJANGO_DB_ROLE", "app") == "owner"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": env("DB_HOST", "127.0.0.1"),
        # 55432 is the local Compose port, chosen so it won't clash with other
        # PostgreSQL servers on a developer machine. Containers and CI set DB_PORT.
        "PORT": env("DB_PORT", "55432"),
        "NAME": env("DB_NAME", "aegisone"),
        "USER": env("DB_OWNER_USER", "aegis_owner") if _use_owner else env("DB_USER", "aegis_app"),
        "PASSWORD": (
            env("DB_OWNER_PASSWORD", "aegis_owner_dev" if DEBUG else None)
            if _use_owner
            else env("DB_PASSWORD", "aegis_app_dev" if DEBUG else None)
        ),
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": int(env("DB_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {"sslmode": env("DB_SSLMODE", "prefer"), "connect_timeout": 5},
    }
}
DB_APP_ROLE = env("DB_APP_ROLE", "aegis_app")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Identity -----------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:sign_in"
LOGIN_REDIRECT_URL = "workspaces:overview"
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Access lifetimes from the TRD (conservative pilot defaults).
INVITATION_LIFETIME = timedelta(hours=48)
RECOVERY_LIFETIME = timedelta(minutes=30)
SESSION_ABSOLUTE_LIFETIME = timedelta(hours=12)

SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = int(SESSION_ABSOLUTE_LIFETIME.total_seconds())
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_NAME = "__Host-aegis_session" if not DEBUG else "aegis_session"
CSRF_COOKIE_NAME = "__Host-aegis_csrf" if not DEBUG else "aegis_csrf"

OTP_TOTP_ISSUER = "AegisOne Open"

# Rate limiting needs a cache shared by every web process. The pilot runs a
# single web process; set CACHE_URL-style config before scaling out.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
RATELIMIT_USE_CACHE = "default"
RATELIMIT_VIEW = "apps.core.views.rate_limited"

# --- Transport and headers ----------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if env_bool("DJANGO_BEHIND_TLS_PROXY") else None
SECURE_SSL_REDIRECT = not DEBUG and env_bool("DJANGO_SSL_REDIRECT", True)
SECURE_HSTS_SECONDS = 0 if DEBUG else int(env("DJANGO_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = False
# Preload is a hard-to-reverse, domain-wide commitment; decide it at launch with
# the final domain rather than in code.
SILENCED_SYSTEM_CHECKS = ["security.W021"]
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# --- Email --------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "localhost")
EMAIL_PORT = int(env("EMAIL_PORT", "25"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS")
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL")
EMAIL_TIMEOUT = float(env("EMAIL_TIMEOUT", "10"))
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "AegisOne Open <no-reply@localhost>")

# --- Static files -------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"redact_account_links": {"()": "apps.core.logging.RedactAccountLinks"}},
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {
        "class": "logging.StreamHandler", "formatter": "plain", "filters": ["redact_account_links"],
    }},
    "loggers": {
        "django": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO"), "propagate": False},
        "django.server": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}
