"""Normalizer port.

Turns a portal-shaped ``RawListing`` into a canonical ``Property``. The only
component allowed to know portal-specific field names/vocabularies. In Phase 4
the return type is refined to a ``NormalizationResult`` carrying non-fatal
issues; for now it returns the ``Property`` directly.
"""

from __future__ import annotations

from typing import Protocol

from real_estate.domain.model.property import Property
from real_estate.domain.ports.scraper import RawListing


class Normalizer(Protocol):
    """Maps a raw listing from one portal onto the canonical model."""

    portal_slug: str

    def normalize(self, raw: RawListing) -> Property:
        """Convert ``raw`` into a canonical :class:`Property`."""
        ...
