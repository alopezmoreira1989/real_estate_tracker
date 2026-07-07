from real_estate.infrastructure.config.portal_capabilities import PORTAL_CAPABILITIES


def test_idealista_declares_the_fields_its_scraper_actually_supports() -> None:
    capabilities = PORTAL_CAPABILITIES["idealista"]

    assert capabilities.portal_slug == "idealista"
    assert capabilities.pushable_fields == frozenset(
        {"province", "property_type", "listing_type", "price"}
    )


def test_idealista_declares_positive_politeness_settings() -> None:
    capabilities = PORTAL_CAPABILITIES["idealista"]

    assert capabilities.rate_limit_per_second > 0
    assert capabilities.circuit_breaker_failure_threshold >= 1
    assert capabilities.circuit_breaker_cooldown_seconds > 0
