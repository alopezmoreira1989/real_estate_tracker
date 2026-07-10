"""Single-user bootstrap: get-or-create the one owner account an MVP without
auth (V3 scope) still needs a real ``user_id`` for.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from real_estate.domain.model.identifiers import UserId
from real_estate.infrastructure.persistence.models.orm import UserModel


def ensure_default_user(session_factory: sessionmaker[Session], email: str) -> UserId:
    """Return the owner's ``UserId``, creating the row on first run."""
    with session_factory() as session:
        existing = session.execute(
            select(UserModel).where(UserModel.email == email)
        ).scalar_one_or_none()
        if existing is not None:
            return UserId(existing.id)

        user_id = uuid4()
        session.add(
            UserModel(
                id=user_id,
                email=email,
                display_name=email.split("@")[0],
                created_at=datetime.now(UTC),
            )
        )
        session.commit()
        return UserId(user_id)
