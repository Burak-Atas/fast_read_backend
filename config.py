"""Application configuration loaded from environment variables.

Values come from the process environment; a local .env file is loaded as a
fallback (it never overrides variables that are already set). Missing
required settings raise at import time so the app fails loudly at startup.
"""
import os

from dotenv import load_dotenv

load_dotenv()

REQUIRED_KEYS = (
    "DATABASE_URL",
    "DATABASE_NAME",
    "SECRET_KEY",
    "EMAIL_SENDER",
    "EMAIL_PASSWORD",
    "CONTACT_EMAIL",
    "CORS_ORIGINS",
)


def _get(key, default=None):
    value = os.environ.get(key, default)
    if isinstance(value, str):
        value = value.strip()
    return value


_missing = [key for key in REQUIRED_KEYS if not _get(key)]
if _missing:
    # Only key names are reported, never values.
    raise RuntimeError(
        "Missing required environment variables: " + ", ".join(_missing)
    )

DATABASE_URL = _get("DATABASE_URL")
DATABASE_NAME = _get("DATABASE_NAME")
SECRET_KEY = _get("SECRET_KEY")
EMAIL_SENDER = _get("EMAIL_SENDER")
EMAIL_PASSWORD = _get("EMAIL_PASSWORD")
CONTACT_EMAIL = _get("CONTACT_EMAIL")
CORS_ORIGINS = [o.strip() for o in _get("CORS_ORIGINS").split(",") if o.strip()]

# Public base URL used to build uploaded video URLs (optional).
SERVER_IP = _get("SERVER_IP")

DEBUG = (_get("FLASK_DEBUG", "false") or "").lower() in ("1", "true", "yes", "on")
HOST = _get("HOST", "127.0.0.1")
PORT = int(_get("PORT", "5000"))
