"""Fixtures for persistence integration tests.

Builds the schema on a temporary SQLite database, seeds a user (so alert
foreign keys are satisfiable), and yields a small harness exposing a
Unit-of-Work factory plus the seeded ``user_id``.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from real_estate.domain.model.identifiers import UserId
from real_estate.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
)
from real_estate.infrastructure.persistence.models import Base
from real_estate.infrastructure.persistence.models.orm import UserModel
from real_estate.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork

_SEED_TIME = datetime(2026, 7, 4, 12, 0)  # naive: SQLite does not persist tz


@dataclass
class Persistence:
    """Test harness bundling a UoW factory and a seeded user id."""

    new_uow: Callable[[], SqlAlchemyUnitOfWork]
    user_id: UserId


@pytest.fixture
def persistence(tmp_path: Path) -> Iterator[Persistence]:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    user_id = UserId(uuid4())
    with session_factory() as session:
        session.add(
            UserModel(
                id=user_id,
                email=f"{user_id}@example.test",
                display_name="Test User",
                created_at=_SEED_TIME,
            )
        )
        session.commit()

    yield Persistence(new_uow=lambda: SqlAlchemyUnitOfWork(session_factory), user_id=user_id)
    engine.dispose()
