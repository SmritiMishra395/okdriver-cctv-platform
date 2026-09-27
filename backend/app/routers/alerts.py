from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Alert, AlertStatus, User
from app.realtime.ws_manager import manager
from app.schemas import AlertOut, AlertUpdate
from app.services import audit

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    status_filter: AlertStatus | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
    camera_id: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AlertOut]:
    query = db.query(Alert)
    if status_filter:
        query = query.filter(Alert.status == status_filter)
    if severity:
        query = query.filter(Alert.severity == severity)
    if camera_id:
        query = query.filter(Alert.camera_id == camera_id)
    return query.order_by(Alert.timestamp.desc()).limit(limit).all()


@router.patch("/{alert_id}", response_model=AlertOut)
async def update_alert(
    alert_id: str,
    payload: AlertUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertOut:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found")

    alert.status = payload.status
    if payload.notes is not None:
        alert.notes = payload.notes
    now = datetime.now(timezone.utc)
    if payload.status == AlertStatus.acknowledged:
        alert.acknowledged_by = current_user.id
        alert.acknowledged_at = now
    elif payload.status == AlertStatus.resolved:
        alert.resolved_by = current_user.id
        alert.resolved_at = now

    db.add(alert)
    db.commit()
    db.refresh(alert)

    audit.record(
        db,
        actor=current_user,
        action=f"alert.{payload.status.value}",
        entity_type="alert",
        entity_id=alert.id,
        details={"matched_identifier": alert.matched_identifier},
    )
    await manager.broadcast(
        "alert.updated",
        {"id": alert.id, "status": alert.status.value, "camera_id": alert.camera_id},
    )
    return alert
