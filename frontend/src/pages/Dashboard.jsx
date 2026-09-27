import { useCallback, useEffect, useState } from "react";
import api from "../api";
import AlertList from "../components/AlertList";
import CameraGrid from "../components/CameraGrid";
import MapView from "../components/MapView";
import StatCard from "../components/StatCard";
import { useRealtime } from "../useRealtime";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [cameras, setCameras] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [events, setEvents] = useState([]);

  const loadAll = useCallback(async () => {
    const [statsRes, camerasRes, alertsRes, eventsRes] = await Promise.all([
      api.get("/stats/summary"),
      api.get("/cameras"),
      api.get("/alerts", { params: { limit: 8 } }),
      api.get("/events", { params: { limit: 10 } }),
    ]);
    setStats(statsRes.data);
    setCameras(camerasRes.data);
    setAlerts(alertsRes.data);
    setEvents(eventsRes.data);
  }, []);

  useEffect(() => {
    loadAll();
    const interval = setInterval(() => api.get("/stats/summary").then((r) => setStats(r.data)), 15000);
    return () => clearInterval(interval);
  }, [loadAll]);

  useRealtime((msg) => {
    if (msg.type === "alert.new") {
      setAlerts((prev) => [msg.payload, ...prev].slice(0, 8));
    }
    if (msg.type === "event.new") {
      setEvents((prev) => [msg.payload, ...prev].slice(0, 10));
    }
    if (msg.type === "camera.status_changed") {
      setCameras((prev) =>
        prev.map((c) => (c.id === msg.payload.camera_id ? { ...c, status: msg.payload.status } : c))
      );
    }
  });

  if (!stats) return <div className="empty-state">Loading dashboard...</div>;

  return (
    <div className="page dashboard-page">
      <div className="stat-row">
        <StatCard label="Cameras total" value={stats.cameras_total} />
        <StatCard label="Online" value={stats.cameras_online} tone="good" />
        <StatCard label="Degraded" value={stats.cameras_degraded} tone="warn" />
        <StatCard label="Offline" value={stats.cameras_offline} tone="bad" />
        <StatCard label="Events (24h)" value={stats.events_last_24h} />
        <StatCard label="Active alerts" value={stats.alerts_active} tone={stats.alerts_active > 0 ? "warn" : "default"} />
        <StatCard label="Critical alerts" value={stats.alerts_critical} tone={stats.alerts_critical > 0 ? "bad" : "default"} />
        <StatCard label="Watchlist size" value={stats.watchlist_entries} />
      </div>

      <div className="two-col">
        <section className="panel">
          <h2>Camera map</h2>
          <MapView cameras={cameras} height={360} />
        </section>
        <section className="panel">
          <h2>Active alerts</h2>
          <AlertList alerts={alerts} compact />
        </section>
      </div>

      <section className="panel">
        <h2>Live camera grid</h2>
        <CameraGrid cameras={cameras} />
      </section>

      <section className="panel">
        <h2>Recent detection events</h2>
        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Camera</th>
              <th>Type</th>
              <th>Identifier</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id}>
                <td>{new Date(e.timestamp).toLocaleTimeString()}</td>
                <td>{e.camera_id}</td>
                <td>{e.event_type}</td>
                <td>{e.vehicle_number || e.person_ref || "-"}</td>
                <td>{(e.confidence * 100).toFixed(0)}%</td>
              </tr>
            ))}
            {events.length === 0 && (
              <tr>
                <td colSpan={5} className="empty-state">
                  No events yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
