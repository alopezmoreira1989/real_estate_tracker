"""The SearchAlert aggregate root."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from real_estate.domain.errors import InvalidAlertError
from real_estate.domain.model.conditions import RuleGroup
from real_estate.domain.model.identifiers import AlertId, UserId

MIN_FREQUENCY_SECONDS = 60


@dataclass(slots=True)
class SearchAlert:
    """A named, reusable search profile owned by a user.

    The aggregate root owns its condition tree and its portal subscriptions;
    conditions are only ever changed through this root, which keeps the tree
    valid and bumps ``updated_at``. Mutating methods take an explicit ``now`` so
    the domain stays deterministic (no ``datetime.now()`` in logic; CLAUDE.md §8).
    """

    id: AlertId
    user_id: UserId
    name: str
    portal_slugs: frozenset[str]
    frequency_seconds: int
    conditions: RuleGroup
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    last_run_at: datetime | None = field(default=None)

    def __post_init__(self) -> None:
        self._validate(self.name, self.portal_slugs, self.frequency_seconds, self.conditions)

    @classmethod
    def create(
        cls,
        *,
        id: AlertId,
        user_id: UserId,
        name: str,
        portal_slugs: frozenset[str],
        frequency_seconds: int,
        conditions: RuleGroup,
        now: datetime,
    ) -> SearchAlert:
        """Create a new, validated alert timestamped at ``now``."""
        return cls(
            id=id,
            user_id=user_id,
            name=name,
            portal_slugs=portal_slugs,
            frequency_seconds=frequency_seconds,
            conditions=conditions,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def _validate(
        name: str,
        portal_slugs: frozenset[str],
        frequency_seconds: int,
        conditions: RuleGroup,
    ) -> None:
        if not name.strip():
            raise InvalidAlertError("alert name must not be empty")
        if not portal_slugs:
            raise InvalidAlertError("alert must monitor at least one portal")
        if frequency_seconds < MIN_FREQUENCY_SECONDS:
            raise InvalidAlertError(
                f"frequency must be >= {MIN_FREQUENCY_SECONDS}s, got {frequency_seconds}"
            )
        if conditions.leaf_count() < 1:
            raise InvalidAlertError("alert must have at least one condition")

    def rename(self, name: str, *, now: datetime) -> None:
        if not name.strip():
            raise InvalidAlertError("alert name must not be empty")
        self.name = name
        self.updated_at = now

    def replace_conditions(self, conditions: RuleGroup, *, now: datetime) -> None:
        """Swap the whole condition tree, keeping the alert valid."""
        if conditions.leaf_count() < 1:
            raise InvalidAlertError("alert must have at least one condition")
        self.conditions = conditions
        self.updated_at = now

    def set_portals(self, portal_slugs: frozenset[str], *, now: datetime) -> None:
        if not portal_slugs:
            raise InvalidAlertError("alert must monitor at least one portal")
        self.portal_slugs = portal_slugs
        self.updated_at = now

    def set_frequency(self, frequency_seconds: int, *, now: datetime) -> None:
        if frequency_seconds < MIN_FREQUENCY_SECONDS:
            raise InvalidAlertError(
                f"frequency must be >= {MIN_FREQUENCY_SECONDS}s, got {frequency_seconds}"
            )
        self.frequency_seconds = frequency_seconds
        self.updated_at = now

    def activate(self, *, now: datetime) -> None:
        self.is_active = True
        self.updated_at = now

    def deactivate(self, *, now: datetime) -> None:
        self.is_active = False
        self.updated_at = now

    def mark_run(self, *, now: datetime) -> None:
        """Record that the alert cycle evaluated this alert at ``now``."""
        self.last_run_at = now
