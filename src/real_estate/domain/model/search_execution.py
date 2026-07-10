"""SearchExecution: an audit-trail record of one scrape attempt (doc03).

Read-side counterpart to ``SearchExecutionRepository.record`` — not a
mutable aggregate (nothing ever changes a past execution), just a value
snapshot for observability (doc05 §6: scrape/normalization health).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SearchExecutionStatus(StrEnum):
    """Outcome of one scrape attempt for one query signature (doc03)."""

    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class SearchExecution:
    """One row of the scrape audit trail."""

    portal_slug: str
    query_signature: str
    status: SearchExecutionStatus
    listings_found: int
    listings_new: int
    normalization_issues: int
    error: str | None
    started_at: datetime
    finished_at: datetime | None
