from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Alert, AlertSeverity, AlertStatus, Camera, CameraStatus, DetectionEvent, User, WatchlistEntry
from app.schemas import StatsSummary

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


@router.get("/summary", response_model=StatsSummary)
async def stats_summary(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> StatsSummary:
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    total = db.query(func.count(Camera.id)).filter(Camera.is_active.is_(True)).scalar() or 0
    online = db.query(func.count(Camera.id)).filter(Camera.status == CameraStatus.online, Camera.is_active.is_(True)).scalar() or 0
    offline = db.query(func.count(Camera.id)).filter(Camera.status == CameraStatus.offline, Camera.is_active.is_(True)).scalar() or 0
    degraded = db.query(func.count(Camera.id)).filter(Camera.status == CameraStatus.degraded, Camera.is_active.is_(True)).scalar() or 0

    events_24h = db.query(func.count(DetectionEvent.id)).filter(DetectionEvent.timestamp >= since).scalar() or 0

    active_alerts = db.query(func.count(Alert.id)).filter(Alert.status != AlertStatus.resolved).scalar() or 0
    critical_alerts = (
        db.query(func.count(Alert.id))
        .filter(Alert.status != AlertStatus.resolved, Alert.severity == AlertSeverity.critical)
        .scalar()
        or 0
    )

    watchlist_count = db.query(func.count(WatchlistEntry.id)).filter(WatchlistEntry.is_active.is_(True)).scalar() or 0

    return StatsSummary(
        cameras_total=total,
        cameras_online=online,
        cameras_offline=offline,
        cameras_degraded=degraded,
        events_last_24h=events_24h,
        alerts_active=active_alerts,
        alerts_critical=critical_alerts,
        watchlist_entries=watchlist_count,
        generated_at=datetime.now(timezone.utc),
    )
