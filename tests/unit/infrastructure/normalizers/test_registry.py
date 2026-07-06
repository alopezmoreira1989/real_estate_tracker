import pytest

from real_estate.infrastructure.normalizers import default_registry
from real_estate.infrastructure.normalizers.idealista import IdealistaNormalizer
from real_estate.infrastructure.normalizers.registry import NormalizerRegistry, UnknownPortalError


def test_register_and_lookup_by_portal_slug() -> None:
    registry = NormalizerRegistry()
    normalizer = IdealistaNormalizer()

    registry.register(normalizer)

    assert registry.for_portal("idealista") is normalizer


def test_unknown_portal_raises() -> None:
    registry = NormalizerRegistry()

    with pytest.raises(UnknownPortalError):
        registry.for_portal("nonexistent")


def test_default_registry_includes_idealista() -> None:
    registry = default_registry()

    normalizer = registry.for_portal("idealista")

    assert isinstance(normalizer, IdealistaNormalizer)
