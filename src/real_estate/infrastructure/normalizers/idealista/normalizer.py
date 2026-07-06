"""The Idealista Normalizer — the first concrete example of BaseNormalizer.

The actual HTTP scraper that produces ``RawListing``s for Idealista is
Phase 5; this normalizer only needs a raw listing to consume, which is why it
lands here (Phase 4) ahead of the scraper.
"""

from __future__ import annotations

from real_estate.infrastructure.normalizers.base import BaseNormalizer
from real_estate.infrastructure.normalizers.idealista.field_map import IDEALISTA_FIELD_MAP


class IdealistaNormalizer(BaseNormalizer):
    """Normalizes raw Idealista listings into canonical ``Property`` objects."""

    portal_slug = "idealista"
    field_map = IDEALISTA_FIELD_MAP
