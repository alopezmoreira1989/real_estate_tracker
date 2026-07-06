"""Specification pattern for the Rule Engine (doc 04 §2).

A :class:`Specification` answers a single yes/no question about a
:class:`Property`. Composites combine specifications with boolean logic, and a
:class:`FieldSpecification` evaluates one leaf condition (a field + operator +
expected value). An alert's condition tree compiles 1:1 onto a specification
tree (see :mod:`real_estate.domain.rules.factory`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from real_estate.domain.model.property import Property
from real_estate.domain.rules.field_registry import FieldDescriptor
from real_estate.domain.rules.operators import OperatorStrategy


@runtime_checkable
class Specification(Protocol):
    """Answers 'does this property satisfy me?'."""

    def is_satisfied_by(self, prop: Property) -> bool: ...


@dataclass(frozen=True, slots=True)
class FieldSpecification:
    """A leaf: apply ``operator`` to the value ``descriptor`` extracts."""

    descriptor: FieldDescriptor
    operator: OperatorStrategy
    expected: Any

    def is_satisfied_by(self, prop: Property) -> bool:
        actual = self.descriptor.extract(prop)
        return self.operator.matches(actual, self.expected)


@dataclass(frozen=True, slots=True)
class AndSpecification:
    """Satisfied only if every child is (GroupOperator.ALL)."""

    specs: tuple[Specification, ...]

    def is_satisfied_by(self, prop: Property) -> bool:
        return all(spec.is_satisfied_by(prop) for spec in self.specs)


@dataclass(frozen=True, slots=True)
class OrSpecification:
    """Satisfied if any child is (GroupOperator.ANY)."""

    specs: tuple[Specification, ...]

    def is_satisfied_by(self, prop: Property) -> bool:
        return any(spec.is_satisfied_by(prop) for spec in self.specs)


@dataclass(frozen=True, slots=True)
class NotSpecification:
    """Satisfied when the wrapped specification is not."""

    spec: Specification

    def is_satisfied_by(self, prop: Property) -> bool:
        return not self.spec.is_satisfied_by(prop)
