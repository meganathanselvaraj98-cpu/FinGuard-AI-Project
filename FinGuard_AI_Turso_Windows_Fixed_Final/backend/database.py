"""Database engine, scoped sessions, and Turso cloud synchronization."""

from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool
from backend.config import settings

logger = logging.getLogger(__name__)
_SYNC_LOCK = threading.Lock()
_LAST_PULL = 0.0

class LibsqlConnectionAdapter:
    """Make the libSQL connection compatible with SQLAlchemy's SQLite dialect."""

    def __init__(self, connection):
        self._connection = connection

    def __getattr__(self, name):
        return getattr(self._connection, name)

    def create_function(
        self,
        name,
        num_params,
        function,
        *,
        deterministic=False,
    ):
        return None


def _new_turso_connection():
    try:
        import libsql
    except ImportError as error:
        raise RuntimeError(
            "Turso mode requires the 'libsql' package. "
            "Install it using: python -m pip install libsql==0.1.11"
        ) from error

    settings.turso_replica_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = libsql.connect(
        str(settings.turso_replica_path),
        sync_url=settings.turso_database_url,
        auth_token=settings.turso_auth_token,
        sync_interval=30,
    )

    return LibsqlConnectionAdapter(connection)

def _build_engine():
    common = {
        "pool_pre_ping": True,
        "future": True,
    }

    if settings.is_turso:
        return create_engine(
            "sqlite://",
            creator=_new_turso_connection,
            poolclass=QueuePool,
            pool_size=3,
            max_overflow=2,
            pool_timeout=30,
            pool_recycle=300,
            **common,
        )

    return create_engine(
        settings.database_url,
        connect_args={
            "check_same_thread": False,
            "timeout": 30,
        },
        **common,
    )


engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

if settings.is_sqlite:
    @event.listens_for(engine, "connect")
    def _configure_local_sqlite(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()


def _sync_driver_connection() -> bool:
    """Synchronize the local replica with Turso Cloud."""
    if not settings.is_turso:
        return False
    raw_connection = engine.raw_connection()
    try:
        driver_connection = getattr(raw_connection, "driver_connection", None)
        if driver_connection is None:
            driver_connection = getattr(raw_connection, "connection", None)
        sync_method = getattr(driver_connection, "sync", None)
        if callable(sync_method):
            sync_method()
            return True
        return False
    finally:
        raw_connection.close()


def sync_from_turso(*, force: bool = False) -> bool:
    """Pull recent cloud changes into the local replica with light throttling."""
    global _LAST_PULL
    if not settings.is_turso:
        return False
    now = time.monotonic()
    if not force and now - _LAST_PULL < 3:
        return False
    with _SYNC_LOCK:
        now = time.monotonic()
        if not force and now - _LAST_PULL < 3:
            return False
        changed = _sync_driver_connection()
        _LAST_PULL = time.monotonic()
        return changed


def sync_to_turso() -> None:
    """Confirm remote writes and refresh the local replica."""
    if not settings.is_turso:
        return
    with _SYNC_LOCK:
        _sync_driver_connection()


@contextmanager
def session_scope() -> Iterator[Session]:
    if settings.is_turso:
        sync_from_turso()
    session = SessionLocal()
    try:
        yield session
        has_changes = bool(session.new or session.dirty or session.deleted)
        session.commit()
        if settings.is_turso and has_changes:
            sync_to_turso()
    except Exception:
        session.rollback()
        logger.exception("Database transaction rolled back")
        raise
    finally:
        session.close()


def _apply_compatibility_migrations() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "transactions" in tables:
        columns = {column["name"] for column in inspector.get_columns("transactions")}
        if "statement_import_id" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE transactions ADD COLUMN statement_import_id INTEGER NULL"))
            if settings.is_turso:
                sync_to_turso()


def initialize_database() -> None:
    from backend.models import Base
    from backend.services import seed_admin_from_environment, seed_default_categories

    settings.active_database_path.parent.mkdir(parents=True, exist_ok=True)
    if settings.is_turso:
        sync_from_turso(force=True)
    Base.metadata.create_all(bind=engine)
    if settings.is_turso:
        sync_to_turso()
        sync_from_turso(force=True)
    _apply_compatibility_migrations()
    with session_scope() as session:
        seed_default_categories(session)
        seed_admin_from_environment(session)
    logger.info("Database initialized in %s mode", settings.database_mode)
