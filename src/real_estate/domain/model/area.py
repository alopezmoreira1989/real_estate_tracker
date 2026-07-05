"""Area and price-per-square-metre value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from functools import total_ordering

from real_estate.domain.model.money import Money
from real_estate.domain.vocabulary import Currency


@total_ordering
@dataclass(frozen=True, slots=True)
class Area:
    """A positive surface area expressed in square metres."""

    square_meters: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.square_meters, Decimal):
            raise TypeError("Area.square_meters must be a Decimal")
        if self.square_meters <= 0:
            raise ValueError("Area.square_meters must be positive")

    def __lt__(self, other: Area) -> bool:
        return self.square_meters < other.square_meters


@total_ordering
@dataclass(frozen=True, slots=True)
class PricePerM2:
    """A positive price per square metre, in a single currency.

    Derived from a :class:`Money` price and an :class:`Area`; the calculation
    lives here so units are guaranteed consistent.
    """

    amount: Decimal
    currency: Currency = field(default=Currency.EUR)

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError("PricePerM2.amount must be a Decimal")
        if self.amount <= 0:
            raise ValueError("PricePerM2.amount must be positive")

    @classmethod
    def from_price_and_area(cls, price: Money, area: Area) -> PricePerM2:
        """Compute price/m² from a price and an area (same currency preserved)."""
        return cls(price.amount / area.square_meters, price.currency)

    def __lt__(self, other: PricePerM2) -> bool:
        if self.currency is not other.currency:
            raise ValueError(
                f"Cannot compare price/m² across currencies: {self.currency} vs {other.currency}"
            )
        return self.amount < other.amount
