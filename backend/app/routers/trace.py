from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Camera, DetectionEvent, IdentifierType, User, WatchlistEntry
from app.schemas import TraceHit, TraceResult, WatchlistOut

router = APIRouter(prefix="/api/v1", tags=["trace"])


@router.get("/entities/search")
async def search_entities(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[dict]:
    like = f"%{q.strip().upper()}%"
    rows = (
        db.query(
            DetectionEvent.vehicle_number,
            func.count(DetectionEvent.id).label("sightings"),
            func.max(DetectionEvent.timestamp).label("last_seen"),
        )
        .filter(DetectionEvent.vehicle_number.ilike(like))
        .group_by(DetectionEvent.vehicle_number)
        .order_by(func.max(DetectionEvent.timestamp).desc())
        .limit(25)
        .all()
    )
    watchlisted = {
        w.identifier_value
        for w in db.query(WatchlistEntry.identifier_value)
        .filter(WatchlistEntry.identifier_type == IdentifierType.plate, WatchlistEntry.is_active.is_(True))
        .all()
    }
    return [
        {
            "identifier": r.vehicle_number,
            "sightings": r.sightings,
            "last_seen": r.last_seen,
            "is_watchlisted": r.vehicle_number in watchlisted,
        }
        for r in rows
    ]


@router.get("/trace/{identifier}", response_model=TraceResult)
async def trace_identifier(
    identifier: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> TraceResult:
    normalized = identifier.strip().upper().replace(" ", "")

    rows = (
        db.query(DetectionEvent, Camera)
        .join(Camera, Camera.id == DetectionEvent.camera_id)
        .filter(DetectionEvent.vehicle_number == normalized)
        .order_by(DetectionEvent.timestamp.asc())
        .all()
    )

    hits = [
        TraceHit(
            event_id=event.id,
            camera_id=camera.id,
            camera_name=camera.name,
            latitude=camera.latitude,
            longitude=camera.longitude,
            timestamp=event.timestamp,
            confidence=event.confidence,
            event_type=event.event_type,
        )
        for event, camera in rows
    ]

    watchlist_entry = (
        db.query(WatchlistEntry)
        .filter(
            WatchlistEntry.identifier_type == IdentifierType.plate,
            WatchlistEntry.identifier_value == normalized,
            WatchlistEntry.is_active.is_(True),
        )
        .first()
    )

    return TraceResult(
        identifier=normalized,
        is_watchlisted=watchlist_entry is not None,
        watchlist_entry=WatchlistOut.model_validate(watchlist_entry) if watchlist_entry else None,
        hits=hits,
    )
