"""Central configuration for local SQLite and shared Turso deployment."""

from __future__ import annotations

import base64
import os
import secrets
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


def _load_streamlit_secrets() -> dict[str, object]:
    path = BASE_DIR / ".streamlit" / "secrets.toml"
    if not path.exists():
        return {}
    try:
        with path.open("rb") as file:
            return tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


_FILE_SECRETS = _load_streamlit_secrets()


def _setting(name: str, default: str = "") -> str:
    env_value = os.getenv(name)
    if env_value is not None:
        return env_value.strip()
    value = _FILE_SECRETS.get(name, default)
    return str(value).strip()


def _load_or_create_text_secret(filename: str, length: int = 48) -> str:
    secret_dir = BASE_DIR / ".secrets"
    secret_dir.mkdir(parents=True, exist_ok=True)
    path = secret_dir / filename
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        if value:
            return value
    value = secrets.token_urlsafe(length)
    path.write_text(value, encoding="utf-8")
    return value


def _database_url() -> str:
    candidate = _setting("DATABASE_URL")
    if candidate:
        return candidate
    data_dir = BASE_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{(data_dir / 'finguard_ai.db').as_posix()}"


@dataclass(frozen=True)
class Settings:
    app_name: str = field(default_factory=lambda: _setting("APP_NAME", "FinGuard AI"))
    environment: str = field(default_factory=lambda: _setting("APP_ENV", "development"))
    database_url: str = field(default_factory=_database_url)
    turso_database_url: str = field(default_factory=lambda: _setting("TURSO_DATABASE_URL"))
    turso_auth_token: str = field(default_factory=lambda: _setting("TURSO_AUTH_TOKEN"))
    secret_key: str = field(
        default_factory=lambda: _setting("SECRET_KEY") or _load_or_create_text_secret("jwt_secret.txt")
    )
    field_encryption_key: str = field(default_factory=lambda: _setting("FIELD_ENCRYPTION_KEY"))
    hash_pepper: str = field(
        default_factory=lambda: _setting("HASH_PEPPER") or _load_or_create_text_secret("hash_pepper.txt")
    )
    admin_email: str = field(default_factory=lambda: _setting("ADMIN_EMAIL"))
    admin_password: str = field(default_factory=lambda: _setting("ADMIN_PASSWORD"))
    cookie_secure: bool = field(default_factory=lambda: _setting("COOKIE_SECURE", "false").lower() == "true")
    access_token_minutes: int = field(default_factory=lambda: int(_setting("ACCESS_TOKEN_MINUTES", "30")))
    max_upload_mb: int = field(default_factory=lambda: int(_setting("MAX_UPLOAD_MB", "50")))
    data_dir: Path = BASE_DIR / "data"
    backup_dir: Path = BASE_DIR / "backups"
    report_dir: Path = BASE_DIR / "reports"
    model_dir: Path = BASE_DIR / "models"
    user_model_dir: Path = BASE_DIR / "models" / "runtime"
    secret_dir: Path = BASE_DIR / ".secrets"
    log_dir: Path = BASE_DIR / "logs"

    @property
    def is_turso(self) -> bool:
        return bool(self.turso_database_url and self.turso_auth_token)

    @property
    def local_only(self) -> bool:
        return not self.is_turso

    @property
    def is_sqlite(self) -> bool:
        return not self.is_turso and self.database_url.startswith("sqlite")

    @property
    def database_mode(self) -> str:
        return "Turso Cloud" if self.is_turso else "Local SQLite"

    @property
    def sqlite_path(self) -> Path:
        prefix = "sqlite:///"
        raw_path = self.database_url[len(prefix):] if self.database_url.startswith(prefix) else ""
        return Path(raw_path).resolve() if raw_path else self.data_dir / "finguard_ai.db"

    @property
    def turso_http_url(self) -> str:
        if self.turso_database_url.startswith("libsql://"):
            return "https://" + self.turso_database_url.removeprefix("libsql://")
        return self.turso_database_url

    @property
    def turso_replica_path(self) -> Path:
        return self.data_dir / "finguard_turso_replica.db"

    @property
    def active_database_path(self) -> Path:
        return self.turso_replica_path if self.is_turso else self.sqlite_path


settings = Settings()
for directory in (
    settings.data_dir,
    settings.backup_dir,
    settings.report_dir,
    settings.model_dir,
    settings.user_model_dir,
    settings.secret_dir,
    settings.log_dir,
):
    directory.mkdir(parents=True, exist_ok=True)


def get_field_encryption_key() -> bytes:
    if settings.field_encryption_key:
        return settings.field_encryption_key.encode("utf-8")

    key_file = settings.secret_dir / "field_key.key"
    if key_file.exists():
        value = key_file.read_bytes().strip()
        if value:
            return value

    key = base64.urlsafe_b64encode(os.urandom(32))
    key_file.write_bytes(key)
    return key
