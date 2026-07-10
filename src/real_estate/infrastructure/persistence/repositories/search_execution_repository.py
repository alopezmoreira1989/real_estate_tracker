"""SQLAlchemy adapter for :class:`SearchExecutionRepository`."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from real_estate.domain.model.search_execution import SearchExecution, SearchExecutionStatus
from real_estate.infrastructure.persistence.models.orm import PortalModel, SearchExecutionModel
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
        normalization_issues: int,
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
                normalization_issues=normalization_issues,
                error=error,
                started_at=started_at,
                finished_at=finished_at,
            )
        )

    def list_recent(self, limit: int) -> Sequence[SearchExecution]:
        stmt = (
            select(SearchExecutionModel, PortalModel.slug)
            .join(PortalModel, PortalModel.id == SearchExecutionModel.portal_id)
            .order_by(SearchExecutionModel.started_at.desc())
            .limit(limit)
        )
        return [
            SearchExecution(
                portal_slug=portal_slug,
                query_signature=model.query_signature,
                status=SearchExecutionStatus(model.status),
                listings_found=model.listings_found,
                listings_new=model.listings_new,
                normalization_issues=model.normalization_issues,
                error=model.error,
                started_at=model.started_at,
                finished_at=model.finished_at,
            )
            for model, portal_slug in self._session.execute(stmt)
        ]
