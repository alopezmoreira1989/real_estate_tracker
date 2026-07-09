"""Engine and session factory.

Builds a SQLAlchemy engine from settings and a ``sessionmaker``. SQLite gets
``foreign_keys=ON`` per connection so FK constraints are actually enforced
(doc 03 §3).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def create_db_engine(database_url: str) -> Engine:
    """Create an engine, enabling SQLite foreign-key enforcement when relevant."""
    engine = create_engine(database_url, future=True)

    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _enable_sqlite_fk(dbapi_connection: object, _record: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            # Phase 7 introduces concurrent writers (per-portal worker pools,
            # #33); without a busy timeout SQLite raises "database is locked"
            # immediately on write contention instead of waiting briefly.
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a ``sessionmaker`` bound to ``engine``."""
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Provide a transactional session scope (commit on success, rollback on error)."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
