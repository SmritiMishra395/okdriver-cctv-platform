from app.models import SourceProtocol
from app.video.base import VideoAdapter
from app.video.file_adapter import FileAdapter
from app.video.rtsp_adapter import RTSPAdapter
from app.video.simulator_adapter import SimulatorAdapter

_ADAPTERS: dict[SourceProtocol, type[VideoAdapter]] = {
    SourceProtocol.simulator: SimulatorAdapter,
    SourceProtocol.file: FileAdapter,
    SourceProtocol.rtsp: RTSPAdapter,
    SourceProtocol.onvif: RTSPAdapter,  # ONVIF profile resolves to an RTSP URI, see onvif_adapter.py
}


def get_adapter(camera_id: str, source_protocol: SourceProtocol, stream_ref: str) -> VideoAdapter:
    adapter_cls = _ADAPTERS.get(source_protocol)
    if adapter_cls is None:
        raise ValueError(f"no adapter registered for protocol {source_protocol}")
    return adapter_cls(camera_id, stream_ref)
