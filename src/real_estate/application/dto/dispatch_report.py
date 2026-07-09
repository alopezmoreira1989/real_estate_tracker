"""Summary of one DispatchNotifications run."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DispatchReport:
    """Counts from one dispatcher run (Phase 7's operational CLI will surface this)."""

    notifications_pending: int
    sent: int
    failed: int
