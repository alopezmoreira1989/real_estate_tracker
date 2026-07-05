"""Listing-level controlled vocabularies: what kind of offer, and its state."""

from enum import StrEnum


class ListingType(StrEnum):
    """The kind of transaction a listing offers."""

    SALE = "SALE"
    RENT = "RENT"
    AUCTION = "AUCTION"
    TRANSFER = "TRANSFER"
    OTHER = "OTHER"


class ListingStatus(StrEnum):
    """Lifecycle state of a listing as last observed.

    ``UNKNOWN`` is used when a portal does not expose the state — normalization
    never drops a listing for lack of it (CLAUDE.md §12).
    """

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    UNKNOWN = "UNKNOWN"
