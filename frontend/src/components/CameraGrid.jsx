import { useState } from "react";
import { streamUrl } from "../api";

const STATUS_LABEL = { online: "Online", offline: "Offline", degraded: "Degraded" };

function CameraTile({ camera }) {
  const [failed, setFailed] = useState(false);
  const canPlay = camera.status === "online";

  return (
    <div className="camera-tile">
      <div className="camera-tile-video">
        {canPlay && !failed ? (
          <img
            src={streamUrl(camera.id)}
            alt={`${camera.id} live feed`}
            onError={() => setFailed(true)}
          />
        ) : (
          <div className="camera-tile-placeholder">Feed unavailable</div>
        )}
        <span className={`status-badge status-${camera.status}`}>{STATUS_LABEL[camera.status]}</span>
      </div>
      <div className="camera-tile-info">
        <strong>
          {camera.id} · {camera.name}
        </strong>
        <span>{camera.department}</span>
      </div>
    </div>
  );
}

export default function CameraGrid({ cameras }) {
  if (!cameras.length) {
    return <div className="empty-state">No cameras registered yet.</div>;
  }
  return (
    <div className="camera-grid">
      {cameras.map((cam) => (
        <CameraTile key={cam.id} camera={cam} />
      ))}
    </div>
  );
}
