import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user_ws, get_optional_query_token, require_admin
from app.models import Camera, User
from app.security import decrypt_secret
from app.video.base import StreamUnavailableError
from app.video.onvif_adapter import discover
from app.video.registry import get_adapter

router = APIRouter(prefix="/api/v1", tags=["streams"])

BOUNDARY = "okdriverframe"


async def _mjpeg_generator(camera: Camera):
    stream_ref = decrypt_secret(camera.stream_ref_encrypted)
    adapter = get_adapter(camera.id, camera.source_protocol, stream_ref)
    try:
        async for frame in adapter.frames():
            yield (
                f"--{BOUNDARY}\r\nContent-Type: image/jpeg\r\nContent-Length: {len(frame)}\r\n\r\n"
            ).encode() + frame + b"\r\n"
    except StreamUnavailableError:
        return


@router.get("/cameras/{camera_id}/stream")
async def stream_camera(
    camera_id: str,
    token: str | None = Depends(get_optional_query_token),
    db: Session = Depends(get_db),
):
    """MJPEG relay: works directly in an <img src="..."> tag.

    Auth token is accepted as a query parameter because browsers cannot
    attach an Authorization header to an <img>/EventSource request; the
    same JWT validation logic as every other endpoint still applies.
    """
    get_current_user_ws(token, db)
    camera = db.query(Camera).filter(Camera.id == camera_id, Camera.is_active.is_(True)).first()
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found or inactive")

    return StreamingResponse(
        _mjpeg_generator(camera),
        media_type=f"multipart/x-mixed-replace; boundary={BOUNDARY}",
    )


@router.get("/cameras/{camera_id}/snapshot")
async def snapshot_camera(
    camera_id: str,
    token: str | None = Depends(get_optional_query_token),
    db: Session = Depends(get_db),
):
    get_current_user_ws(token, db)
    camera = db.query(Camera).filter(Camera.id == camera_id, Camera.is_active.is_(True)).first()
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found or inactive")

    stream_ref = decrypt_secret(camera.stream_ref_encrypted)
    adapter = get_adapter(camera.id, camera.source_protocol, stream_ref)
    try:
        async with asyncio.timeout(5):
            async for frame in adapter.frames():
                from fastapi import Response

                return Response(content=frame, media_type="image/jpeg")
    except (StreamUnavailableError, TimeoutError):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Camera source unavailable")


@router.get("/onvif/discover")
async def onvif_discover(_: User = Depends(require_admin)):
    devices = discover()
    return [d.__dict__ for d in devices]
