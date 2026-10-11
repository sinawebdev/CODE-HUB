"""All settings come from environment variables / .env. Nothing secret lives in code."""
from pathlib import Path

from pydantic import NonNegativeInt, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "KoforLink"
    app_version: str = "0.1.0"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://koforlink:koforlink@localhost:5432/koforlink"
    # Optional direct/session connection for Alembic when runtime uses transaction pooling.
    migration_database_url: str = ""
    database_pool_size: PositiveInt = 5
    database_max_overflow: NonNegativeInt = 0
    secret_key: str = "change-me"

    # Tokens: short-lived JWT access tokens + rotating refresh tokens stored in the database.
    access_token_minutes: int = 15
    refresh_token_days: int = 30  # "remember me"
    session_hours: int = 72  # refresh-token lifetime without "remember me"

    # Brute-force protection on login.
    max_login_attempts: int = 5
    lock_minutes: int = 15

    # One-time codes (email verification, password reset).
    otp_expiry_minutes: int = 10
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60
    otp_max_requests_per_hour: int = 10

    story_expiry_hours: int = 24

    # Uploaded files are stored on local disk under media_root (object storage later).
    media_root: Path = Path("media")
    max_upload_bytes: int = 5 * 1024 * 1024
    story_max_upload_bytes: int = 8 * 1024 * 1024
    # Prefix for absolute media URLs, e.g. https://api.koforlink.com. Empty = relative URLs.
    public_base_url: str = ""

    # SMTP. Leave smtp_host empty in development: emails are then logged instead of sent.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    mail_from: str = "KoforLink <no-reply@koforlink.local>"

    # HTTP. cors_origins is a JSON list, e.g. CORS_ORIGINS='["http://localhost:5500"]'.
    cors_origins: list[str] = []
    serve_frontend: bool = True
    frontend_dir: Path = _REPO_ROOT / "frontend"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() in {"development", "dev", "local", "test"}


settings = Settings()
