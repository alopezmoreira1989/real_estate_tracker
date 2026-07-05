"""Repository ports.

The domain speaks in collections of aggregates, not SQL. Infrastructure
provides concrete adapters (e.g. ``SqlAlchemyAlertRepository``). Repositories
are always scoped by ``user_id`` where the entity is user-owned (multi-tenant,
driver D5) — enforced by the adapters.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from real_estate.domain.model.alert import SearchAlert
from real_estate.domain.model.identifiers import AlertId, PropertyId, UserId
from real_estate.domain.model.property import Property


class AlertRepository(Protocol):
    """Persistence of the :class:`SearchAlert` aggregate."""

    def add(self, alert: SearchAlert) -> None: ...

    def get(self, alert_id: AlertId) -> SearchAlert | None: ...

    def list_for_user(self, user_id: UserId) -> Sequence[SearchAlert]: ...


class PropertyRepository(Protocol):
    """Persistence of canonical :class:`Property` entities."""

    def add(self, prop: Property) -> None: ...

    def get(self, property_id: PropertyId) -> Property | None: ...
