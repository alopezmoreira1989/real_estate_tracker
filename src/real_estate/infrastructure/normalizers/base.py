"""BaseNormalizer: the four-step normalization pipeline.

Field mapping -> value parsing -> vocabulary mapping -> derivation & assembly
(docs/architecture/05-normalization.md §2). Concrete portal normalizers
subclass this and supply only ``portal_slug`` and ``field_map``; adding a
portal never means editing this pipeline (OCP), only registering a new
subclass (``infrastructure/normalizers/registry.py``).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from real_estate.domain.model.features import Features
from real_estate.domain.model.identifiers import PropertyId
from real_estate.domain.model.location import Location
from real_estate.domain.model.media import Media
from real_estate.domain.model.property import Property
from real_estate.domain.ports.normalizer import NormalizationIssue, NormalizationResult
from real_estate.domain.ports.scraper import RawListing
from real_estate.domain.vocabulary import ListingStatus, ListingType, PropertyType, Province
from real_estate.infrastructure.normalizers.parsers import (
    parse_area,
    parse_bool,
    parse_int,
    parse_money,
)
from real_estate.infrastructure.normalizers.vocabularies import (
    resolve_land_type,
    resolve_listing_type,
    resolve_property_type,
    resolve_province,
)

# Fixed namespace for deterministic PropertyIds: the same (portal, external_id)
# always yields the same id, so re-normalizing a listing is idempotent ahead of
# the real upsert-by-natural-key wiring in Phase 5.
_PROPERTY_ID_NAMESPACE = uuid.UUID("2b7a6b3e-6c1a-4f0a-9d3a-9f6e1d9c9a10")

_FEATURES_PREFIX = "features."
_MEDIA_PREFIX = "media."

_FEATURE_KEYS = (
    "has_lift",
    "has_terrace",
    "has_garden",
    "has_parking",
    "has_pool",
    "is_new_build",
)


class BaseNormalizer:
    """Composes the four-step normalization pipeline for one portal.

    Subclasses set ``portal_slug`` and ``field_map`` (portal raw key ->
    canonical field name, using a ``"features."``/``"media."`` prefix for
    fields that belong under :class:`Features`/:class:`Media`).
    """

    portal_slug: str
    field_map: Mapping[str, str]

    def normalize(self, raw: RawListing) -> NormalizationResult:
        issues: list[NormalizationIssue] = []
        scalars, features_raw, media_raw = self._map_fields(raw.raw)
        parsed = self._parse_values(scalars, issues)
        canonical = self._map_vocabulary(parsed, issues)
        return self._assemble(raw, canonical, features_raw, media_raw, issues)

    def _map_fields(
        self, raw: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        scalars: dict[str, Any] = {}
        features_raw: dict[str, Any] = {}
        media_raw: dict[str, Any] = {}
        for portal_key, canonical_field in self.field_map.items():
            if portal_key not in raw:
                continue
            value = raw[portal_key]
            if canonical_field.startswith(_FEATURES_PREFIX):
                features_raw[canonical_field.removeprefix(_FEATURES_PREFIX)] = value
            elif canonical_field.startswith(_MEDIA_PREFIX):
                media_raw[canonical_field.removeprefix(_MEDIA_PREFIX)] = value
            else:
                scalars[canonical_field] = value
        return scalars, features_raw, media_raw

    def _parse_values(
        self, scalars: Mapping[str, Any], issues: list[NormalizationIssue]
    ) -> dict[str, Any]:
        parsed: dict[str, Any] = dict(scalars)
        parsed["price"] = self._parsed(parse_money, parsed.get("price"), "price", issues)
        parsed["area"] = self._parsed(parse_area, parsed.get("area"), "area", issues)
        parsed["plot_area"] = self._parsed(parse_area, parsed.get("plot_area"), "plot_area", issues)
        parsed["rooms"] = self._parsed(parse_int, parsed.get("rooms"), "rooms", issues)
        parsed["bathrooms"] = self._parsed(parse_int, parsed.get("bathrooms"), "bathrooms", issues)
        return parsed

    @staticmethod
    def _parsed(
        parser: Any, raw_value: Any, field_name: str, issues: list[NormalizationIssue]
    ) -> Any:
        if raw_value is None:
            return None
        text = str(raw_value)
        value = parser(text)
        if value is None:
            issues.append(
                NormalizationIssue(
                    field=field_name, message="could not parse value", raw_value=text
                )
            )
        return value

    def _map_vocabulary(
        self, parsed: Mapping[str, Any], issues: list[NormalizationIssue]
    ) -> dict[str, Any]:
        canonical = dict(parsed)
        canonical["property_type"] = self._resolved(
            resolve_property_type,
            canonical.get("property_type"),
            PropertyType.OTHER,
            "property_type",
            issues,
        )
        canonical["listing_type"] = self._resolved(
            resolve_listing_type,
            canonical.get("listing_type"),
            ListingType.OTHER,
            "listing_type",
            issues,
        )
        canonical["province"] = self._resolved(
            resolve_province, canonical.get("province"), Province.UNKNOWN, "province", issues
        )
        if canonical["property_type"] is PropertyType.LAND:
            canonical["land_type"] = self._resolved(
                resolve_land_type, canonical.get("land_type"), None, "land_type", issues
            )
        else:
            canonical["land_type"] = None
        return canonical

    @staticmethod
    def _resolved(
        resolver: Any,
        raw_value: Any,
        fallback: Any,
        field_name: str,
        issues: list[NormalizationIssue],
    ) -> Any:
        text = str(raw_value) if raw_value is not None else None
        value = resolver(text)
        if fallback is not None and value is fallback and text is not None:
            issues.append(
                NormalizationIssue(field=field_name, message="unmapped vocabulary", raw_value=text)
            )
        return value

    def _assemble(
        self,
        raw: RawListing,
        canonical: Mapping[str, Any],
        features_raw: Mapping[str, Any],
        media_raw: Mapping[str, Any],
        issues: list[NormalizationIssue],
    ) -> NormalizationResult:
        features = Features(**{key: parse_bool(features_raw.get(key)) for key in _FEATURE_KEYS})
        media = Media(
            images=tuple(self._valid_urls(media_raw.get("images"), "images", issues)),
            videos=tuple(self._valid_urls(media_raw.get("videos"), "videos", issues)),
        )
        location = Location(province=canonical.get("province") or Province.UNKNOWN)

        try:
            prop = Property(
                id=PropertyId(
                    uuid.uuid5(_PROPERTY_ID_NAMESPACE, f"{raw.portal_slug}:{raw.external_id}")
                ),
                listing_type=canonical.get("listing_type") or ListingType.OTHER,
                property_type=canonical.get("property_type") or PropertyType.OTHER,
                location=location,
                title=str(canonical.get("title") or ""),
                status=ListingStatus.ACTIVE,
                land_type=canonical.get("land_type"),
                price=canonical.get("price"),
                area=canonical.get("area"),
                plot_area=canonical.get("plot_area"),
                rooms=canonical.get("rooms"),
                bathrooms=canonical.get("bathrooms"),
                features=features,
                description=str(canonical.get("description") or ""),
                media=media,
                published_at=None,
            )
        except (ValueError, TypeError) as exc:
            issues.append(
                NormalizationIssue(field="property", message=f"could not construct Property: {exc}")
            )
            return NormalizationResult(property=None, issues=tuple(issues))

        return NormalizationResult(property=prop, issues=tuple(issues))

    @staticmethod
    def _valid_urls(value: Any, field_name: str, issues: list[NormalizationIssue]) -> list[str]:
        if not value:
            return []
        urls: list[str] = []
        for url in value:
            if isinstance(url, str) and url.startswith(("http://", "https://")):
                urls.append(url)
            else:
                issues.append(
                    NormalizationIssue(
                        field=field_name, message="invalid media URL", raw_value=str(url)
                    )
                )
        return urls
