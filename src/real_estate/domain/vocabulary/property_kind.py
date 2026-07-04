"""Property classification vocabularies: the kind of property and, for land,
its development classification."""

from enum import StrEnum


class PropertyType(StrEnum):
    """Canonical property type. Portal-specific labels map onto these.

    ``OTHER`` is the never-drop fallback for a type we could not classify; it is
    always accompanied by a logged normalization issue (CLAUDE.md §12).
    """

    FLAT = "FLAT"
    PENTHOUSE = "PENTHOUSE"
    DUPLEX = "DUPLEX"
    STUDIO = "STUDIO"
    HOUSE = "HOUSE"
    CHALET = "CHALET"
    LAND = "LAND"
    GARAGE = "GARAGE"
    STORAGE_ROOM = "STORAGE_ROOM"
    OFFICE = "OFFICE"
    COMMERCIAL = "COMMERCIAL"
    BUILDING = "BUILDING"
    OTHER = "OTHER"


class LandType(StrEnum):
    """Development classification for ``PropertyType.LAND``.

    ``UNKNOWN`` covers land whose classification a portal did not state.
    """

    URBAN = "URBAN"
    URBANIZABLE = "URBANIZABLE"
    RUSTIC = "RUSTIC"
    NON_DEVELOPABLE = "NON_DEVELOPABLE"
    UNKNOWN = "UNKNOWN"
