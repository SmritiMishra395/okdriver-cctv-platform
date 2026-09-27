"""Mock ONVIF discovery.

A real deployment would send a WS-Discovery multicast probe (e.g. via
`onvif-zeep` or `wsdiscovery`) and parse each device's GetCapabilities /
GetStreamUri SOAP responses to obtain its RTSP URL. Multicast discovery
does not work from this sandboxed environment, so this module returns a
fixed, clearly-labelled result shaped exactly like that real response,
so the onboarding flow and adapter selection downstream do not change
when a genuine ONVIF stack is swapped in.
"""

from dataclasses import dataclass


@dataclass
class DiscoveredDevice:
    endpoint_address: str
    manufacturer: str
    model: str
    rtsp_uri: str


def discover(timeout_seconds: float = 2.0) -> list[DiscoveredDevice]:
    return [
        DiscoveredDevice(
            endpoint_address="onvif://mock-nvt-01.local",
            manufacturer="GenericONVIF",
            model="NVT-2MP-IR",
            rtsp_uri="rtsp://198.51.100.10:554/onvif1",
        ),
        DiscoveredDevice(
            endpoint_address="onvif://mock-nvt-02.local",
            manufacturer="GenericONVIF",
            model="NVT-4MP-PTZ",
            rtsp_uri="rtsp://198.51.100.11:554/onvif1",
        ),
    ]
