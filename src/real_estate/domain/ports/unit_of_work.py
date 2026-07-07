"""Unit of Work port.

Defines the transaction boundary for a use-case: repositories accessed through
a UoW commit or roll back together (CLAUDE.md §7). Concrete adapters wrap a
SQLAlchemy session.
"""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, runtime_checkable

from real_estate.domain.ports.repositories import (
    AlertRepository,
    MatchRepository,
    PortalListingRepository,
    PropertyRepository,
    SearchCacheRepository,
    SearchExecutionRepository,
)


@runtime_checkable
class UnitOfWork(Protocol):
    """A single atomic transaction exposing the repositories it governs."""

    alerts: AlertRepository
    properties: PropertyRepository
    matches: MatchRepository
    portal_listings: PortalListingRepository
    search_cache: SearchCacheRepository
    search_executions: SearchExecutionRepository

    def __enter__(self) -> UnitOfWork: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None:
        """Persist all changes made within this transaction."""
        ...

    def rollback(self) -> None:
        """Discard all changes made within this transaction."""
        ...
