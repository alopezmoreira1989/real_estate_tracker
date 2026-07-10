"""CreateAlert — builds and persists a new SearchAlert from flat, AND-only
conditions (ADR-014: AND-only condition UI for the MVP).

Condition strings are ``FIELD:OPERATOR[:VALUE]`` (e.g. ``province:EQ:36``,
``price_per_m2:LTE:20``, ``price:BETWEEN:50000,200000``,
``features.has_garden:EXISTS``) — the CLI's own syntax, parsed here rather
than in presentation so the parsing/validation logic is testable without a
Typer runner and reusable by any future presentation surface.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from real_estate.application.ports import Clock
from real_estate.domain.errors import InvalidConditionError
from real_estate.domain.model.alert import SearchAlert
from real_estate.domain.model.conditions import (
    AlertCondition,
    ConditionValue,
    GroupOperator,
    Operator,
    RuleGroup,
    Scalar,
)
from real_estate.domain.model.identifiers import AlertId, UserId
from real_estate.domain.ports import UnitOfWork
from real_estate.domain.rules import FieldRegistry, FieldType

_NULLARY_OPERATORS = frozenset({Operator.EXISTS, Operator.NOT_EXISTS})


class CreateAlert:
    """Parses CLI condition strings and persists a new SearchAlert."""

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
        conditions = RuleGroup(
            GroupOperator.ALL, tuple(self._parse_condition(raw) for raw in condition_strings)
        )
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

    def _parse_condition(self, raw: str) -> AlertCondition:
        parts = raw.split(":", 2)
        if len(parts) < 2:
            raise InvalidConditionError(
                f"malformed condition {raw!r}, expected FIELD:OPERATOR[:VALUE]"
            )
        field_key, operator_name, *rest = parts
        value_text = rest[0] if rest else None

        descriptor = self._field_registry.get(field_key)
        try:
            operator = Operator(operator_name.upper())
        except ValueError as exc:
            raise InvalidConditionError(f"unknown operator: {operator_name!r}") from exc
        if operator not in descriptor.allowed_operators:
            raise InvalidConditionError(f"{operator} is not valid for field {field_key!r}")

        value = self._coerce_value(descriptor.field_type, operator, value_text)
        return AlertCondition(field_key, operator, value)

    def _coerce_value(
        self, field_type: FieldType, operator: Operator, value_text: str | None
    ) -> ConditionValue | None:
        if operator in _NULLARY_OPERATORS:
            return None
        if value_text is None:
            raise InvalidConditionError(f"{operator} requires a value")
        if operator is Operator.BETWEEN:
            low_text, _, high_text = value_text.partition(",")
            return (
                self._coerce_scalar(field_type, low_text.strip()),
                self._coerce_scalar(field_type, high_text.strip()),
            )
        return self._coerce_scalar(field_type, value_text)

    @staticmethod
    def _coerce_scalar(field_type: FieldType, value_text: str) -> Scalar:
        if field_type in (FieldType.MONEY, FieldType.AREA):
            try:
                return Decimal(value_text)
            except InvalidOperation as exc:
                raise InvalidConditionError(f"expected a number, got {value_text!r}") from exc
        if field_type is FieldType.NUMERIC:
            try:
                return int(value_text)
            except ValueError as exc:
                raise InvalidConditionError(f"expected an integer, got {value_text!r}") from exc
        if field_type is FieldType.BOOL:
            lowered = value_text.strip().lower()
            if lowered in {"true", "1", "yes"}:
                return True
            if lowered in {"false", "0", "no"}:
                return False
            raise InvalidConditionError(f"expected a boolean, got {value_text!r}")
        return value_text
