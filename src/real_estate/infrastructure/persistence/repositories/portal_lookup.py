"""Shared ``portal_slug`` -> ``PortalModel`` lookup.

Used by every repository that keys rows by ``portal_id`` (portal listings,
search executions, search cache). ``AlertRepository`` has its own private
copy predating this helper (Phase 2); not worth touching already-shipped,
tested code to dedupe ~10 lines.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from real_estate.infrastructure.persistence.models.orm import PortalModel


def get_or_create_portal(session: Session, slug: str) -> PortalModel:
    existing = session.execute(
        select(PortalModel).where(PortalModel.slug == slug)
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    portal = PortalModel(slug=slug, name=slug, base_url=f"https://{slug}")
    session.add(portal)
    session.flush()
    return portal
