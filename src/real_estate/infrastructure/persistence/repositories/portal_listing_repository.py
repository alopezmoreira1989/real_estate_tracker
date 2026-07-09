"""SQLAlchemy adapter for :class:`PortalListingRepository`."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from real_estate.domain.model.identifiers import PropertyId
from real_estate.infrastructure.persistence.models.orm import PortalListingModel, PortalModel
from real_estate.infrastructure.persistence.repositories.portal_lookup import get_or_create_portal


class SqlAlchemyPortalListingRepository:
    """Tracks the raw per-portal record backing a canonical Property."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_unchanged_property_id(
        self, portal_slug: str, external_id: str, content_hash: str
    ) -> PropertyId | None:
        model = self._find(portal_slug, external_id)
        if model is not None and model.content_hash == content_hash:
            return PropertyId(model.property_id)
        return None

    def upsert(
        self,
        *,
        portal_slug: str,
        external_id: str,
        property_id: PropertyId,
        url: str,
        raw_payload: Mapping[str, Any],
        content_hash: str,
        scraped_at: datetime,
    ) -> None:
        existing = self._find(portal_slug, external_id)
        if existing is not None:
            existing.property_id = property_id
            existing.url = url
            existing.raw_payload = dict(raw_payload)
            existing.content_hash = content_hash
            existing.scraped_at = scraped_at
            return

        portal = get_or_create_portal(self._session, portal_slug)
        self._session.add(
            PortalListingModel(
                id=uuid4(),
                portal_id=portal.id,
                property_id=property_id,
                external_id=external_id,
                url=url,
                raw_payload=dict(raw_payload),
                content_hash=content_hash,
                scraped_at=scraped_at,
            )
        )

    def get_url_for_property(self, property_id: PropertyId) -> str | None:
        model = (
            self._session.execute(
                select(PortalListingModel).where(PortalListingModel.property_id == property_id)
            )
            .scalars()
            .first()
        )
        return model.url if model is not None else None

    def _find(self, portal_slug: str, external_id: str) -> PortalListingModel | None:
        portal = self._session.execute(
            select(PortalModel).where(PortalModel.slug == portal_slug)
        ).scalar_one_or_none()
        if portal is None:
            return None
        return self._session.execute(
            select(PortalListingModel).where(
                PortalListingModel.portal_id == portal.id,
                PortalListingModel.external_id == external_id,
            )
        ).scalar_one_or_none()
