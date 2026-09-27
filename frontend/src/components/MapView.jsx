import L from "leaflet";
import { MapContainer, Marker, Polyline, Popup, TileLayer } from "react-leaflet";

const STATUS_COLOR = {
  online: "#1fb35a",
  degraded: "#e8a734",
  offline: "#d64545",
};

function dotIcon(color, size = 16) {
  return L.divIcon({
    className: "camera-dot-wrapper",
    html: `<span class="camera-dot" style="--dot-color:${color};width:${size}px;height:${size}px"></span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

const DEFAULT_CENTER = [22.6, 72.4]; // roughly central Gujarat

export default function MapView({ cameras = [], traceHits = [], height = 420, onSelectCamera }) {
  const center =
    cameras.length > 0
      ? [cameras[0].latitude, cameras[0].longitude]
      : traceHits.length > 0
      ? [traceHits[0].latitude, traceHits[0].longitude]
      : DEFAULT_CENTER;

  return (
    <MapContainer center={center} zoom={8} style={{ height, width: "100%", borderRadius: 10 }} scrollWheelZoom={true}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {cameras.map((cam) => (
        <Marker
          key={cam.id}
          position={[cam.latitude, cam.longitude]}
          icon={dotIcon(STATUS_COLOR[cam.status] || "#888")}
          eventHandlers={{ click: () => onSelectCamera?.(cam) }}
        >
          <Popup>
            <strong>
              {cam.id} - {cam.name}
            </strong>
            <br />
            {cam.department}
            <br />
            Status: <span style={{ color: STATUS_COLOR[cam.status] }}>{cam.status}</span>
          </Popup>
        </Marker>
      ))}

      {traceHits.map((hit, idx) => (
        <Marker key={hit.event_id} position={[hit.latitude, hit.longitude]} icon={dotIcon("#3568d4", 14)}>
          <Popup>
            Stop {idx + 1}: {hit.camera_name}
            <br />
            {new Date(hit.timestamp).toLocaleString()}
            <br />
            Confidence: {(hit.confidence * 100).toFixed(0)}%
          </Popup>
        </Marker>
      ))}

      {traceHits.length > 1 && (
        <Polyline
          positions={traceHits.map((h) => [h.latitude, h.longitude])}
          pathOptions={{ color: "#3568d4", weight: 3, dashArray: "6 6" }}
        />
      )}
    </MapContainer>
  );
}
