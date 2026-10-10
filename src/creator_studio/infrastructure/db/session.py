from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from creator_studio.infrastructure.db.base import Base
from creator_studio.infrastructure.db import models as _models  # noqa: F401
from creator_studio.infrastructure.settings import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _configure_sqlite(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_engine(url: str | None = None) -> Engine:
    global _engine, _session_factory
    if _engine is None or url is not None:
        settings = get_settings()
        engine_url = url or settings.sqlalchemy_url()
        connect_args = {"check_same_thread": False} if engine_url.startswith("sqlite") else {}
        _engine = create_engine(engine_url, future=True, connect_args=connect_args)
        if engine_url.startswith("sqlite"):
            _configure_sqlite(_engine)
        _session_factory = sessionmaker(_engine, expire_on_commit=False, future=True)
    return _engine


def get_session_factory(url: str | None = None) -> sessionmaker[Session]:
    get_engine(url)
    assert _session_factory is not None
    return _session_factory


def reset_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


_FTS_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS marketplace_items_fts USING fts5(
    item_id UNINDEXED,
    title,
    garment_description,
    style_tags
)
"""


def init_db(url: str | None = None) -> None:
    """Unit-test / offline fixture helper only.

    Application bootstrap must use Alembic (`upgrade_head`), not create_all.
    create_all alone would hide missing migrations; this helper also creates FTS5
    so isolated unit fixtures that explicitly call init_db stay consistent.
    """
    engine = get_engine(url)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text(_FTS_DDL))
        conn.execute(text("SELECT 1"))



@contextmanager
def session_scope(url: str | None = None) -> Iterator[Session]:
    factory = get_session_factory(url)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()