"""SQLAlchemy ORM models mirroring the schema in docs/architecture/03-database.md.

Enum values are stored as strings (the controlled vocabulary value); domain
constructors validate them. UUIDs use SQLAlchemy's ``Uuid`` (native on
PostgreSQL, CHAR on SQLite) and JSON columns use ``JSON`` (JSONB on PostgreSQL).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from real_estate.infrastructure.persistence.base import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PortalModel(Base):
    __tablename__ = "portals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    base_url: Mapped[str] = mapped_column(String(500))
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_enabled: Mapped[bool] = mapped_column(default=True)


class SearchAlertModel(Base):
    __tablename__ = "search_alerts"
    __table_args__ = (
        CheckConstraint("frequency_seconds >= 60", name="frequency_min_60s"),
        Index("ix_search_alerts_due", "is_active", "last_run_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    frequency_seconds: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    conditions: Mapped[list[AlertConditionModel]] = relationship(
        back_populates="alert",
        cascade="all, delete-orphan",
        order_by="AlertConditionModel.position",
    )


class AlertConditionModel(Base):
    """One node of an alert's condition tree (a GROUP or a leaf CONDITION)."""

    __tablename__ = "alert_conditions"
    __table_args__ = (
        CheckConstraint("node_type in ('GROUP', 'CONDITION')", name="node_type_valid"),
        CheckConstraint(
            "(node_type = 'CONDITION' AND field_key IS NOT NULL AND operator IS NOT NULL "
            "AND group_operator IS NULL) OR "
            "(node_type = 'GROUP' AND group_operator IS NOT NULL AND field_key IS NULL "
            "AND operator IS NULL)",
            name="node_shape_valid",
        ),
        Index("ix_alert_conditions_tree", "alert_id", "parent_group_id", "position"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    alert_id: Mapped[UUID] = mapped_column(ForeignKey("search_alerts.id", ondelete="CASCADE"))
    parent_group_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("alert_conditions.id", ondelete="CASCADE"), nullable=True
    )
    node_type: Mapped[str] = mapped_column(String(16))
    group_operator: Mapped[str | None] = mapped_column(String(8), nullable=True)
    field_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    operator: Mapped[str | None] = mapped_column(String(16), nullable=True)
    value: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    alert: Mapped[SearchAlertModel] = relationship(back_populates="conditions")


class AlertSubscriptionPortalModel(Base):
    __tablename__ = "alert_subscription_portals"

    alert_id: Mapped[UUID] = mapped_column(
        ForeignKey("search_alerts.id", ondelete="CASCADE"), primary_key=True
    )
    portal_id: Mapped[int] = mapped_column(
        ForeignKey("portals.id", ondelete="CASCADE"), primary_key=True
    )


class PropertyModel(Base):
    __tablename__ = "properties"
    __table_args__ = (
        Index("ix_properties_prov_type_listing", "province_ine", "property_type", "listing_type"),
        Index("ix_properties_type_ppm2", "property_type", "price_per_m2"),
        Index("ix_properties_prov_price", "province_ine", "price_amount"),
        Index("ix_properties_land_type", "land_type"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    fingerprint: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    listing_type: Mapped[str] = mapped_column(String(16))
    property_type: Mapped[str] = mapped_column(String(24))
    land_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    province_ine: Mapped[str] = mapped_column(String(2))
    municipality_ine: Mapped[str | None] = mapped_column(String(5), nullable=True)
    municipality_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    district: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(5), nullable=True)
    lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    price_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    price_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    area_m2: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    plot_area_m2: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_per_m2: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    features: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    media: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="UNKNOWN")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PortalListingModel(Base):
    __tablename__ = "portal_listings"
    __table_args__ = (UniqueConstraint("portal_id", "external_id", name="portal_external_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    portal_id: Mapped[int] = mapped_column(ForeignKey("portals.id", ondelete="CASCADE"))
    property_id: Mapped[UUID] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"))
    external_id: Mapped[str] = mapped_column(String(128))
    url: Mapped[str] = mapped_column(String(1000))
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64))
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PriceHistoryModel(Base):
    __tablename__ = "price_history"
    __table_args__ = (Index("ix_price_history_property_time", "property_id", "observed_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    property_id: Mapped[UUID] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"))
    price_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    price_currency: Mapped[str] = mapped_column(String(3))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AlertMatchModel(Base):
    __tablename__ = "alert_matches"
    __table_args__ = (
        UniqueConstraint("alert_id", "property_id", name="alert_property_unique"),
        Index("ix_alert_matches_status_time", "status", "matched_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    alert_id: Mapped[UUID] = mapped_column(ForeignKey("search_alerts.id", ondelete="CASCADE"))
    property_id: Mapped[UUID] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"))
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="NEW")


class NotificationChannelModel(Base):
    __tablename__ = "notification_channels"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    channel_type: Mapped[str] = mapped_column(String(24))
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_enabled: Mapped[bool] = mapped_column(default=True)


class NotificationModel(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_status_time", "status", "created_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    match_id: Mapped[UUID] = mapped_column(ForeignKey("alert_matches.id", ondelete="CASCADE"))
    channel_id: Mapped[UUID] = mapped_column(
        ForeignKey("notification_channels.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SearchExecutionModel(Base):
    __tablename__ = "search_executions"
    __table_args__ = (Index("ix_search_executions_portal_time", "portal_id", "started_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    portal_id: Mapped[int] = mapped_column(ForeignKey("portals.id", ondelete="CASCADE"))
    query_signature: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    listings_found: Mapped[int] = mapped_column(Integer, default=0)
    listings_new: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SearchCacheModel(Base):
    __tablename__ = "search_cache"

    query_signature: Mapped[str] = mapped_column(String(64), primary_key=True)
    portal_id: Mapped[int] = mapped_column(ForeignKey("portals.id", ondelete="CASCADE"))
    result_ref: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
