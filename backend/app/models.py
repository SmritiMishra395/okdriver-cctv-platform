import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


class UserRole(str, enum.Enum):
    admin = "admin"
    operator = "operator"


class CameraStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    degraded = "degraded"


class SourceProtocol(str, enum.Enum):
    simulator = "simulator"
    file = "file"
    rtsp = "rtsp"
    onvif = "onvif"


class StorageTier(str, enum.Enum):
    hot = "hot"
    warm = "warm"
    cold = "cold"


class WatchlistCategory(str, enum.Enum):
    stolen_vehicle = "stolen_vehicle"
    blacklisted_vehicle = "blacklisted_vehicle"
    wanted_person = "wanted_person"
    missing_person = "missing_person"
    other = "other"


class IdentifierType(str, enum.Enum):
    plate = "plate"
    face_id = "face_id"
    name = "name"


class EventType(str, enum.Enum):
    anpr = "anpr"
    vehicle_detection = "vehicle_detection"
    person_detection = "person_detection"
    object_detection = "object_detection"


class AlertSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AlertStatus(str, enum.Enum):
    new = "new"
    acknowledged = "acknowledged"
    resolved = "resolved"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.operator, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    department: Mapped[str] = mapped_column(String(128), nullable=False)
    zone: Mapped[str | None] = mapped_column(String(128), nullable=True)
    camera_type: Mapped[str] = mapped_column(String(32), default="fixed")
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    source_protocol: Mapped[SourceProtocol] = mapped_column(Enum(SourceProtocol), nullable=False)
    stream_ref_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CameraStatus] = mapped_column(Enum(CameraStatus), default=CameraStatus.offline)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    storage_tier: Mapped[StorageTier] = mapped_column(Enum(StorageTier), default=StorageTier.hot)
    retention_days: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    onboarded_via: Mapped[str] = mapped_column(String(16), default="manual")  # manual | api
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    events: Mapped[list["DetectionEvent"]] = relationship(back_populates="camera")

    __table_args__ = (
        Index("ix_cameras_status", "status"),
        Index("ix_cameras_department", "department"),
    )


class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    category: Mapped[WatchlistCategory] = mapped_column(Enum(WatchlistCategory), nullable=False)
    identifier_type: Mapped[IdentifierType] = mapped_column(Enum(IdentifierType), nullable=False)
    identifier_value: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), default=AlertSeverity.medium)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    __table_args__ = (
        Index("ix_watchlist_identifier", "identifier_type", "identifier_value"),
    )


class DetectionEvent(Base):
    __tablename__ = "detection_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    camera_id: Mapped[str] = mapped_column(String(32), ForeignKey("cameras.id"), nullable=False)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
    vehicle_number: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    vehicle_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    person_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    bounding_box: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(32), default="analytics_service")
    dedup_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    camera: Mapped["Camera"] = relationship(back_populates="events")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="event")

    __table_args__ = (
        Index("ix_events_camera_time", "camera_id", "timestamp"),
        Index("ix_events_vehicle_time", "vehicle_number", "timestamp"),
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    event_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("detection_events.id"), nullable=True)
    camera_id: Mapped[str] = mapped_column(String(32), ForeignKey("cameras.id"), nullable=False)
    watchlist_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("watchlist_entries.id"), nullable=True)
    matched_identifier: Mapped[str] = mapped_column(String(64), nullable=False)
    alert_type: Mapped[WatchlistCategory] = mapped_column(Enum(WatchlistCategory), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus), default=AlertStatus.new, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    event: Mapped["DetectionEvent"] = relationship(back_populates="alerts")

    __table_args__ = (
        Index("ix_alerts_status_time", "status", "timestamp"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    actor_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    actor_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
