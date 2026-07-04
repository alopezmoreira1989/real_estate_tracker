"""Property features value object (tri-state booleans)."""

from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True, slots=True)
class Features:
    """Common boolean amenities of a property.

    Each flag is tri-state: ``True``/``False`` when the portal stated it, and
    ``None`` when unknown. "Unknown" must stay distinct from an explicit "no"
    so the rule engine does not treat missing data as a negative
    (docs/architecture/02-domain-model.md §2).
    """

    has_lift: bool | None = None
    has_terrace: bool | None = None
    has_garden: bool | None = None
    has_parking: bool | None = None
    has_pool: bool | None = None
    is_new_build: bool | None = None

    def get(self, name: str) -> bool | None:
        """Return a feature flag by name, or ``None`` if the feature is unknown.

        Raises :class:`KeyError` if ``name`` is not a defined feature.
        """
        valid = {f.name for f in fields(self)}
        if name not in valid:
            raise KeyError(name)
        value: bool | None = getattr(self, name)
        return value
