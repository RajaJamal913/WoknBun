"""
Django settings for the Wok & Bun ordering site backend.
"""
from pathlib import Path
import os
import sys

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Reads backend/.env (if present) so DB_* settings work from any terminal,
# VS Code's run button, or a double-clicked script. Real environment
# variables always win over the file.
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = "dev-secret-key-change-me-in-production"

DEBUG = True

ALLOWED_HOSTS = ["*"]

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

# Allow the Next.js dev server (and any origin, for local dev) to call the API.
CORS_ALLOW_ALL_ORIGINS = True

from datetime import timedelta

# JWT access tokens default to 5 minutes in simplejwt - far too short for a
# cashier's shift. 30 minutes is a saner default; JWT_ACCESS_SECONDS lets
# this be forced short for testing the auto-refresh behavior.
_jwt_access_seconds = os.environ.get("JWT_ACCESS_SECONDS")
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(seconds=int(_jwt_access_seconds)) if _jwt_access_seconds else timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
}
from decimal import Decimal

TAX_RATE = Decimal("0.16")
DELIVERY_CHARGES = Decimal("250.00")
POS_REFUND_ROLES = ("manager", "admin")