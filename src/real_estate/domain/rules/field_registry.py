"""Field Registry — fields are data, not columns (driver D1).

A leaf condition names a canonical field; a :class:`FieldDescriptor` knows that
field's type, how to extract its value from a :class:`Property`, and which
operators are valid for it. Adding a new filter = registering one descriptor —
no engine change (doc 04 §3).

Extractors return the same primitive representation stored in the condition tree
(province code ``"36"``, enum value ``"LAND"``, ``Decimal`` amounts, ``int``
counts, ``bool``/``None`` flags), so operator strategies compare like-for-like.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from real_estate.domain.errors import InvalidConditionError
from real_estate.domain.model.conditions import Operator
from real_estate.domain.model.property import Property


class FieldType(Enum):
    NUMERIC = auto()
    MONEY = auto()
    AREA = auto()
    ENUM = auto()
    TEXT = auto()
    BOOL = auto()
    GEO = auto()


_ENUM_OPS = frozenset(
    {Operator.EQ, Operator.NEQ, Operator.IN, Operator.NOT_IN, Operator.EXISTS, Operator.NOT_EXISTS}
)
_NUMERIC_OPS = frozenset(
    {
        Operator.EQ,
        Operator.NEQ,
        Operator.LT,
        Operator.LTE,
        Operator.GT,
        Operator.GTE,
        Operator.BETWEEN,
        Operator.EXISTS,
        Operator.NOT_EXISTS,
    }
)
_TEXT_OPS = frozenset(
    {
        Operator.EQ,
        Operator.NEQ,
        Operator.CONTAINS,
        Operator.NOT_CONTAINS,
        Operator.IN,
        Operator.NOT_IN,
        Operator.EXISTS,
        Operator.NOT_EXISTS,
    }
)
_BOOL_OPS = frozenset({Operator.EQ, Operator.NEQ, Operator.EXISTS, Operator.NOT_EXISTS})

_OPS_BY_TYPE: dict[FieldType, frozenset[Operator]] = {
    FieldType.NUMERIC: _NUMERIC_OPS,
    FieldType.MONEY: _NUMERIC_OPS,
    FieldType.AREA: _NUMERIC_OPS,
    FieldType.ENUM: _ENUM_OPS,
    FieldType.TEXT: _TEXT_OPS,
    FieldType.BOOL: _BOOL_OPS,
    FieldType.GEO: frozenset(),
}


@dataclass(frozen=True, slots=True)
class FieldDescriptor:
    """Describes one queryable canonical field."""

    key: str
    field_type: FieldType
    extract: Callable[[Property], Any]
    allowed_operators: frozenset[Operator]


class FieldRegistry:
    """A lookup of registered :class:`FieldDescriptor` keyed by field key."""

    def __init__(self) -> None:
        self._by_key: dict[str, FieldDescriptor] = {}

    def register(self, descriptor: FieldDescriptor) -> None:
        if descriptor.key in self._by_key:
            raise ValueError(f"field already registered: {descriptor.key}")
        self._by_key[descriptor.key] = descriptor

    def get(self, key: str) -> FieldDescriptor:
        try:
            return self._by_key[key]
        except KeyError as exc:
            raise InvalidConditionError(f"unknown field: {key}") from exc

    def __contains__(self, key: str) -> bool:
        return key in self._by_key


_FEATURE_FLAGS = (
    "has_lift",
    "has_terrace",
    "has_garden",
    "has_parking",
    "has_pool",
    "is_new_build",
)


def _feature_extractor(flag: str) -> Callable[[Property], Any]:
    return lambda prop: prop.features.get(flag)


def default_registry() -> FieldRegistry:
    """Registry of the MVP canonical fields."""
    registry = FieldRegistry()

    def add(key: str, field_type: FieldType, extract: Callable[[Property], Any]) -> None:
        registry.register(FieldDescriptor(key, field_type, extract, _OPS_BY_TYPE[field_type]))

    add("province", FieldType.ENUM, lambda p: p.location.province.code)
    add(
        "municipality",
        FieldType.ENUM,
        lambda p: p.location.municipality.ine_code if p.location.municipality else None,
    )
    add("property_type", FieldType.ENUM, lambda p: p.property_type.value)
    add("land_type", FieldType.ENUM, lambda p: p.land_type.value if p.land_type else None)
    add("listing_type", FieldType.ENUM, lambda p: p.listing_type.value)
    add("status", FieldType.ENUM, lambda p: p.status.value)

    add("price", FieldType.MONEY, lambda p: p.price.amount if p.price else None)
    add(
        "price_per_m2",
        FieldType.MONEY,
        lambda p: p.price_per_m2.amount if p.price_per_m2 else None,
    )
    add("area", FieldType.AREA, lambda p: p.area.square_meters if p.area else None)
    add(
        "plot_area",
        FieldType.AREA,
        lambda p: p.plot_area.square_meters if p.plot_area else None,
    )
    add("rooms", FieldType.NUMERIC, lambda p: p.rooms)
    add("bathrooms", FieldType.NUMERIC, lambda p: p.bathrooms)

    add("postal_code", FieldType.TEXT, lambda p: p.location.postal_code)
    add("district", FieldType.TEXT, lambda p: p.location.district)
    add("title", FieldType.TEXT, lambda p: p.title)
    add("description", FieldType.TEXT, lambda p: p.description)

    for flag in _FEATURE_FLAGS:
        add(f"features.{flag}", FieldType.BOOL, _feature_extractor(flag))

    return registry
