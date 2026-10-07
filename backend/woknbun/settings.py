"""
Django settings for the Wok & Bun ordering site backend.
"""
import os
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Reads backend/.env (if present) so DB_* settings work from any terminal,
# VS Code's run button, or a double-clicked script. Real environment
# variables always win over the file.
load_dotenv(BASE_DIR / ".env")


def _env_list(name):
    return [v.strip() for v in os.environ.get(name, "").split(",") if v.strip()]


# ---- Security --------------------------------------------------------------
# Defaults keep today's behaviour (development). For the live site put these in
# backend/.env:   DJANGO_DEBUG=0   DJANGO_SECRET_KEY=<long random string>
#                 CORS_ALLOWED_ORIGINS=https://www.woknbun.com,https://woknbun.com
_DEV_SECRET = "dev-secret-key-change-me-in-production"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", _DEV_SECRET)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

if not DEBUG and SECRET_KEY == _DEV_SECRET:
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY in .env when DJANGO_DEBUG=0.")

ALLOWED_HOSTS = ["www.woknbun.com", "woknbun.com", "localhost", "127.0.0.1"] + _env_list("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "menu",
    "orders",
    "accounts",
    "pos",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "woknbun.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "woknbun.wsgi.application"

# PostgreSQL when DB_NAME is set (see .env.example); otherwise the old
# SQLite file, so nothing breaks on a machine that isn't configured yet.
if os.environ.get("DB_NAME"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["DB_NAME"],
            "USER": os.environ.get("DB_USER", "postgres"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
    print(
        f"[settings] Database: PostgreSQL '{DATABASES['default']['NAME']}' "
        f"on {DATABASES['default']['HOST']}:{DATABASES['default']['PORT']}",
        file=sys.stderr,
    )
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
    print("[settings] Database: SQLite fallback (DB_NAME is not set)", file=sys.stderr)


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Karachi"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Local development: any origin may call the API. With DJANGO_DEBUG=0 only the
# origins listed in CORS_ALLOWED_ORIGINS may (the POS terminal is not a browser,
# so it is not affected by CORS).
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = _env_list("CORS_ALLOWED_ORIGINS")

# JWT access tokens default to 5 minutes in simplejwt - far too short for a
# cashier's shift. 30 minutes is a saner default; JWT_ACCESS_SECONDS lets
# this be forced short for testing the auto-refresh behavior.
_jwt_access_seconds = os.environ.get("JWT_ACCESS_SECONDS")
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(seconds=int(_jwt_access_seconds)) if _jwt_access_seconds else timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

REST_FRAMEWORK = {
    # Secure by default: every endpoint needs a login unless it says otherwise.
    # (The public ones - menu, website checkout, customer sign-in - opt in.)
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Limits per visitor (IP address). Both scopes MUST exist or those endpoints
    # return a 500. These are generous for testing - for the live site set
    # THROTTLE_ORDER_CREATE=20/hour and THROTTLE_CUSTOMER_AUTH=30/hour in .env.
    "DEFAULT_THROTTLE_RATES": {
        "order_create": os.environ.get("THROTTLE_ORDER_CREATE", "10/minute"),
        "customer_auth": os.environ.get("THROTTLE_CUSTOMER_AUTH", "20/minute"),
    },
}

# ---- Business rules (the server is the source of truth for these) ----------
TAX_RATE = Decimal("0.16")
DELIVERY_CHARGES = Decimal("250.00")
POS_REFUND_ROLES = ("manager", "admin")  # who may refund a settled order

# Fast password hashing so the test suite doesn't spend its time in PBKDF2.
if "test" in sys.argv:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]