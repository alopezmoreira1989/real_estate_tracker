"""Selects the right Normalizer for a portal (docs/architecture/05-normalization.md §4).

The registry itself has no portal knowledge — it holds no switch statement and
no imports of any concrete normalizer. Portals are registered once, in
``infrastructure/normalizers/__init__.py::default_registry()``, so adding a
portal never means editing this class (OCP).
"""

from __future__ import annotations

from real_estate.domain.ports.normalizer import Normalizer


class UnknownPortalError(KeyError):
    """Raised when no normalizer is registered for a portal slug."""


class NormalizerRegistry:
    """Looks up a :class:`Normalizer` by portal slug."""

    def __init__(self) -> None:
        self._normalizers: dict[str, Normalizer] = {}

    def register(self, normalizer: Normalizer) -> None:
        self._normalizers[normalizer.portal_slug] = normalizer

    def for_portal(self, portal_slug: str) -> Normalizer:
        try:
            return self._normalizers[portal_slug]
        except KeyError:
            raise UnknownPortalError(
                f"no normalizer registered for portal {portal_slug!r}"
            ) from None
