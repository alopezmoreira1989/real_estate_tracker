"""SQLAlchemy adapter for :class:`SearchCacheRepository`."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from real_estate.domain.model.identifiers import PropertyId
from real_estate.infrastructure.persistence.models.orm import SearchCacheModel
from real_estate.infrastructure.persistence.repositories.portal_lookup import get_or_create_portal


class SqlAlchemySearchCacheRepository:
    """TTL-based cache of a query signature's resulting property ids."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, signature: str, *, now: datetime) -> Sequence[PropertyId] | None:
        model = self._session.get(SearchCacheModel, signature)
        if model is None or model.expires_at <= now:
            return None
        return [PropertyId(UUID(raw_id)) for raw_id in model.result_ref.get("property_ids", [])]

    def put(
        self,
        signature: str,
        portal_slug: str,
        property_ids: Sequence[PropertyId],
        *,
        fetched_at: datetime,
        ttl_seconds: int,
    ) -> None:
        result_ref = {"property_ids": [str(property_id) for property_id in property_ids]}
        expires_at = fetched_at + timedelta(seconds=ttl_seconds)

        existing = self._session.get(SearchCacheModel, signature)
        if existing is not None:
            existing.result_ref = result_ref
            existing.fetched_at = fetched_at
            existing.expires_at = expires_at
            return

        portal = get_or_create_portal(self._session, portal_slug)
        self._session.add(
            SearchCacheModel(
                query_signature=signature,
                portal_id=portal.id,
                result_ref=result_ref,
                fetched_at=fetched_at,
                expires_at=expires_at,
            )
        )
