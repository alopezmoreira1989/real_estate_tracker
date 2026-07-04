"""SQLAlchemy adapter for :class:`AlertRepository`.

Maps the :class:`SearchAlert` aggregate — including its condition **tree** and
its portal subscriptions — onto the ``search_alerts``, ``alert_conditions``
(self-referential) and ``alert_subscription_portals`` tables.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from real_estate.domain.model.alert import SearchAlert
from real_estate.domain.model.conditions import (
    AlertCondition,
    ConditionValue,
    GroupOperator,
    Operator,
    RuleGroup,
    Scalar,
)
from real_estate.domain.model.identifiers import AlertId, UserId
from real_estate.infrastructure.persistence.models.orm import (
    AlertConditionModel,
    AlertSubscriptionPortalModel,
    PortalModel,
    SearchAlertModel,
)

# --- condition value codec (preserves scalar types through JSON) ------------


def _encode_scalar(value: Scalar) -> dict[str, Any]:
    if isinstance(value, bool):
        return {"t": "bool", "v": value}
    if isinstance(value, int):
        return {"t": "int", "v": value}
    if isinstance(value, Decimal):
        return {"t": "dec", "v": str(value)}
    return {"t": "str", "v": value}


def _decode_scalar(data: dict[str, Any]) -> Scalar:
    kind = data["t"]
    raw = data["v"]
    if kind == "bool":
        return bool(raw)
    if kind == "int":
        return int(raw)
    if kind == "dec":
        return Decimal(str(raw))
    return str(raw)


def encode_value(value: ConditionValue | None) -> Any | None:
    if value is None:
        return None
    if isinstance(value, tuple):
        return {"tuple": [_encode_scalar(item) for item in value]}
    return _encode_scalar(value)


def decode_value(data: Any | None) -> ConditionValue | None:
    if data is None:
        return None
    if isinstance(data, dict) and "tuple" in data:
        return tuple(_decode_scalar(item) for item in data["tuple"])
    return _decode_scalar(data)


# --- tree <-> rows ----------------------------------------------------------


def _build_rows(
    alert_id: UUID,
    node: AlertCondition | RuleGroup,
    parent_id: UUID | None,
    position: int,
    out: list[AlertConditionModel],
) -> None:
    node_id = uuid4()
    if isinstance(node, RuleGroup):
        out.append(
            AlertConditionModel(
                id=node_id,
                alert_id=alert_id,
                parent_group_id=parent_id,
                node_type="GROUP",
                group_operator=node.operator.value,
                position=position,
            )
        )
        for index, child in enumerate(node.children):
            _build_rows(alert_id, child, node_id, index, out)
    else:
        out.append(
            AlertConditionModel(
                id=node_id,
                alert_id=alert_id,
                parent_group_id=parent_id,
                node_type="CONDITION",
                field_key=node.field_key,
                operator=node.operator.value,
                value=encode_value(node.value),
                position=position,
            )
        )


def _rebuild_tree(rows: list[AlertConditionModel]) -> RuleGroup:
    by_parent: dict[UUID | None, list[AlertConditionModel]] = defaultdict(list)
    for row in rows:
        by_parent[row.parent_group_id].append(row)
    for children in by_parent.values():
        children.sort(key=lambda r: r.position)

    def build(row: AlertConditionModel) -> AlertCondition | RuleGroup:
        if row.node_type == "GROUP":
            assert row.group_operator is not None
            children = [build(child) for child in by_parent[row.id]]
            return RuleGroup(GroupOperator(row.group_operator), tuple(children))
        assert row.field_key is not None and row.operator is not None
        return AlertCondition(row.field_key, Operator(row.operator), decode_value(row.value))

    roots = by_parent[None]
    if len(roots) != 1:
        raise ValueError(f"expected exactly one root condition group, found {len(roots)}")
    root = build(roots[0])
    if not isinstance(root, RuleGroup):
        raise ValueError("root condition node must be a group")
    return root


class SqlAlchemyAlertRepository:
    """Persists the SearchAlert aggregate via a SQLAlchemy session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, alert: SearchAlert) -> None:
        model = SearchAlertModel(
            id=alert.id,
            user_id=alert.user_id,
            name=alert.name,
            frequency_seconds=alert.frequency_seconds,
            is_active=alert.is_active,
            last_run_at=alert.last_run_at,
            created_at=alert.created_at,
            updated_at=alert.updated_at,
        )
        rows: list[AlertConditionModel] = []
        _build_rows(alert.id, alert.conditions, None, 0, rows)
        model.conditions = rows
        self._session.add(model)

        for slug in sorted(alert.portal_slugs):
            portal = self._get_or_create_portal(slug)
            self._session.add(AlertSubscriptionPortalModel(alert_id=alert.id, portal_id=portal.id))

    def get(self, alert_id: AlertId) -> SearchAlert | None:
        model = self._session.get(SearchAlertModel, alert_id)
        if model is None:
            return None
        return self._to_domain(model)

    def list_for_user(self, user_id: UserId) -> list[SearchAlert]:
        stmt = select(SearchAlertModel).where(SearchAlertModel.user_id == user_id)
        return [self._to_domain(m) for m in self._session.execute(stmt).scalars()]

    def _to_domain(self, model: SearchAlertModel) -> SearchAlert:
        slugs = self._session.execute(
            select(PortalModel.slug)
            .join(
                AlertSubscriptionPortalModel,
                AlertSubscriptionPortalModel.portal_id == PortalModel.id,
            )
            .where(AlertSubscriptionPortalModel.alert_id == model.id)
        ).scalars()
        return SearchAlert(
            id=AlertId(model.id),
            user_id=UserId(model.user_id),
            name=model.name,
            portal_slugs=frozenset(slugs),
            frequency_seconds=model.frequency_seconds,
            conditions=_rebuild_tree(list(model.conditions)),
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_active=model.is_active,
            last_run_at=model.last_run_at,
        )

    def _get_or_create_portal(self, slug: str) -> PortalModel:
        existing = self._session.execute(
            select(PortalModel).where(PortalModel.slug == slug)
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        portal = PortalModel(slug=slug, name=slug, base_url=f"https://{slug}")
        self._session.add(portal)
        self._session.flush()
        return portal
