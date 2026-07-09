"""RunAlertCycle — orchestrates one scheduler tick end-to-end.

plan -> for each deduplicated query: cache-or-scrape, content-hash-or-
normalize, upsert -> evaluate every alert sharing that query -> persist
matches and enqueue notifications for genuinely new ones (docs/architecture/
08-sequence-diagrams.md §2). A scraper failure for one query is isolated
(recorded, then skipped) so the cycle continues with every other query
(doc08 §4, driver D7).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from typing import Any

from real_estate.application.dto import PlannedQuery, RunAlertCycleReport
from real_estate.application.ports import Clock
from real_estate.application.services.search_planner import SearchPlanner
from real_estate.domain.model.alert import SearchAlert
from real_estate.domain.model.identifiers import PropertyId
from real_estate.domain.model.property import Property
from real_estate.domain.ports import Normalizer, Scraper, SearchExecutionStatus, UnitOfWork
from real_estate.domain.ports.scraper import ScraperError
from real_estate.domain.services.alert_engine import AlertEngine


class RunAlertCycle:
    """Runs one alert cycle: scrape (deduplicated), normalize, evaluate, persist matches."""

    def __init__(
        self,
        *,
        uow_factory: Callable[[], UnitOfWork],
        planner: SearchPlanner,
        scraper_for_portal: Callable[[str], Scraper],
        normalizer_for_portal: Callable[[str], Normalizer],
        engine: AlertEngine,
        clock: Clock,
        cache_ttl_seconds: int = 900,
    ) -> None:
        self._uow_factory = uow_factory
        self._planner = planner
        self._scraper_for_portal = scraper_for_portal
        self._normalizer_for_portal = normalizer_for_portal
        self._engine = engine
        self._clock = clock
        self._cache_ttl_seconds = cache_ttl_seconds

    def run(self, due_alerts: Sequence[SearchAlert]) -> RunAlertCycleReport:
        planned_queries = self._planner.plan(due_alerts)
        succeeded = 0
        failed = 0
        matches_created = 0

        for planned in planned_queries:
            now = self._clock.now()
            with self._uow_factory() as uow:
                try:
                    property_ids = self._resolve_candidates(uow, planned, now)
                except ScraperError as exc:
                    uow.search_executions.record(
                        portal_slug=planned.portal_slug,
                        query_signature=planned.signature,
                        status=SearchExecutionStatus.FAILED,
                        listings_found=0,
                        listings_new=0,
                        error=str(exc),
                        started_at=now,
                        finished_at=self._clock.now(),
                    )
                    uow.commit()
                    failed += 1
                    continue  # isolate the failure; the cycle continues (D7, doc08 §4)

                candidates = self._load_candidates(uow, property_ids)
                matches_created += self._evaluate_and_persist(uow, planned.alerts, candidates, now)
                uow.commit()
                succeeded += 1

        return RunAlertCycleReport(
            queries_planned=len(planned_queries),
            queries_succeeded=succeeded,
            queries_failed=failed,
            matches_created=matches_created,
        )

    def _resolve_candidates(
        self, uow: UnitOfWork, planned: PlannedQuery, now: datetime
    ) -> list[PropertyId]:
        cached = uow.search_cache.get(planned.signature, now=now)
        if cached is not None:
            return list(cached)

        scraper = self._scraper_for_portal(planned.portal_slug)
        raw_listings = scraper.fetch(planned.query)  # raises ScraperError on failure

        normalizer = self._normalizer_for_portal(planned.portal_slug)
        property_ids: list[PropertyId] = []
        listings_new = 0
        for raw in raw_listings:
            content_hash = _content_hash(raw.raw)
            unchanged_id = uow.portal_listings.find_unchanged_property_id(
                raw.portal_slug, raw.external_id, content_hash
            )
            if unchanged_id is not None:
                property_ids.append(unchanged_id)
                continue

            result = normalizer.normalize(raw)
            if result.property is None:
                continue  # normalization fatally failed; skip this listing only

            uow.properties.add(result.property)
            uow.portal_listings.upsert(
                portal_slug=raw.portal_slug,
                external_id=raw.external_id,
                property_id=result.property.id,
                url=raw.url,
                raw_payload=raw.raw,
                content_hash=content_hash,
                scraped_at=raw.scraped_at,
            )
            property_ids.append(result.property.id)
            listings_new += 1

        uow.search_cache.put(
            planned.signature,
            planned.portal_slug,
            property_ids,
            fetched_at=now,
            ttl_seconds=self._cache_ttl_seconds,
        )
        uow.search_executions.record(
            portal_slug=planned.portal_slug,
            query_signature=planned.signature,
            status=SearchExecutionStatus.SUCCESS,
            listings_found=len(raw_listings),
            listings_new=listings_new,
            error=None,
            started_at=now,
            finished_at=self._clock.now(),
        )
        return property_ids

    @staticmethod
    def _load_candidates(uow: UnitOfWork, property_ids: Sequence[PropertyId]) -> list[Property]:
        candidates: list[Property] = []
        for property_id in property_ids:
            prop = uow.properties.get(property_id)
            if prop is not None:
                candidates.append(prop)
        return candidates

    def _evaluate_and_persist(
        self,
        uow: UnitOfWork,
        alerts: Sequence[SearchAlert],
        candidates: Sequence[Property],
        now: datetime,
    ) -> int:
        created = 0
        for alert in alerts:
            for match in self._engine.evaluate(alert, candidates, now=now):
                match_id = uow.matches.add_if_new(match)
                if match_id is not None:
                    created += 1
                    for channel in uow.notification_channels.list_enabled_for_user(alert.user_id):
                        uow.notifications.enqueue(match_id, channel.id, now=now)
            alert.mark_run(now=now)
            uow.alerts.add(alert)
        return created


def _content_hash(raw: Mapping[str, Any]) -> str:
    """Deterministic hash of a raw payload — detects "listing unchanged since
    last scrape" so it can be skipped instead of re-normalized (doc03, doc05 §2).
    """
    canonical = json.dumps(raw, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
