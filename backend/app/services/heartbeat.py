import asyncio
import logging
from datetime import datetime, timezone

from app.config import get_settings
from app.database import SessionLocal
from app.models import Camera, CameraStatus
from app.realtime.ws_manager import manager
from app.video.registry import get_adapter
from app.security import decrypt_secret

logger = logging.getLogger("okdriver.heartbeat")
settings = get_settings()

_CHECK_TIMEOUT_SECONDS = 3.0


class HeartbeatService:
    """Periodically probes every registered camera's adapter.

    A camera is marked Online when its adapter's health check succeeds
    within the timeout, Degraded when the check itself raises but the
    camera has an active record (mis-provisioned or momentarily
    unreachable), and Offline when the check cleanly reports the source
    as unreachable. Status changes are pushed to the dashboard immediately.
    """

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if not settings.enable_heartbeat_service:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Heartbeat service started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except Exception:  # noqa: BLE001
                logger.exception("heartbeat tick failed")
            await asyncio.sleep(settings.heartbeat_interval_seconds)

    async def _tick(self) -> None:
        db = SessionLocal()
        try:
            cameras = db.query(Camera).filter(Camera.is_active.is_(True)).all()
            for camera in cameras:
                new_status = await self._probe(camera)
                if new_status != camera.status:
                    camera.status = new_status
                    camera.last_heartbeat = datetime.now(timezone.utc)
                    db.add(camera)
                    db.commit()
                    await manager.broadcast(
                        "camera.status_changed",
                        {"camera_id": camera.id, "status": new_status.value},
                    )
                else:
                    camera.last_heartbeat = datetime.now(timezone.utc)
                    db.add(camera)
                    db.commit()
        finally:
            db.close()

    async def _probe(self, camera: Camera) -> CameraStatus:
        try:
            stream_ref = decrypt_secret(camera.stream_ref_encrypted)
            adapter = get_adapter(camera.id, camera.source_protocol, stream_ref)
            healthy = await asyncio.wait_for(adapter.health_check(), timeout=_CHECK_TIMEOUT_SECONDS)
            return CameraStatus.online if healthy else CameraStatus.offline
        except asyncio.TimeoutError:
            return CameraStatus.degraded
        except Exception:  # noqa: BLE001
            return CameraStatus.offline


heartbeat_service = HeartbeatService()
