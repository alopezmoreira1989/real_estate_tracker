"""Normalizer port and its boundary DTOs.

Turns a portal-shaped ``RawListing`` into a canonical ``Property``. The only
component allowed to know portal-specific field names/vocabularies
(docs/architecture/05-normalization.md). Normalization never drops a listing
for a field it cannot map or parse — it falls back to ``OTHER``/``UNKNOWN`` or
``None`` and records a :class:`NormalizationIssue` instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from real_estate.domain.model.property import Property
from real_estate.domain.ports.scraper import RawListing


@dataclass(frozen=True, slots=True)
class NormalizationIssue:
    """A non-fatal problem encountered while normalizing one field.

    Carries enough to log and diagnose (docs/architecture/05-normalization.md
    §6): which canonical field was affected, a human-readable reason, and the
    offending raw value when there was one.
    """

    field: str
    message: str
    raw_value: str | None = None


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    """The outcome of normalizing one ``RawListing``.

    ``property`` is ``None`` only when the listing could not be turned into a
    valid ``Property`` at all (rare — most problems degrade to a fallback
    value plus an issue rather than failing construction entirely).
    """

    property: Property | None
    issues: tuple[NormalizationIssue, ...] = field(default_factory=tuple)


class Normalizer(Protocol):
    """Maps a raw listing from one portal onto the canonical model."""

    portal_slug: str

    def normalize(self, raw: RawListing) -> NormalizationResult:
        """Convert ``raw`` into a :class:`NormalizationResult`."""
        ...
