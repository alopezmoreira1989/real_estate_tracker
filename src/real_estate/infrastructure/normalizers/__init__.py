"""Normalizers: per-portal RawListing -> Property, plus shared parsing/vocabulary helpers.

``default_registry()`` is the one place that lists which portals exist —
adding a portal means adding one line here plus that portal's own package,
never touching :class:`NormalizerRegistry` or :class:`BaseNormalizer`.
"""

from real_estate.infrastructure.normalizers.idealista import IdealistaNormalizer
from real_estate.infrastructure.normalizers.registry import NormalizerRegistry

__all__ = ["NormalizerRegistry", "default_registry"]


def default_registry() -> NormalizerRegistry:
    """Build a :class:`NormalizerRegistry` with every known portal registered."""
    registry = NormalizerRegistry()
    registry.register(IdealistaNormalizer())
    return registry
