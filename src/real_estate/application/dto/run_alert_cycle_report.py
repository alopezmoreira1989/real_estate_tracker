"""Summary of one RunAlertCycle run."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RunAlertCycleReport:
    """Counts from one alert cycle — enough to log/report without exposing
    internal state (Phase 7's operational CLI will surface this)."""

    queries_planned: int
    queries_succeeded: int
    queries_failed: int
    matches_created: int
