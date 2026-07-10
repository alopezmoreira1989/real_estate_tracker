"""ListSearchExecutions — recent scrape attempts, for the dashboard's
execution/normalization health view (doc05 §6)."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from real_estate.domain.model.search_execution import SearchExecution
from real_estate.domain.ports import UnitOfWork


class ListSearchExecutions:
    def __init__(self, *, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def run(self, *, limit: int = 50) -> Sequence[SearchExecution]:
        with self._uow_factory() as uow:
            return uow.search_executions.list_recent(limit)
