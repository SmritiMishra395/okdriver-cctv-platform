import asyncio
import os
import time
from collections.abc import AsyncIterator

import cv2

from app.video.base import StreamUnavailableError, VideoAdapter

_TARGET_FPS = 8


class FileAdapter(VideoAdapter):
    """Loops a recorded video file, standing in for a device with stored/offline footage.

    `stream_ref` is `file:/absolute/or/relative/path.mp4`. The health check
    genuinely opens the file, so an operator who registers a camera with a
    bad path will correctly see it reported Offline on the dashboard rather
    than a hard-coded "online".
    """

    def __init__(self, camera_id: str, stream_ref: str) -> None:
        super().__init__(camera_id, stream_ref)
        _, _, path = stream_ref.partition(":")
        self.path = path

    def _resolve_path(self) -> str:
        if os.path.isabs(self.path):
            return self.path
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base, self.path)

    async def frames(self) -> AsyncIterator[bytes]:
        path = self._resolve_path()
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise StreamUnavailableError(f"cannot open video source: {path}")
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ok, frame = cap.read()
                    if not ok:
                        raise StreamUnavailableError("video source exhausted and could not loop")
                cv2.putText(
                    frame,
                    f"{self.camera_id} | {time.strftime('%Y-%m-%d %H:%M:%S')}",
                    (10, 24),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 230, 120),
                    2,
                )
                ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                if ok:
                    yield buf.tobytes()
                await asyncio.sleep(1 / _TARGET_FPS)
        finally:
            cap.release()

    async def health_check(self) -> bool:
        path = self._resolve_path()
        if not os.path.exists(path):
            return False
        cap = cv2.VideoCapture(path)
        ok = cap.isOpened()
        cap.release()
        return ok
