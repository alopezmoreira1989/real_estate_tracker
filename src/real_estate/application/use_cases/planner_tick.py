"""PlannerTick — the scheduler's/CLI's entry point into one alert cycle.

Lists the due set (doc06 §5: active alerts whose last_run_at + frequency has
elapsed) and delegates to RunAlertCycle. This is the *only* orchestration
Phase 7 adds on top of Phase 5's use-case — a single, tested seam reused by
both the scheduled planner job and the CLI's `run-cycle` command.
"""

from __future__ import annotations

from collections.abc import Callable

from real_estate.application.dto import RunAlertCycleReport
from real_estate.application.ports import Clock
from real_estate.application.use_cases.run_alert_cycle import RunAlertCycle
from real_estate.domain.ports import UnitOfWork


class PlannerTick:
    """Runs one cycle over the currently-due alerts."""

    def __init__(
        self,
        *,
        uow_factory: Callable[[], UnitOfWork],
        run_alert_cycle: RunAlertCycle,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._run_alert_cycle = run_alert_cycle
        self._clock = clock

    def run(self) -> RunAlertCycleReport:
        with self._uow_factory() as uow:
            due = uow.alerts.list_due(now=self._clock.now())
        return self._run_alert_cycle.run(due)
