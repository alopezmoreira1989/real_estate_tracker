"""AlertEngine — evaluate alerts against candidate properties (doc 04 §6).

A pure domain service: it compiles an alert to a Specification (via the
factory) and returns the matches. It performs no I/O and does not persist —
persisting matches idempotently (the ``UNIQUE(alert_id, property_id)``
constraint) is the job of the RunAlertCycle use-case in Phase 5.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from real_estate.domain.model.alert import SearchAlert
from real_estate.domain.model.match import AlertMatch
from real_estate.domain.model.property import Property
from real_estate.domain.rules.factory import SpecificationFactory


class AlertEngine:
    """Evaluates an alert's specification over candidate properties."""

    def __init__(self, factory: SpecificationFactory) -> None:
        self._factory = factory

    def evaluate(
        self,
        alert: SearchAlert,
        candidates: Iterable[Property],
        *,
        now: datetime,
    ) -> list[AlertMatch]:
        """Return a match for each candidate that satisfies the alert."""
        spec = self._factory.build(alert)
        return [
            AlertMatch(alert_id=alert.id, property_id=prop.id, matched_at=now)
            for prop in candidates
            if spec.is_satisfied_by(prop)
        ]
