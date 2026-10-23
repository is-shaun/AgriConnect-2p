"""Application configuration, read from environment variables (see .env.example)."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    APP_ENV = os.getenv("APP_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

    # MySQL, e.g. mysql+pymysql://agri_user:password@localhost:3306/agriconnect?charset=utf8mb4
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    # Authentication: JWT in HttpOnly cookies + double-submit CSRF token.
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv("JWT_ACCESS_HOURS", "8")))
    JWT_COOKIE_SECURE = _bool("JWT_COOKIE_SECURE", True)
    JWT_COOKIE_SAMESITE = os.getenv("JWT_COOKIE_SAMESITE", "Lax")
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_ACCESS_COOKIE_PATH = "/api/"
    JWT_ACCESS_CSRF_COOKIE_PATH = "/"

    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

    MODEL_PATH = os.getenv("MODEL_PATH", str(PROJECT_ROOT / "ml" / "artifacts" / "price_model.joblib"))
    RATE_LIMIT_ENABLED = _bool("RATE_LIMIT_ENABLED", True)
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB request bodies
    JSON_SORT_KEYS = False
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class DevelopmentConfig(Config):
    DEBUG = True
    JWT_COOKIE_SECURE = _bool("JWT_COOKIE_SECURE", False)  # http://localhost in development
    SECRET_KEY = Config.SECRET_KEY or "dev-only-secret-change-me"
    JWT_SECRET_KEY = Config.JWT_SECRET_KEY or "dev-only-jwt-secret-change-me-32bytes!"


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    JWT_SECRET_KEY = "test-jwt-secret-that-is-long-enough-32b"
    JWT_COOKIE_SECURE = False
    # Tests default to in-memory SQLite; set TEST_DATABASE_URL to run them against MySQL.
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_ENGINE_OPTIONS = {}
    RATE_LIMIT_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False


CONFIGS = {"development": DevelopmentConfig, "testing": TestingConfig, "production": ProductionConfig}


def validate_config(cfg) -> None:
    """Fail fast with a helpful message instead of starting with an unsafe config."""
    if not cfg.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URL is not set. Copy backend/.env.example to backend/.env and configure MySQL.")
    if cfg.get("APP_ENV") == "production":
        for key in ("SECRET_KEY", "JWT_SECRET_KEY"):
            if not cfg.get(key) or len(cfg[key]) < 32:
                raise RuntimeError(f"{key} must be set to a random value of at least 32 characters in production.")
        if not cfg.get("JWT_COOKIE_SECURE"):
            raise RuntimeError("JWT_COOKIE_SECURE must be true in production (HTTPS only).")
