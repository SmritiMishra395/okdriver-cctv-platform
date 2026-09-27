import hashlib
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Alert, AlertSeverity, Camera, DetectionEvent, IdentifierType, WatchlistEntry
from app.realtime.ws_manager import manager
from app.schemas import DetectionEventIn

settings = get_settings()


def _dedup_hash(camera_id: str, event_type: str, identifier: str | None, ts: datetime) -> str:
    window = settings.event_dedup_window_seconds
    bucket = int(ts.timestamp() // window)
    raw = f"{camera_id}|{event_type}|{identifier or ''}|{bucket}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def ingest_event(db: Session, payload: DetectionEventIn) -> tuple[DetectionEvent, Alert | None, bool]:
    """Validates, stores, deduplicates and watchlist-matches one analytics event.

    Returns (event, alert_or_none, was_duplicate). This is the single code
    path used by both the public /events/ingest API and the built-in
    analytics simulator, so a real AI service can be pointed at the same
    endpoint with no backend changes.
    """
    camera = db.query(Camera).filter(Camera.id == payload.camera_id, Camera.is_active.is_(True)).first()
    if camera is None:
        raise ValueError(f"unknown or inactive camera_id '{payload.camera_id}'")

    ts = payload.timestamp or datetime.now(timezone.utc)
    identifier = payload.vehicle_number or payload.person_ref
    dedup_hash = _dedup_hash(payload.camera_id, payload.event_type.value, identifier, ts)

    existing = db.query(DetectionEvent).filter(DetectionEvent.dedup_hash == dedup_hash).first()
    if existing is not None:
        return existing, None, True

    event = DetectionEvent(
        camera_id=payload.camera_id,
        event_type=payload.event_type,
        timestamp=ts,
        vehicle_number=payload.vehicle_number,
        vehicle_type=payload.vehicle_type,
        person_ref=payload.person_ref,
        confidence=payload.confidence,
        bounding_box=payload.bounding_box,
        raw_payload=payload.model_dump(mode="json"),
        source=payload.source,
        dedup_hash=dedup_hash,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    await manager.broadcast(
        "event.new",
        {
            "id": event.id,
            "camera_id": event.camera_id,
            "camera_name": camera.name,
            "event_type": event.event_type.value,
            "vehicle_number": event.vehicle_number,
            "vehicle_type": event.vehicle_type,
            "confidence": event.confidence,
            "timestamp": event.timestamp,
            "latitude": camera.latitude,
            "longitude": camera.longitude,
        },
    )

    alert = await _match_watchlist(db, camera, event)
    return event, alert, False


async def _match_watchlist(db: Session, camera: Camera, event: DetectionEvent) -> Alert | None:
    if not event.vehicle_number:
        return None

    entry = (
        db.query(WatchlistEntry)
        .filter(
            WatchlistEntry.identifier_type == IdentifierType.plate,
            WatchlistEntry.identifier_value == event.vehicle_number,
            WatchlistEntry.is_active.is_(True),
        )
        .first()
    )
    if entry is None:
        return None

    alert = Alert(
        event_id=event.id,
        camera_id=camera.id,
        watchlist_id=entry.id,
        matched_identifier=event.vehicle_number,
        alert_type=entry.category,
        severity=entry.risk_level,
        confidence=event.confidence,
        timestamp=event.timestamp,
        latitude=camera.latitude,
        longitude=camera.longitude,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    await manager.broadcast(
        "alert.new",
        {
            "id": alert.id,
            "camera_id": camera.id,
            "camera_name": camera.name,
            "matched_identifier": alert.matched_identifier,
            "alert_type": alert.alert_type.value,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "confidence": alert.confidence,
            "timestamp": alert.timestamp,
            "latitude": alert.latitude,
            "longitude": alert.longitude,
            "watchlist_label": entry.label,
        },
    )
    return alert
