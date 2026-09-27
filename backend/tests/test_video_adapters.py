import asyncio
import time

import pytest

from app.video.file_adapter import FileAdapter
from app.video.rtsp_adapter import RTSPAdapter
from app.video.simulator_adapter import SimulatorAdapter


@pytest.mark.asyncio
async def test_simulator_health_check_is_always_true():
    adapter = SimulatorAdapter("TCAM", "simulator:TCAM:Test")
    assert await adapter.health_check() is True


@pytest.mark.asyncio
async def test_file_adapter_reports_offline_for_missing_file():
    adapter = FileAdapter("TCAM", "file:media/sample/does-not-exist.mp4")
    assert await adapter.health_check() is False


@pytest.mark.asyncio
async def test_rtsp_health_check_never_blocks_the_event_loop():
    """Regression test for a real incident hit while building this platform:
    cv2.VideoCapture() against an unreachable RTSP host can block inside
    native FFmpeg code for a long time without releasing control back to
    asyncio, which stalls every other request on the same process --
    including completely unrelated ones like /health. The fix does a raw
    TCP pre-check (see rtsp_adapter._tcp_reachable) before ever calling into
    OpenCV. This test asserts the whole check completes well within a few
    seconds against a non-routable address, proving the pre-check is what
    actually runs first.
    """
    adapter = RTSPAdapter("TCAM", "rtsp://198.51.100.77:554/stream1")

    started = time.monotonic()
    result = await asyncio.wait_for(adapter.health_check(), timeout=5)
    elapsed = time.monotonic() - started

    assert result is False
    assert elapsed < 5
