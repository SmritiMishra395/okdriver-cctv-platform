from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class StreamUnavailableError(Exception):
    """Raised when an adapter cannot produce frames right now."""


class VideoAdapter(ABC):
    """Common interface every camera source implements.

    A registered camera stores `source_protocol` + an encrypted `stream_ref`.
    `registry.get_adapter()` maps that pair to one of these implementations,
    so the rest of the platform (stream relay, health checks) never needs to
    know whether frames come from a simulator, a looped file, or a live
    RTSP/ONVIF device. Adding a real vendor SDK later means adding one more
    adapter class here, not touching any router or the dashboard.
    """

    def __init__(self, camera_id: str, stream_ref: str) -> None:
        self.camera_id = camera_id
        self.stream_ref = stream_ref

    @abstractmethod
    async def frames(self) -> AsyncIterator[bytes]:
        """Yield an unbounded sequence of JPEG-encoded frames."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True when the underlying source is currently reachable."""
