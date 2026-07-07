"""SQLAlchemy adapter for :class:`SearchExecutionRepository`."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from real_estate.domain.ports.repositories import SearchExecutionStatus
from real_estate.infrastructure.persistence.models.orm import SearchExecutionModel
from real_estate.infrastructure.persistence.repositories.portal_lookup import get_or_create_portal


class SqlAlchemySearchExecutionRepository:
    """Audit trail of scrape attempts — one row per attempt, success or failure."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        *,
        portal_slug: str,
        query_signature: str,
        status: SearchExecutionStatus,
        listings_found: int,
        listings_new: int,
        error: str | None,
        started_at: datetime,
        finished_at: datetime,
    ) -> None:
        portal = get_or_create_portal(self._session, portal_slug)
        self._session.add(
            SearchExecutionModel(
                id=uuid4(),
                portal_id=portal.id,
                query_signature=query_signature,
                status=status.value,
                listings_found=listings_found,
                listings_new=listings_new,
                error=error,
                started_at=started_at,
                finished_at=finished_at,
            )
        )
