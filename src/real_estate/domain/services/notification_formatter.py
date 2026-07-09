"""format_match_message — builds a channel-agnostic message for a matched listing.

A pure domain service: no I/O, formats using only the ``Property`` value
already known to the domain (title, price, area) plus its originating url
(supplied by the caller, since a portal-specific url is not a ``Property``
field — doc02 §2, doc08 §3's "title, price, area, link").
"""

from __future__ import annotations

from real_estate.domain.model.property import Property
from real_estate.domain.ports.notifier import NotificationMessage


def format_match_message(alert_name: str, prop: Property, url: str | None) -> NotificationMessage:
    """Render ``prop`` (a new match for ``alert_name``) into a NotificationMessage."""
    lines = [prop.title]
    if prop.price is not None:
        lines.append(f"{prop.price.amount:,.0f} {prop.price.currency.value}")
    if prop.area is not None:
        lines.append(f"{prop.area.square_meters:,.0f} m²")

    return NotificationMessage(
        title=f"New match: {alert_name}",
        body="\n".join(lines),
        url=url,
    )
