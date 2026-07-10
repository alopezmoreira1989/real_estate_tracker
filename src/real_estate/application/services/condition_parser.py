"""Parses CLI/dashboard condition strings into a RuleGroup.

Condition strings are ``FIELD:OPERATOR[:VALUE]`` (e.g. ``province:EQ:36``,
``price_per_m2:LTE:20``, ``price:BETWEEN:50000,200000``,
``features.has_garden:EXISTS``) — shared by every presentation surface that
lets a person build an alert (CLI's ``alerts create``, the dashboard's
create/edit forms), so the parsing/coercion logic lives once here rather
than in each use-case (``CreateAlert``, ``UpdateAlert``).

AND-only for the MVP (ADR-014): every condition string becomes one leaf in
a single top-level ``RuleGroup(GroupOperator.ALL, ...)``.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal, InvalidOperation

from real_estate.domain.errors import InvalidConditionError
from real_estate.domain.model.conditions import (
    AlertCondition,
    ConditionValue,
    GroupOperator,
    Operator,
    RuleGroup,
    Scalar,
)
from real_estate.domain.rules import FieldRegistry, FieldType

_NULLARY_OPERATORS = frozenset({Operator.EXISTS, Operator.NOT_EXISTS})


def parse_conditions(field_registry: FieldRegistry, condition_strings: Sequence[str]) -> RuleGroup:
    """Parse every condition string into one AND-only RuleGroup."""
    return RuleGroup(
        GroupOperator.ALL,
        tuple(_parse_condition(field_registry, raw) for raw in condition_strings),
    )


def _parse_condition(field_registry: FieldRegistry, raw: str) -> AlertCondition:
    parts = raw.split(":", 2)
    if len(parts) < 2:
        raise InvalidConditionError(f"malformed condition {raw!r}, expected FIELD:OPERATOR[:VALUE]")
    field_key, operator_name, *rest = parts
    value_text = rest[0] if rest else None

    descriptor = field_registry.get(field_key)
    try:
        operator = Operator(operator_name.upper())
    except ValueError as exc:
        raise InvalidConditionError(f"unknown operator: {operator_name!r}") from exc
    if operator not in descriptor.allowed_operators:
        raise InvalidConditionError(f"{operator} is not valid for field {field_key!r}")

    value = _coerce_value(descriptor.field_type, operator, value_text)
    return AlertCondition(field_key, operator, value)


def _coerce_value(
    field_type: FieldType, operator: Operator, value_text: str | None
) -> ConditionValue | None:
    if operator in _NULLARY_OPERATORS:
        return None
    if value_text is None:
        raise InvalidConditionError(f"{operator} requires a value")
    if operator is Operator.BETWEEN:
        low_text, _, high_text = value_text.partition(",")
        return (
            _coerce_scalar(field_type, low_text.strip()),
            _coerce_scalar(field_type, high_text.strip()),
        )
    return _coerce_scalar(field_type, value_text)


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
