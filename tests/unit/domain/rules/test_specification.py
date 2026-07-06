from dataclasses import dataclass

from real_estate.domain.model import Property
from real_estate.domain.rules.specification import (
    AndSpecification,
    NotSpecification,
    OrSpecification,
    Specification,
)


@dataclass(frozen=True)
class _Const:
    """A stub specification with a fixed answer (isolates composite logic)."""

    value: bool

    def is_satisfied_by(self, prop: Property) -> bool:
        return self.value


TRUE = _Const(True)
FALSE = _Const(False)
_PROP = object()  # composites never touch the property when children are stubs


def _sat(spec: Specification) -> bool:
    return spec.is_satisfied_by(_PROP)  # type: ignore[arg-type]


def test_and_requires_all() -> None:
    assert _sat(AndSpecification((TRUE, TRUE))) is True
    assert _sat(AndSpecification((TRUE, FALSE))) is False


def test_or_requires_any() -> None:
    assert _sat(OrSpecification((FALSE, TRUE))) is True
    assert _sat(OrSpecification((FALSE, FALSE))) is False


def test_not_inverts() -> None:
    assert _sat(NotSpecification(TRUE)) is False
    assert _sat(NotSpecification(FALSE)) is True


def test_none_group_is_not_of_or() -> None:
    # GroupOperator.NONE compiles to NotSpecification(OrSpecification(...))
    none_group = NotSpecification(OrSpecification((FALSE, FALSE)))
    assert _sat(none_group) is True
    none_group_with_hit = NotSpecification(OrSpecification((FALSE, TRUE)))
    assert _sat(none_group_with_hit) is False


def test_nested_composites() -> None:
    spec = AndSpecification((TRUE, OrSpecification((FALSE, TRUE)), NotSpecification(FALSE)))
    assert _sat(spec) is True
