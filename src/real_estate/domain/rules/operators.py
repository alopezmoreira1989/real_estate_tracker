"""Operator strategies for the Rule Engine.

Each :class:`Operator` maps to a small, stateless :class:`OperatorStrategy`
(the Strategy pattern, doc 04 §4). Strategies compare a value **extracted from a
Property** (``actual``) against the condition's ``expected`` value; both are
plain primitives (str / Decimal / int / bool / tuple), so comparisons are
trivial and unit-safe.

Tri-state rule: ``actual is None`` (the portal did not state the value) fails
every comparison except ``EXISTS``/``NOT_EXISTS`` — unknown never counts as a
match for a positive filter (docs/architecture/02-domain-model.md §2).
"""

from __future__ import annotations

import unicodedata
from typing import Any, Protocol

from real_estate.domain.model.conditions import Operator


class OperatorStrategy(Protocol):
    """Compares an extracted value against a condition's expected value."""

    def matches(self, actual: Any, expected: Any) -> bool: ...


def _fold(text: str) -> str:
    """Case- and accent-insensitive folding (``agua`` == ``água`` == ``AGUA``)."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return stripped.casefold()


class _Eq:
    def matches(self, actual: Any, expected: Any) -> bool:
        return bool(actual == expected)


class _Neq:
    def matches(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        return bool(actual != expected)


class _Lt:
    def matches(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        return bool(actual < expected)


class _Lte:
    def matches(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        return bool(actual <= expected)


class _Gt:
    def matches(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        return bool(actual > expected)


class _Gte:
    def matches(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        return bool(actual >= expected)


class _Between:
    def matches(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        low, high = expected
        return bool(low <= actual <= high)


class _In:
    def matches(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        return actual in expected


class _NotIn:
    def matches(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        return actual not in expected


class _Contains:
    def matches(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        return _fold(str(expected)) in _fold(str(actual))


class _NotContains:
    def matches(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        return _fold(str(expected)) not in _fold(str(actual))


class _Exists:
    def matches(self, actual: Any, expected: Any) -> bool:
        return actual is not None


class _NotExists:
    def matches(self, actual: Any, expected: Any) -> bool:
        return actual is None


OPERATORS: dict[Operator, OperatorStrategy] = {
    Operator.EQ: _Eq(),
    Operator.NEQ: _Neq(),
    Operator.LT: _Lt(),
    Operator.LTE: _Lte(),
    Operator.GT: _Gt(),
    Operator.GTE: _Gte(),
    Operator.BETWEEN: _Between(),
    Operator.IN: _In(),
    Operator.NOT_IN: _NotIn(),
    Operator.CONTAINS: _Contains(),
    Operator.NOT_CONTAINS: _NotContains(),
    Operator.EXISTS: _Exists(),
    Operator.NOT_EXISTS: _NotExists(),
}


def strategy_for(operator: Operator) -> OperatorStrategy:
    """Return the strategy implementing ``operator``."""
    return OPERATORS[operator]
