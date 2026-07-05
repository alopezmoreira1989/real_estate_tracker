"""The alert condition tree.

Conditions are **data, not columns** (driver D1): an alert owns a tree of
``RuleGroup`` combinators over ``AlertCondition`` leaves. This module models the
tree and validates it *structurally* (operator/value shape, non-empty groups).

Validation that a leaf's ``field`` is a registered canonical field, and that the
operator is valid for that field's *type*, happens when the tree is compiled
against the Field Registry (Phase 3, ``SpecificationFactory``) — this module has
no dependency on the registry, keeping the model pure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

Scalar = str | int | Decimal | bool
ConditionValue = Scalar | tuple[Scalar, ...]
ConditionNode = "AlertCondition | RuleGroup"


class Operator(StrEnum):
    """Comparison operators a leaf condition may use."""

    EQ = "EQ"
    NEQ = "NEQ"
    LT = "LT"
    LTE = "LTE"
    GT = "GT"
    GTE = "GTE"
    BETWEEN = "BETWEEN"
    IN = "IN"
    NOT_IN = "NOT_IN"
    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT_CONTAINS"
    EXISTS = "EXISTS"
    NOT_EXISTS = "NOT_EXISTS"


class GroupOperator(StrEnum):
    """Boolean combinators over a group's children."""

    ALL = "ALL"  # AND
    ANY = "ANY"  # OR
    NONE = "NONE"  # NOT (none of the children may match)


_TUPLE_OPERATORS = {Operator.BETWEEN, Operator.IN, Operator.NOT_IN}
_NULLARY_OPERATORS = {Operator.EXISTS, Operator.NOT_EXISTS}


@dataclass(frozen=True, slots=True)
class AlertCondition:
    """A single predicate: ``field <operator> value``.

    ``value`` shape is validated against the operator:

    - ``EXISTS``/``NOT_EXISTS`` take no value (``None``).
    - ``BETWEEN`` takes a 2-tuple ``(low, high)``.
    - ``IN``/``NOT_IN`` take a non-empty tuple.
    - everything else takes a single scalar.
    """

    field_key: str
    operator: Operator
    value: ConditionValue | None = None

    def __post_init__(self) -> None:
        if not self.field_key.strip():
            raise ValueError("AlertCondition.field_key must not be empty")

        if self.operator in _NULLARY_OPERATORS:
            if self.value is not None:
                raise ValueError(f"{self.operator} takes no value")
            return

        if self.operator is Operator.BETWEEN:
            if not (isinstance(self.value, tuple) and len(self.value) == 2):
                raise ValueError("BETWEEN requires a (low, high) tuple")
            return

        if self.operator in {Operator.IN, Operator.NOT_IN}:
            if not (isinstance(self.value, tuple) and len(self.value) >= 1):
                raise ValueError(f"{self.operator} requires a non-empty tuple")
            return

        # Scalar operators.
        if self.value is None or isinstance(self.value, tuple):
            raise ValueError(f"{self.operator} requires a single scalar value")


@dataclass(frozen=True, slots=True)
class RuleGroup:
    """A boolean combinator over one or more child nodes (conditions or groups)."""

    operator: GroupOperator
    children: tuple[AlertCondition | RuleGroup, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if len(self.children) == 0:
            raise ValueError("RuleGroup must have at least one child")

    def leaf_count(self) -> int:
        """Total number of :class:`AlertCondition` leaves in this subtree."""
        total = 0
        for child in self.children:
            total += child.leaf_count() if isinstance(child, RuleGroup) else 1
        return total
