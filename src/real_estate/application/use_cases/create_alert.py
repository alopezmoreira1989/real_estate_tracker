"""CreateAlert — builds and persists a new SearchAlert from flat, AND-only
conditions (ADR-014: AND-only condition UI for the MVP).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from uuid import uuid4

from real_estate.application.ports import Clock
from real_estate.application.services.condition_parser import parse_conditions
from real_estate.domain.model.alert import SearchAlert
from real_estate.domain.model.identifiers import AlertId, UserId
from real_estate.domain.ports import UnitOfWork
from real_estate.domain.rules import FieldRegistry


class CreateAlert:
    """Parses condition strings and persists a new SearchAlert."""

    def __init__(
        self,
        *,
        uow_factory: Callable[[], UnitOfWork],
        field_registry: FieldRegistry,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._field_registry = field_registry
        self._clock = clock

    def run(
        self,
        *,
        user_id: UserId,
        name: str,
        portal_slugs: frozenset[str],
        frequency_seconds: int,
        condition_strings: Sequence[str],
    ) -> SearchAlert:
        conditions = parse_conditions(self._field_registry, condition_strings)
        alert = SearchAlert.create(
            id=AlertId(uuid4()),
            user_id=user_id,
            name=name,
            portal_slugs=portal_slugs,
            frequency_seconds=frequency_seconds,
            conditions=conditions,
            now=self._clock.now(),
        )
        with self._uow_factory() as uow:
            uow.alerts.add(alert)
            uow.commit()
        return alert
