import asyncio
import logging
import random

from app.config import get_settings
from app.database import SessionLocal
from app.models import Camera
from app.schemas import DetectionEventIn
from app.services.ingest import ingest_event

logger = logging.getLogger("okdriver.analytics_simulator")
settings = get_settings()

_STATES = ["GJ", "DL", "UP", "MH", "RJ", "HR"]
_VEHICLE_TYPES = ["car", "motorcycle", "truck", "bus", "auto-rickshaw"]


def _random_plate() -> str:
    state = random.choice(_STATES)
    return f"{state}{random.randint(1, 30):02d}{random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}{random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}{random.randint(1000, 9999)}"


class AnalyticsSimulator:
    """Stands in for a real computer-vision pipeline during the demo.

    Every tick it posts a synthetic ANPR/vehicle-detection event through
    `ingest_event` -- the exact function a production model-serving
    service would call over HTTP against `/api/v1/events/ingest`. About a
    third of generated plates are drawn from the live watchlist so the
    match -> alert -> WebSocket flow is visible without waiting.
    """

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if not settings.enable_analytics_simulator:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Analytics simulator started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except Exception:  # noqa: BLE001
                logger.exception("analytics simulator tick failed")
            await asyncio.sleep(settings.analytics_event_interval_seconds)

    async def _tick(self) -> None:
        db = SessionLocal()
        try:
            cameras = db.query(Camera).filter(Camera.is_active.is_(True)).all()
            if not cameras:
                return
            camera = random.choice(cameras)

            watchlist_plate = _pick_watchlist_plate(db)
            use_watchlist = watchlist_plate is not None and random.random() < 0.35
            plate = watchlist_plate if use_watchlist else _random_plate()

            payload = DetectionEventIn(
                camera_id=camera.id,
                event_type="anpr",
                vehicle_number=plate,
                vehicle_type=random.choice(_VEHICLE_TYPES),
                confidence=round(random.uniform(0.78, 0.99), 2),
                bounding_box={
                    "x": random.randint(20, 400),
                    "y": random.randint(20, 200),
                    "w": random.randint(60, 160),
                    "h": random.randint(40, 100),
                },
                source="analytics_simulator",
            )
            await ingest_event(db, payload)
        finally:
            db.close()


def _pick_watchlist_plate(db) -> str | None:
    from app.models import IdentifierType, WatchlistEntry

    entries = (
        db.query(WatchlistEntry)
        .filter(WatchlistEntry.identifier_type == IdentifierType.plate, WatchlistEntry.is_active.is_(True))
        .all()
    )
    if not entries:
        return None
    return random.choice(entries).identifier_value


simulator = AnalyticsSimulator()
