import { useEffect, useState } from "react";
import api, { streamUrl } from "../api";
import MapView from "../components/MapView";
import { useAuth } from "../context/AuthContext";
import { useRealtime } from "../useRealtime";

const EMPTY_FORM = {
  id: "",
  name: "",
  department: "",
  zone: "",
  camera_type: "fixed",
  latitude: "",
  longitude: "",
  source_protocol: "simulator",
  stream_ref: "",
  storage_tier: "hot",
  retention_days: 30,
};

export default function Cameras() {
  const { isAdmin } = useAuth();
  const [cameras, setCameras] = useState([]);
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [previewCamera, setPreviewCamera] = useState(null);
  const [error, setError] = useState("");

  async function load() {
    const params = {};
    if (q) params.q = q;
    if (statusFilter) params.status = statusFilter;
    const { data } = await api.get("/cameras", { params });
    setCameras(data);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, statusFilter]);

  useRealtime((msg) => {
    if (msg.type === "camera.status_changed") {
      setCameras((prev) =>
        prev.map((c) => (c.id === msg.payload.camera_id ? { ...c, status: msg.payload.status } : c))
      );
    }
  });

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/cameras", {
        ...form,
        latitude: parseFloat(form.latitude),
        longitude: parseFloat(form.longitude),
        retention_days: parseInt(form.retention_days, 10),
      });
      setForm(EMPTY_FORM);
      setShowForm(false);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || "Could not create camera");
    }
  }

  async function toggleActive(camera) {
    const action = camera.is_active ? "disable" : "enable";
    await api.post(`/cameras/${camera.id}/${action}`);
    load();
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Camera registry</h1>
        {isAdmin && (
          <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Cancel" : "+ Add camera"}
          </button>
        )}
      </div>

      {showForm && (
        <form className="panel form-panel" onSubmit={handleCreate}>
          <div className="form-grid">
            <label>
              Camera ID
              <input required value={form.id} onChange={(e) => setForm({ ...form, id: e.target.value })} placeholder="C006" />
            </label>
            <label>
              Name
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </label>
            <label>
              Department
              <input required value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} />
            </label>
            <label>
              Zone
              <input value={form.zone} onChange={(e) => setForm({ ...form, zone: e.target.value })} />
            </label>
            <label>
              Latitude
              <input required type="number" step="any" value={form.latitude} onChange={(e) => setForm({ ...form, latitude: e.target.value })} />
            </label>
            <label>
              Longitude
              <input required type="number" step="any" value={form.longitude} onChange={(e) => setForm({ ...form, longitude: e.target.value })} />
            </label>
            <label>
              Source protocol
              <select value={form.source_protocol} onChange={(e) => setForm({ ...form, source_protocol: e.target.value })}>
                <option value="simulator">Simulator</option>
                <option value="file">Recorded file</option>
                <option value="rtsp">RTSP</option>
                <option value="onvif">ONVIF</option>
              </select>
            </label>
            <label>
              Stream reference
              <input
                required
                value={form.stream_ref}
                onChange={(e) => setForm({ ...form, stream_ref: e.target.value })}
                placeholder="simulator:C006:Junction name  |  rtsp://user:pass@host/stream"
              />
            </label>
            <label>
              Storage tier
              <select value={form.storage_tier} onChange={(e) => setForm({ ...form, storage_tier: e.target.value })}>
                <option value="hot">Hot</option>
                <option value="warm">Warm</option>
                <option value="cold">Cold</option>
              </select>
            </label>
            <label>
              Retention (days)
              <input type="number" min={1} value={form.retention_days} onChange={(e) => setForm({ ...form, retention_days: e.target.value })} />
            </label>
          </div>
          {error && <div className="form-error">{error}</div>}
          <button type="submit" className="btn-primary">
            Save camera
          </button>
        </form>
      )}

      <div className="panel">
        <MapView cameras={cameras} height={320} onSelectCamera={setPreviewCamera} />
      </div>

      <div className="filter-row">
        <input placeholder="Search by ID or name" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="online">Online</option>
          <option value="degraded">Degraded</option>
          <option value="offline">Offline</option>
        </select>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Department</th>
            <th>Zone</th>
            <th>Protocol</th>
            <th>Status</th>
            <th>Last heartbeat</th>
            <th>Active</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {cameras.map((cam) => (
            <tr key={cam.id}>
              <td>{cam.id}</td>
              <td>{cam.name}</td>
              <td>{cam.department}</td>
              <td>{cam.zone || "-"}</td>
              <td>{cam.source_protocol}</td>
              <td>
                <span className={`status-chip status-${cam.status}`}>{cam.status}</span>
              </td>
              <td>{cam.last_heartbeat ? new Date(cam.last_heartbeat).toLocaleTimeString() : "-"}</td>
              <td>{cam.is_active ? "Yes" : "No"}</td>
              <td className="row-actions">
                <button className="btn-ghost sm" onClick={() => setPreviewCamera(cam)}>
                  Preview
                </button>
                {isAdmin && (
                  <button className="btn-ghost sm" onClick={() => toggleActive(cam)}>
                    {cam.is_active ? "Disable" : "Enable"}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {previewCamera && (
        <div className="modal-backdrop" onClick={() => setPreviewCamera(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3>
              {previewCamera.id} · {previewCamera.name}
            </h3>
            {previewCamera.status === "online" ? (
              <img className="preview-video" src={streamUrl(previewCamera.id)} alt="live preview" />
            ) : (
              <div className="camera-tile-placeholder">Feed unavailable - camera {previewCamera.status}</div>
            )}
            <button className="btn-ghost" onClick={() => setPreviewCamera(null)}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
