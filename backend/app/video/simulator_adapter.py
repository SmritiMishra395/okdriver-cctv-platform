import asyncio
import io
import math
import time
from collections.abc import AsyncIterator

from PIL import Image, ImageDraw, ImageFont

from app.video.base import VideoAdapter

_WIDTH, _HEIGHT = 640, 360
_FPS = 6


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype("DejaVuSansMono.ttf", size)
    except OSError:
        return ImageFont.load_default()


_FONT = _load_font(14)
_FONT_BIG = _load_font(18)


class SimulatorAdapter(VideoAdapter):
    """Synthetic camera feed: a procedurally generated junction scene.

    Stands in for a real fixed camera when no physical device is wired up.
    `stream_ref` looks like `simulator:C001:Ahmedabad Ring Road Junction`
    and only controls the on-screen label, so several cameras can each get
    a distinct-looking feed without any external media dependency.
    """

    def __init__(self, camera_id: str, stream_ref: str) -> None:
        super().__init__(camera_id, stream_ref)
        parts = stream_ref.split(":", 2)
        self.label = parts[2] if len(parts) > 2 else camera_id
        self._seed = sum(ord(c) for c in camera_id)

    def _render_frame(self, tick: int) -> bytes:
        img = Image.new("RGB", (_WIDTH, _HEIGHT), color=(28, 32, 38))
        draw = ImageDraw.Draw(img)

        draw.rectangle([0, _HEIGHT - 90, _WIDTH, _HEIGHT], fill=(40, 44, 50))
        for lane in range(1, 4):
            x = lane * _WIDTH // 4
            draw.line([(x, _HEIGHT - 90), (x, _HEIGHT)], fill=(90, 90, 90), width=2)

        phase = (tick + self._seed) * 0.12
        for i in range(3):
            offset = i * 2.4
            x = int((math.sin(phase + offset) * 0.5 + 0.5) * (_WIDTH - 60))
            y = _HEIGHT - 60 - (i * 8)
            color = [(60, 140, 230), (230, 160, 40), (90, 200, 120)][i % 3]
            draw.rectangle([x, y, x + 46, y + 26], fill=color, outline=(15, 15, 15))
            draw.text((x + 4, y + 6), f"V{i+1}", font=_FONT, fill=(15, 15, 15))

        draw.rectangle([0, 0, _WIDTH, 34], fill=(0, 0, 0))
        draw.text((8, 8), f"{self.camera_id} | {self.label}", font=_FONT_BIG, fill=(255, 255, 255))
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        draw.text((_WIDTH - 168, 8), ts, font=_FONT, fill=(0, 230, 120))
        draw.text((8, _HEIGHT - 20), "SIMULATED SOURCE", font=_FONT, fill=(255, 90, 90))

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        return buf.getvalue()

    async def frames(self) -> AsyncIterator[bytes]:
        tick = 0
        while True:
            yield self._render_frame(tick)
            tick += 1
            await asyncio.sleep(1 / _FPS)

    async def health_check(self) -> bool:
        return True
