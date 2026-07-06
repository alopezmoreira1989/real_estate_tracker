"""The Rule Engine: Specification pattern + Field Registry + operator strategies.

Adding a new filter is registering a :class:`FieldDescriptor` — the engine never
changes (driver D1, doc 04).
"""

from real_estate.domain.rules.factory import SpecificationFactory
from real_estate.domain.rules.field_registry import (
    FieldDescriptor,
    FieldRegistry,
    FieldType,
    default_registry,
)
from real_estate.domain.rules.operators import OperatorStrategy, strategy_for
from real_estate.domain.rules.specification import (
    AndSpecification,
    FieldSpecification,
    NotSpecification,
    OrSpecification,
    Specification,
)

__all__ = [
    "AndSpecification",
    "FieldDescriptor",
    "FieldRegistry",
    "FieldSpecification",
    "FieldType",
    "NotSpecification",
    "OperatorStrategy",
    "OrSpecification",
    "Specification",
    "SpecificationFactory",
    "default_registry",
    "strategy_for",
]
