from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import (
    AlertSeverity,
    AlertStatus,
    CameraStatus,
    EventType,
    IdentifierType,
    SourceProtocol,
    StorageTier,
    UserRole,
    WatchlistCategory,
)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    username: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: str
    username: str
    email: str | None = None
    full_name: str | None = None
    role: UserRole
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CameraCreate(BaseModel):
    id: str = Field(..., min_length=2, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    name: str
    department: str
    zone: str | None = None
    camera_type: str = "fixed"
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    source_protocol: SourceProtocol
    stream_ref: str = Field(..., description="Plain stream reference; encrypted at rest server-side")
    storage_tier: StorageTier = StorageTier.hot
    retention_days: int = Field(30, ge=1, le=3650)
    onboarded_via: str = "manual"


class CameraUpdate(BaseModel):
    name: str | None = None
    department: str | None = None
    zone: str | None = None
    camera_type: str | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    stream_ref: str | None = None
    storage_tier: StorageTier | None = None
    retention_days: int | None = Field(None, ge=1, le=3650)
    is_active: bool | None = None


class CameraOut(BaseModel):
    id: str
    name: str
    department: str
    zone: str | None
    camera_type: str
    latitude: float
    longitude: float
    source_protocol: SourceProtocol
    stream_ref_masked: str
    status: CameraStatus
    last_heartbeat: datetime | None
    storage_tier: StorageTier
    retention_days: int
    is_active: bool
    onboarded_via: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WatchlistCreate(BaseModel):
    category: WatchlistCategory
    identifier_type: IdentifierType
    identifier_value: str = Field(..., min_length=2, max_length=64)
    label: str
    description: str | None = None
    risk_level: AlertSeverity = AlertSeverity.medium

    @field_validator("identifier_value")
    @classmethod
    def normalize_identifier(cls, v: str) -> str:
        return v.strip().upper().replace(" ", "")


class WatchlistUpdate(BaseModel):
    label: str | None = None
    description: str | None = None
    risk_level: AlertSeverity | None = None
    is_active: bool | None = None


class WatchlistOut(BaseModel):
    id: str
    category: WatchlistCategory
    identifier_type: IdentifierType
    identifier_value: str
    label: str
    description: str | None
    risk_level: AlertSeverity
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DetectionEventIn(BaseModel):
    camera_id: str
    event_type: EventType
    timestamp: datetime | None = None
    vehicle_number: str | None = None
    vehicle_type: str | None = None
    person_ref: str | None = None
    confidence: float = Field(..., ge=0, le=1)
    bounding_box: dict[str, Any] = Field(default_factory=dict)
    source: str = "analytics_service"

    @field_validator("vehicle_number")
    @classmethod
    def normalize_plate(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v.strip().upper().replace(" ", "")


class DetectionEventOut(BaseModel):
    id: str
    camera_id: str
    event_type: EventType
    timestamp: datetime
    vehicle_number: str | None
    vehicle_type: str | None
    person_ref: str | None
    confidence: float
    bounding_box: dict[str, Any]
    source: str

    model_config = ConfigDict(from_attributes=True)


class AlertOut(BaseModel):
    id: str
    event_id: str | None
    camera_id: str
    watchlist_id: str | None
    matched_identifier: str
    alert_type: WatchlistCategory
    severity: AlertSeverity
    status: AlertStatus
    confidence: float
    timestamp: datetime
    latitude: float | None
    longitude: float | None
    notes: str | None
    acknowledged_by: str | None
    resolved_by: str | None

    model_config = ConfigDict(from_attributes=True)


class AlertUpdate(BaseModel):
    status: AlertStatus
    notes: str | None = None


class TraceHit(BaseModel):
    event_id: str
    camera_id: str
    camera_name: str
    latitude: float
    longitude: float
    timestamp: datetime
    confidence: float
    event_type: EventType


class TraceResult(BaseModel):
    identifier: str
    is_watchlisted: bool
    watchlist_entry: WatchlistOut | None
    hits: list[TraceHit]


class StatsSummary(BaseModel):
    cameras_total: int
    cameras_online: int
    cameras_offline: int
    cameras_degraded: int
    events_last_24h: int
    alerts_active: int
    alerts_critical: int
    watchlist_entries: int
    generated_at: datetime


class AuditLogOut(BaseModel):
    id: str
    actor_username: str | None
    action: str
    entity_type: str
    entity_id: str | None
    details: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
