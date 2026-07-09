"""Typed identifier wrappers.

Raw ``str``/``int``/``UUID`` ids are never passed across boundaries; these
``NewType`` wrappers make signatures self-documenting and mixing ids a type
error (CLAUDE.md §4).
"""

from __future__ import annotations

from typing import NewType
from uuid import UUID

UserId = NewType("UserId", UUID)
PropertyId = NewType("PropertyId", UUID)
AlertId = NewType("AlertId", UUID)
ConditionId = NewType("ConditionId", UUID)
MatchId = NewType("MatchId", UUID)
NotificationChannelId = NewType("NotificationChannelId", UUID)
NotificationId = NewType("NotificationId", UUID)
