import asyncio
import socket
from collections.abc import AsyncIterator
from urllib.parse import urlparse

import cv2

from app.video.base import StreamUnavailableError, VideoAdapter

_TARGET_FPS = 8
_OPEN_TIMEOUT_MS = 4000
_TCP_PRECHECK_TIMEOUT_SECONDS = 2.0


def _tcp_reachable(url: str, timeout: float = _TCP_PRECHECK_TIMEOUT_SECONDS) -> bool:
    """Raw TCP connect test, run before ever handing control to OpenCV/FFmpeg.

    `cv2.VideoCapture` on an unreachable RTSP host can block for a long time
    inside native FFmpeg code that does not reliably honor
    `CAP_PROP_OPEN_TIMEOUT_MSEC` on every build, and a blocking native call
    like that can stall the asyncio event loop for everyone even when it is
    dispatched via `asyncio.to_thread`. A plain `socket.connect` with
    `settimeout` is implemented on top of `select`/`poll`, which reliably
    releases the GIL and respects the timeout, so this cheaply screens out
    unreachable hosts (as with the sample TEST-NET camera in the seed data)
    without ever risking that hang.
    """
    parsed = urlparse(url)
    host, port = parsed.hostname, parsed.port or 554
    if not host:
        return False
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


class RTSPAdapter(VideoAdapter):
    """Live RTSP/vendor-stream adapter.

    `stream_ref` is `rtsp://user:pass@host:port/path`. This is a real,
    functional implementation (OpenCV + FFmpeg backend) rather than a stub;
    it simply has no physical camera to connect to in this environment.
    Point a camera's `stream_ref` at any reachable RTSP endpoint and it
    works unchanged. The same class also covers ONVIF-profile devices once
    `onvif_adapter.discover()` has resolved their RTSP URL.
    """

    def __init__(self, camera_id: str, stream_ref: str) -> None:
        super().__init__(camera_id, stream_ref)

    def _open(self) -> cv2.VideoCapture:
        cap = cv2.VideoCapture(self.stream_ref, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, _OPEN_TIMEOUT_MS)
        return cap

    async def frames(self) -> AsyncIterator[bytes]:
        if not await asyncio.to_thread(_tcp_reachable, self.stream_ref):
            raise StreamUnavailableError(f"RTSP host unreachable for {self.camera_id}")

        cap = await asyncio.to_thread(self._open)
        if not cap.isOpened():
            raise StreamUnavailableError(f"cannot open RTSP source for {self.camera_id}")
        try:
            while True:
                ok, frame = await asyncio.to_thread(cap.read)
                if not ok:
                    raise StreamUnavailableError("RTSP stream dropped")
                ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                if ok:
                    yield buf.tobytes()
                await asyncio.sleep(1 / _TARGET_FPS)
        finally:
            cap.release()

    async def health_check(self) -> bool:
        if not await asyncio.to_thread(_tcp_reachable, self.stream_ref):
            return False
        try:
            cap = await asyncio.to_thread(self._open)
            ok = cap.isOpened()
            cap.release()
            return ok
        except Exception:  # noqa: BLE001
            return False
