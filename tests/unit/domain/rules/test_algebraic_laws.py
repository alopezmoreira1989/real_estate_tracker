"""Property-based tests for the specification algebra (Hypothesis)."""

from dataclasses import dataclass

from hypothesis import given
from hypothesis import strategies as st

from real_estate.domain.model import Property
from real_estate.domain.rules.specification import (
    AndSpecification,
    NotSpecification,
    OrSpecification,
)


@dataclass(frozen=True)
class _Const:
    value: bool

    def is_satisfied_by(self, prop: Property) -> bool:
        return self.value


_PROP = object()  # _Const ignores the property


def _ev(spec: object) -> bool:
    return spec.is_satisfied_by(_PROP)  # type: ignore[attr-defined]


@given(st.booleans())
def test_double_negation_is_identity(b):
    s = _Const(b)
    assert _ev(NotSpecification(NotSpecification(s))) == b


@given(st.booleans(), st.booleans())
def test_de_morgan_and(a, b):
    sa, sb = _Const(a), _Const(b)
    left = NotSpecification(AndSpecification((sa, sb)))
    right = OrSpecification((NotSpecification(sa), NotSpecification(sb)))
    assert _ev(left) == _ev(right)


@given(st.booleans(), st.booleans())
def test_de_morgan_or(a, b):
    sa, sb = _Const(a), _Const(b)
    left = NotSpecification(OrSpecification((sa, sb)))
    right = AndSpecification((NotSpecification(sa), NotSpecification(sb)))
    assert _ev(left) == _ev(right)


@given(st.booleans())
def test_identities(b):
    s = _Const(b)
    assert _ev(AndSpecification((s, _Const(True)))) == b
    assert _ev(OrSpecification((s, _Const(False)))) == b
