from real_estate.infrastructure.scheduling.scheduler import build_scheduler


def test_planner_job_is_registered_with_jitter_and_no_overlap() -> None:
    scheduler = build_scheduler(
        planner_tick=lambda: None,
        dispatch_notifications=lambda: None,
        planner_interval_seconds=60,
        planner_jitter_seconds=10,
        dispatcher_interval_seconds=30,
    )

    job = scheduler.get_job("planner")

    assert job is not None
    assert job.max_instances == 1
    assert job.coalesce is True
    assert job.trigger.interval.total_seconds() == 60
    assert job.trigger.jitter == 10


def test_dispatcher_job_is_registered_without_overlap() -> None:
    scheduler = build_scheduler(
        planner_tick=lambda: None,
        dispatch_notifications=lambda: None,
        planner_interval_seconds=60,
        planner_jitter_seconds=10,
        dispatcher_interval_seconds=30,
    )

    job = scheduler.get_job("dispatcher")

    assert job is not None
    assert job.max_instances == 1
    assert job.coalesce is True
    assert job.trigger.interval.total_seconds() == 30


def test_exactly_two_jobs_are_registered_a_single_planner_and_a_single_dispatcher() -> None:
    scheduler = build_scheduler(
        planner_tick=lambda: None,
        dispatch_notifications=lambda: None,
        planner_interval_seconds=60,
        planner_jitter_seconds=10,
        dispatcher_interval_seconds=30,
    )

    assert len(scheduler.get_jobs()) == 2
