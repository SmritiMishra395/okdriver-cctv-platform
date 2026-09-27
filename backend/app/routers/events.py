from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models import DetectionEvent, User
from app.schemas import DetectionEventIn, DetectionEventOut
from app.services.ingest import ingest_event

router = APIRouter(prefix="/api/v1/events", tags=["events"])
settings = get_settings()
limiter = Limiter(key_func=get_remote_address)


@router.post("/ingest", response_model=DetectionEventOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_ingest)
async def ingest(
    request: Request,
    payload: DetectionEventIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DetectionEventOut:
    """Entry point for any analytics engine (ANPR, object/person detection, etc).

    Validates the event, deduplicates it against recent identical events on
    the same camera, persists it, and checks it against the watchlist --
    generating a real-time alert automatically on a match.
    """
    try:
        event, _alert, was_duplicate = await ingest_event(db, payload)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    response = DetectionEventOut.model_validate(event)
    if was_duplicate:
        request.state.duplicate = True
    return response


@router.get("", response_model=list[DetectionEventOut])
async def list_events(
    camera_id: str | None = Query(default=None),
    vehicle_number: str | None = Query(default=None),
    limit: int = Query(default=50, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[DetectionEventOut]:
    query = db.query(DetectionEvent)
    if camera_id:
        query = query.filter(DetectionEvent.camera_id == camera_id)
    if vehicle_number:
        query = query.filter(DetectionEvent.vehicle_number == vehicle_number.strip().upper())
    events = query.order_by(DetectionEvent.timestamp.desc()).limit(limit).all()
    return [DetectionEventOut.model_validate(e) for e in events]
