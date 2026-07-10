"""SystemClock — the real Clock (application/ports.py) used outside tests.

Returns a naive UTC datetime, matching the naive-datetime convention used
throughout the persistence layer (SQLite does not persist tz-awareness, so
every stored timestamp is naive already — see tests/conftest.py).
"""

from __future__ import annotations

from datetime import UTC, datetime


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)
