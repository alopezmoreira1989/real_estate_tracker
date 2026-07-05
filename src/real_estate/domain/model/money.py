"""Money value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from functools import total_ordering

from real_estate.domain.vocabulary import Currency


@total_ordering
@dataclass(frozen=True, slots=True)
class Money:
    """A non-negative monetary amount in a single currency.

    Arithmetic and comparison are only valid within the same currency; mixing
    currencies raises, so a bug can never silently compare euros to anything
    else (docs/architecture/02-domain-model.md §2).
    """

    amount: Decimal
    currency: Currency = field(default=Currency.EUR)

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError("Money.amount must be a Decimal")
        if self.amount < 0:
            raise ValueError("Money.amount must not be negative")

    def _check_same_currency(self, other: Money) -> None:
        if self.currency is not other.currency:
            raise ValueError(
                f"Cannot operate across currencies: {self.currency} vs {other.currency}"
            )

    def __add__(self, other: Money) -> Money:
        self._check_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._check_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __lt__(self, other: Money) -> bool:
        self._check_same_currency(other)
        return self.amount < other.amount
