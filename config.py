"""Application configuration loaded from environment variables."""

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration shared by all environments."""

    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

    # ── Database ──────────────────────────────────────────────────────────
    # Require explicit DATABASE_URL; never fall back to SQLite silently.
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": 5,
        "max_overflow": 10,
    }

    # ── Session / Cookies ─────────────────────────────────────────────────
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # ── AI Service ────────────────────────────────────────────────────────
    AI_API_KEY = os.getenv("AI_API_KEY", "")
    AI_MODEL = os.getenv("AI_MODEL", "gemini-3.1-flash-lite")

    # ── Misc ──────────────────────────────────────────────────────────────
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB request body limit

    @staticmethod
    def validate():
        """Raise early if critical config is missing or invalid."""
        db_url = os.getenv("DATABASE_URL", "")
        if not db_url:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set. "
                "Example: mysql+pymysql://root:password@localhost/prepai_db"
            )
        if "sqlite" in db_url.lower():
            raise RuntimeError(
                "DATABASE_URL must point to a MySQL database, not SQLite. "
                "Example: mysql+pymysql://root:password@localhost/prepai_db"
            )


class DevelopmentConfig(Config):
    """Local development settings."""

    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production-ready settings."""

    DEBUG = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Isolated test settings."""

    TESTING = True
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        "mysql+pymysql://root:MySQL%4073@localhost/prepai_test_db?charset=utf8mb4",
    )
    # Tests use their own DATABASE_URL from env or fixture
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_size": 2,
        "max_overflow": 0,
    }

    @staticmethod
    def validate():
        """Tests may use a special test database; still reject SQLite."""
        db_url = os.getenv("DATABASE_URL", os.getenv("TEST_DATABASE_URL", ""))
        if db_url and "sqlite" in db_url.lower():
            raise RuntimeError("Tests must not use SQLite.")


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    """Return the config class for the current FLASK_ENV."""
    env = os.getenv("FLASK_ENV", "development").lower()
    return config_by_name.get(env, DevelopmentConfig)
