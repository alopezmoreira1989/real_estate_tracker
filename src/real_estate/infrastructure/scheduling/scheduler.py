"""APScheduler wiring: the due-set planner tick and the notification
dispatcher, each a single recurring job (doc06 §5) — never one timer per
alert. ``max_instances=1`` + ``coalesce=True`` are what make "single planner
job" concrete: a slow tick can never overlap the next one, and a missed tick
collapses into the next run instead of queueing up a backlog of catch-up runs.
"""

from __future__ import annotations

from collections.abc import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

_PLANNER_JOB_ID = "planner"
_DISPATCHER_JOB_ID = "dispatcher"


def build_scheduler(
    *,
    planner_tick: Callable[[], object],
    dispatch_notifications: Callable[[], object],
    planner_interval_seconds: int,
    planner_jitter_seconds: int,
    dispatcher_interval_seconds: int,
) -> BackgroundScheduler:
    """Build (but do not start) a scheduler with the planner and dispatcher jobs registered."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        planner_tick,
        trigger=IntervalTrigger(seconds=planner_interval_seconds, jitter=planner_jitter_seconds),
        id=_PLANNER_JOB_ID,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        dispatch_notifications,
        trigger=IntervalTrigger(seconds=dispatcher_interval_seconds),
        id=_DISPATCHER_JOB_ID,
        max_instances=1,
        coalesce=True,
    )
    return scheduler
