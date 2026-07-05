"""Currency controlled vocabulary."""

from enum import StrEnum


class Currency(StrEnum):
    """ISO-4217 currency codes the platform understands.

    EUR is the only currency in use for Spanish portals; the enum is left open
    for extension (OCP) without changing callers.
    """

    EUR = "EUR"
