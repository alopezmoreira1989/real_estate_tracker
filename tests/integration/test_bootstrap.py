"""Integration test: ensure_default_user against a real (temp) SQLite DB."""

from __future__ import annotations

from pathlib import Path

from real_estate.infrastructure.persistence.bootstrap import ensure_default_user
from real_estate.infrastructure.persistence.database import create_db_engine, create_session_factory
from real_estate.infrastructure.persistence.models import Base


def _session_factory(tmp_path: Path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'bootstrap.db'}")
    Base.metadata.create_all(engine)
    return create_session_factory(engine)


def test_ensure_default_user_creates_the_user_on_first_call(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)

    user_id = ensure_default_user(session_factory, "owner@example.test")

    assert user_id is not None


def test_ensure_default_user_is_idempotent(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)

    first = ensure_default_user(session_factory, "owner@example.test")
    second = ensure_default_user(session_factory, "owner@example.test")

    assert first == second
