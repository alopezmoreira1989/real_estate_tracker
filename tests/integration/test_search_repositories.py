"""Integration tests: the Phase 5 search-support repositories (match,
portal listing, search cache, search execution) and PriceHistory-on-change,
against a real (temp) SQLite DB.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from real_estate.domain.model import (
    AlertCondition,
    AlertId,
    Area,
    Features,
    GroupOperator,
    Location,
    Media,
    Money,
    Operator,
    Property,
    PropertyId,
    RuleGroup,
    SearchAlert,
    UserId,
)
from real_estate.domain.model.match import AlertMatch
from real_estate.domain.ports import SearchExecutionStatus
from real_estate.domain.vocabulary import ListingStatus, ListingType, PropertyType, Province
from real_estate.infrastructure.persistence.models.orm import PriceHistoryModel, UserModel

NOW = datetime(2026, 7, 4, 12, 0)  # naive: SQLite does not persist tz


def _property(price: Decimal = Decimal("60000")) -> Property:
    return Property(
        id=PropertyId(uuid4()),
        listing_type=ListingType.SALE,
        property_type=PropertyType.LAND,
        location=Location(province=Province.PONTEVEDRA),
        title="Urbanizable plot near water",
        status=ListingStatus.ACTIVE,
        price=Money(price),
        area=Area(Decimal("3000")),
        features=Features(),
        media=Media(),
    )


def _alert(user_id: UserId) -> SearchAlert:
    return SearchAlert.create(
        id=AlertId(uuid4()),
        user_id=user_id,
        name="Land in Pontevedra",
        portal_slugs=frozenset({"idealista"}),
        frequency_seconds=900,
        conditions=RuleGroup(GroupOperator.ALL, (AlertCondition("province", Operator.EQ, "36"),)),
        now=NOW,
    )


def test_match_add_if_new_is_idempotent(persistence) -> None:
    prop = _property()
    alert = _alert(persistence.user_id)
    with persistence.new_uow() as uow:
        uow.properties.add(prop)
        uow.alerts.add(alert)
        uow.commit()

    match = AlertMatch(alert_id=alert.id, property_id=prop.id, matched_at=NOW)
    with persistence.new_uow() as uow:
        first = uow.matches.add_if_new(match)
        second = uow.matches.add_if_new(match)
        uow.commit()

    assert first is not None
    assert second is None


def test_match_list_recent_for_user_is_scoped_and_ordered_newest_first(persistence) -> None:
    alert = _alert(persistence.user_id)
    prop_a = _property()
    prop_b = _property()
    other_user_id = UserId(uuid4())
    other_user_alert = _alert(other_user_id)
    other_prop = _property()
    with persistence.new_uow() as uow:
        uow._session.add(  # noqa: SLF001
            UserModel(
                id=other_user_id,
                email=f"{other_user_id}@example.test",
                display_name="Other User",
                created_at=NOW,
            )
        )
        uow.properties.add(prop_a)
        uow.properties.add(prop_b)
        uow.properties.add(other_prop)
        uow.alerts.add(alert)
        uow.alerts.add(other_user_alert)
        uow.commit()

    with persistence.new_uow() as uow:
        uow.matches.add_if_new(AlertMatch(alert_id=alert.id, property_id=prop_a.id, matched_at=NOW))
        uow.matches.add_if_new(
            AlertMatch(
                alert_id=alert.id, property_id=prop_b.id, matched_at=NOW + timedelta(minutes=5)
            )
        )
        uow.matches.add_if_new(
            AlertMatch(alert_id=other_user_alert.id, property_id=other_prop.id, matched_at=NOW)
        )
        uow.commit()

    with persistence.new_uow() as uow:
        recent = uow.matches.list_recent_for_user(persistence.user_id, limit=10)

    assert [m.property_id for m in recent] == [prop_b.id, prop_a.id]


def test_portal_listing_find_unchanged_property_id(persistence) -> None:
    prop = _property()
    with persistence.new_uow() as uow:
        uow.properties.add(prop)
        assert (
            uow.portal_listings.find_unchanged_property_id("idealista", "ext-1", "hash-a") is None
        )
        uow.portal_listings.upsert(
            portal_slug="idealista",
            external_id="ext-1",
            property_id=prop.id,
            url="https://idealista.com/ext-1",
            raw_payload={"precio": "60.000 €"},
            content_hash="hash-a",
            scraped_at=NOW,
        )
        uow.commit()

    with persistence.new_uow() as uow:
        # same hash -> unchanged, returns the linked property id
        assert (
            uow.portal_listings.find_unchanged_property_id("idealista", "ext-1", "hash-a")
            == prop.id
        )
        # different hash -> changed, needs re-normalizing
        assert (
            uow.portal_listings.find_unchanged_property_id("idealista", "ext-1", "hash-b") is None
        )


def test_portal_listing_upsert_updates_in_place_not_duplicated(persistence) -> None:
    prop = _property()
    with persistence.new_uow() as uow:
        uow.properties.add(prop)
        uow.portal_listings.upsert(
            portal_slug="idealista",
            external_id="ext-2",
            property_id=prop.id,
            url="https://idealista.com/ext-2",
            raw_payload={},
            content_hash="hash-a",
            scraped_at=NOW,
        )
        uow.commit()

    with persistence.new_uow() as uow:
        uow.portal_listings.upsert(
            portal_slug="idealista",
            external_id="ext-2",
            property_id=prop.id,
            url="https://idealista.com/ext-2",
            raw_payload={},
            content_hash="hash-b",
            scraped_at=NOW,
        )
        uow.commit()

    with persistence.new_uow() as uow:
        assert (
            uow.portal_listings.find_unchanged_property_id("idealista", "ext-2", "hash-b")
            == prop.id
        )
        assert (
            uow.portal_listings.find_unchanged_property_id("idealista", "ext-2", "hash-a") is None
        )


def test_match_get_returns_the_persisted_match(persistence) -> None:
    prop = _property()
    alert = _alert(persistence.user_id)
    with persistence.new_uow() as uow:
        uow.properties.add(prop)
        uow.alerts.add(alert)
        uow.commit()

    match = AlertMatch(alert_id=alert.id, property_id=prop.id, matched_at=NOW)
    with persistence.new_uow() as uow:
        match_id = uow.matches.add_if_new(match)
        uow.commit()

    with persistence.new_uow() as uow:
        fetched = uow.matches.get(match_id)

    assert fetched is not None
    assert fetched.alert_id == alert.id
    assert fetched.property_id == prop.id


def test_portal_listing_get_url_for_property(persistence) -> None:
    prop = _property()
    with persistence.new_uow() as uow:
        uow.properties.add(prop)
        assert uow.portal_listings.get_url_for_property(prop.id) is None
        uow.portal_listings.upsert(
            portal_slug="idealista",
            external_id="ext-3",
            property_id=prop.id,
            url="https://idealista.com/ext-3",
            raw_payload={},
            content_hash="hash-a",
            scraped_at=NOW,
        )
        uow.commit()

    with persistence.new_uow() as uow:
        assert uow.portal_listings.get_url_for_property(prop.id) == "https://idealista.com/ext-3"


def test_search_cache_hit_within_ttl(persistence) -> None:
    property_ids = [PropertyId(uuid4())]
    with persistence.new_uow() as uow:
        uow.search_cache.put("sig-1", "idealista", property_ids, fetched_at=NOW, ttl_seconds=900)
        uow.commit()

    with persistence.new_uow() as uow:
        cached = uow.search_cache.get("sig-1", now=NOW + timedelta(minutes=5))

    assert cached == property_ids


def test_search_cache_miss_after_ttl_expires(persistence) -> None:
    property_ids = [PropertyId(uuid4())]
    with persistence.new_uow() as uow:
        uow.search_cache.put("sig-2", "idealista", property_ids, fetched_at=NOW, ttl_seconds=60)
        uow.commit()

    with persistence.new_uow() as uow:
        cached = uow.search_cache.get("sig-2", now=NOW + timedelta(minutes=5))

    assert cached is None


def test_search_cache_miss_for_unknown_signature(persistence) -> None:
    with persistence.new_uow() as uow:
        assert uow.search_cache.get("nonexistent", now=NOW) is None


def test_search_execution_record_does_not_raise(persistence) -> None:
    with persistence.new_uow() as uow:
        uow.search_executions.record(
            portal_slug="idealista",
            query_signature="sig-3",
            status=SearchExecutionStatus.SUCCESS,
            listings_found=5,
            listings_new=2,
            normalization_issues=1,
            error=None,
            started_at=NOW,
            finished_at=NOW + timedelta(seconds=3),
        )
        uow.commit()


def test_search_execution_list_recent_returns_newest_first(persistence) -> None:
    with persistence.new_uow() as uow:
        uow.search_executions.record(
            portal_slug="idealista",
            query_signature="sig-old",
            status=SearchExecutionStatus.SUCCESS,
            listings_found=3,
            listings_new=1,
            normalization_issues=0,
            error=None,
            started_at=NOW,
            finished_at=NOW + timedelta(seconds=1),
        )
        uow.search_executions.record(
            portal_slug="idealista",
            query_signature="sig-new",
            status=SearchExecutionStatus.FAILED,
            listings_found=0,
            listings_new=0,
            normalization_issues=0,
            error="portal unreachable",
            started_at=NOW + timedelta(minutes=5),
            finished_at=NOW + timedelta(minutes=5, seconds=1),
        )
        uow.commit()

    with persistence.new_uow() as uow:
        recent = uow.search_executions.list_recent(limit=10)

    assert [e.query_signature for e in recent] == ["sig-new", "sig-old"]
    assert recent[0].status is SearchExecutionStatus.FAILED
    assert recent[0].error == "portal unreachable"
    assert recent[0].portal_slug == "idealista"


def test_search_execution_list_recent_respects_limit(persistence) -> None:
    with persistence.new_uow() as uow:
        for i in range(3):
            uow.search_executions.record(
                portal_slug="idealista",
                query_signature=f"sig-{i}",
                status=SearchExecutionStatus.SUCCESS,
                listings_found=1,
                listings_new=1,
                normalization_issues=0,
                error=None,
                started_at=NOW + timedelta(minutes=i),
                finished_at=NOW + timedelta(minutes=i, seconds=1),
            )
        uow.commit()

    with persistence.new_uow() as uow:
        recent = uow.search_executions.list_recent(limit=2)

    assert len(recent) == 2


def _price_history_count(uow, property_id: PropertyId) -> int:
    rows = (
        uow._session.execute(  # noqa: SLF001
            select(PriceHistoryModel).where(PriceHistoryModel.property_id == property_id)
        )
        .scalars()
        .all()
    )
    return len(rows)


def test_price_history_row_added_only_when_price_changes(persistence) -> None:
    prop = _property(price=Decimal("60000"))

    with persistence.new_uow() as uow:
        uow.properties.add(prop)
        uow.commit()

    with persistence.new_uow() as uow:
        uow.properties.add(prop)  # re-scraped, same price
        uow.commit()

    with persistence.new_uow() as uow:
        assert _price_history_count(uow, prop.id) == 1

    changed = replace(prop, price=Money(Decimal("65000")))
    with persistence.new_uow() as uow:
        uow.properties.add(changed)
        uow.commit()

    with persistence.new_uow() as uow:
        assert _price_history_count(uow, prop.id) == 2
