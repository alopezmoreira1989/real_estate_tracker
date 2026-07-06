"""Compile a persisted condition tree into an executable Specification (doc 04 §5).

Walks a :class:`SearchAlert`'s :class:`RuleGroup`/:class:`AlertCondition` tree,
resolving each leaf's field via the :class:`FieldRegistry` and its operator via
the operator strategies, and assembling the composite specification. Rejects an
unknown field or an operator not permitted for the field's type with
:class:`InvalidConditionError`.
"""

from __future__ import annotations

from real_estate.domain.errors import InvalidConditionError
from real_estate.domain.model.alert import SearchAlert
from real_estate.domain.model.conditions import (
    AlertCondition,
    GroupOperator,
    RuleGroup,
)
from real_estate.domain.rules.field_registry import FieldRegistry
from real_estate.domain.rules.operators import strategy_for
from real_estate.domain.rules.specification import (
    AndSpecification,
    FieldSpecification,
    NotSpecification,
    OrSpecification,
    Specification,
)


class SpecificationFactory:
    """Builds specifications from persisted alert conditions."""

    def __init__(self, registry: FieldRegistry) -> None:
        self._registry = registry

    def build(self, alert: SearchAlert) -> Specification:
        """Compile an alert's whole condition tree into a Specification."""
        return self._node(alert.conditions)

    def _node(self, node: AlertCondition | RuleGroup) -> Specification:
        if isinstance(node, RuleGroup):
            return self._group(node)
        return self._leaf(node)

    def _group(self, group: RuleGroup) -> Specification:
        children = tuple(self._node(child) for child in group.children)
        match group.operator:
            case GroupOperator.ALL:
                return AndSpecification(children)
            case GroupOperator.ANY:
                return OrSpecification(children)
            case GroupOperator.NONE:
                return NotSpecification(OrSpecification(children))

    def _leaf(self, condition: AlertCondition) -> Specification:
        descriptor = self._registry.get(condition.field_key)
        if condition.operator not in descriptor.allowed_operators:
            raise InvalidConditionError(
                f"operator {condition.operator} is not valid for field "
                f"{condition.field_key!r} ({descriptor.field_type.name})"
            )
        return FieldSpecification(descriptor, strategy_for(condition.operator), condition.value)
