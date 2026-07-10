"""UpdateAlert — applies whichever fields a person actually changed on an
existing SearchAlert. Every mutation goes through the aggregate's own
mutators (rename, set_frequency, replace_conditions, activate/deactivate),
which is what keeps the alert valid and bumps updated_at consistently
(CLAUDE.md §5 SRP — this use-case only orchestrates, it owns no validation
of its own).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from real_estate.application.ports import Clock
from real_estate.application.services.condition_parser import parse_conditions
from real_estate.domain.errors import DomainError
from real_estate.domain.model.alert import SearchAlert
from real_estate.domain.model.identifiers import AlertId
from real_estate.domain.ports import UnitOfWork
from real_estate.domain.rules import FieldRegistry


class AlertNotFoundError(DomainError):
    """Raised when the alert to update does not exist."""


class UpdateAlert:
    """Applies partial updates to an existing SearchAlert."""

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
        alert_id: AlertId,
        name: str | None = None,
        frequency_seconds: int | None = None,
        is_active: bool | None = None,
        condition_strings: Sequence[str] | None = None,
    ) -> SearchAlert:
        now = self._clock.now()
        with self._uow_factory() as uow:
            alert = uow.alerts.get(alert_id)
            if alert is None:
                raise AlertNotFoundError(f"no such alert: {alert_id}")

            if name is not None:
                alert.rename(name, now=now)
            if frequency_seconds is not None:
                alert.set_frequency(frequency_seconds, now=now)
            if condition_strings is not None:
                conditions = parse_conditions(self._field_registry, condition_strings)
                alert.replace_conditions(conditions, now=now)
            if is_active is True:
                alert.activate(now=now)
            elif is_active is False:
                alert.deactivate(now=now)

            uow.alerts.add(alert)
            uow.commit()
        return alert
