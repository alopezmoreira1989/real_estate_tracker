"""AlertMatch: the fact that a property satisfied an alert."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from real_estate.domain.model.identifiers import AlertId, MatchId, PropertyId


class MatchStatus(StrEnum):
    """Lifecycle of a match as it moves toward notification."""

    NEW = "NEW"
    NOTIFIED = "NOTIFIED"
    SUPPRESSED = "SUPPRESSED"


@dataclass(frozen=True, slots=True)
class AlertMatch:
    """A property matched an alert.

    Identity is the **natural key** ``(alert_id, property_id)`` — the other
    fields are excluded from equality/hashing so two observations of the same
    match are equal. This underpins idempotency: persisting relies on the
    ``UNIQUE(alert_id, property_id)`` constraint, and de-duplicating a list of
    matches is a plain ``set`` operation.
    """

    alert_id: AlertId
    property_id: PropertyId
    matched_at: datetime = field(compare=False)
    status: MatchStatus = field(default=MatchStatus.NEW, compare=False)
    id: MatchId | None = field(default=None, compare=False)
