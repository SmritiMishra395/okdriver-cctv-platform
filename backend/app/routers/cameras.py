from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import AuditLog, Camera, CameraStatus, SourceProtocol, User
from app.schemas import CameraCreate, CameraOut, CameraUpdate
from app.security import decrypt_secret, encrypt_secret, mask_stream_ref
from app.services import audit

router = APIRouter(prefix="/api/v1/cameras", tags=["cameras"])


def _to_out(camera: Camera) -> CameraOut:
    plain = decrypt_secret(camera.stream_ref_encrypted)
    return CameraOut(
        id=camera.id,
        name=camera.name,
        department=camera.department,
        zone=camera.zone,
        camera_type=camera.camera_type,
        latitude=camera.latitude,
        longitude=camera.longitude,
        source_protocol=camera.source_protocol,
        stream_ref_masked=mask_stream_ref(plain),
        status=camera.status,
        last_heartbeat=camera.last_heartbeat,
        storage_tier=camera.storage_tier,
        retention_days=camera.retention_days,
        is_active=camera.is_active,
        onboarded_via=camera.onboarded_via,
        created_at=camera.created_at,
        updated_at=camera.updated_at,
    )


@router.get("", response_model=list[CameraOut])
async def list_cameras(
    department: str | None = Query(default=None),
    status_filter: CameraStatus | None = Query(default=None, alias="status"),
    zone: str | None = Query(default=None),
    q: str | None = Query(default=None, description="Search by camera id or name"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[CameraOut]:
    query = db.query(Camera)
    if department:
        query = query.filter(Camera.department == department)
    if status_filter:
        query = query.filter(Camera.status == status_filter)
    if zone:
        query = query.filter(Camera.zone == zone)
    if q:
        like = f"%{q}%"
        query = query.filter((Camera.id.ilike(like)) | (Camera.name.ilike(like)))
    cameras = query.order_by(Camera.id).all()
    return [_to_out(c) for c in cameras]


@router.post("", response_model=CameraOut, status_code=status.HTTP_201_CREATED)
async def create_camera(
    payload: CameraCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> CameraOut:
    if db.query(Camera).filter(Camera.id == payload.id).first():
        raise HTTPException(status.HTTP_409_CONFLICT, f"Camera '{payload.id}' already exists")

    camera = Camera(
        id=payload.id,
        name=payload.name,
        department=payload.department,
        zone=payload.zone,
        camera_type=payload.camera_type,
        latitude=payload.latitude,
        longitude=payload.longitude,
        source_protocol=payload.source_protocol,
        stream_ref_encrypted=encrypt_secret(payload.stream_ref),
        storage_tier=payload.storage_tier,
        retention_days=payload.retention_days,
        onboarded_via=payload.onboarded_via,
        status=CameraStatus.offline,
        created_by=current_user.id,
    )
    db.add(camera)
    db.commit()
    db.refresh(camera)

    audit.record(
        db,
        actor=current_user,
        action="camera.create",
        entity_type="camera",
        entity_id=camera.id,
        details={"name": camera.name, "onboarded_via": camera.onboarded_via},
    )
    return _to_out(camera)


@router.get("/{camera_id}", response_model=CameraOut)
async def get_camera(
    camera_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> CameraOut:
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found")
    return _to_out(camera)


@router.patch("/{camera_id}", response_model=CameraOut)
async def update_camera(
    camera_id: str,
    payload: CameraUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> CameraOut:
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found")

    updates = payload.model_dump(exclude_unset=True)
    stream_ref = updates.pop("stream_ref", None)
    for field, value in updates.items():
        setattr(camera, field, value)
    if stream_ref is not None:
        camera.stream_ref_encrypted = encrypt_secret(stream_ref)

    db.add(camera)
    db.commit()
    db.refresh(camera)

    audit.record(
        db,
        actor=current_user,
        action="camera.update",
        entity_type="camera",
        entity_id=camera.id,
        details={"fields": list(updates.keys())},
    )
    return _to_out(camera)


@router.post("/{camera_id}/disable", response_model=CameraOut)
async def disable_camera(
    camera_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
) -> CameraOut:
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found")
    camera.is_active = False
    camera.status = CameraStatus.offline
    db.add(camera)
    db.commit()
    db.refresh(camera)

    audit.record(db, actor=current_user, action="camera.disable", entity_type="camera", entity_id=camera.id)
    return _to_out(camera)


@router.post("/{camera_id}/enable", response_model=CameraOut)
async def enable_camera(
    camera_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
) -> CameraOut:
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found")
    camera.is_active = True
    db.add(camera)
    db.commit()
    db.refresh(camera)

    audit.record(db, actor=current_user, action="camera.enable", entity_type="camera", entity_id=camera.id)
    return _to_out(camera)


@router.get("/{camera_id}/audit")
async def camera_audit_history(
    camera_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[dict]:
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "camera", AuditLog.entity_id == camera_id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "action": log.action,
            "actor": log.actor_username,
            "details": log.details,
            "created_at": log.created_at,
        }
        for log in logs
    ]
