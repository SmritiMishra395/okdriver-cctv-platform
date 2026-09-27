import { useEffect, useState } from "react";
import api from "../api";
import AlertList from "../components/AlertList";
import { useRealtime } from "../useRealtime";

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");

  async function load() {
    const { data } = await api.get("/alerts", { params: statusFilter ? { status: statusFilter } : {} });
    setAlerts(data);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  useRealtime((msg) => {
    if (msg.type === "alert.new" && (!statusFilter || statusFilter === "new")) {
      setAlerts((prev) => [msg.payload, ...prev]);
    }
    if (msg.type === "alert.updated") {
      load();
    }
  });

  async function acknowledge(alert) {
    await api.patch(`/alerts/${alert.id}`, { status: "acknowledged" });
    load();
  }

  async function resolve(alert) {
    await api.patch(`/alerts/${alert.id}`, { status: "resolved" });
    load();
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Alerts</h1>
      </div>
      <div className="filter-row">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="new">New</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="resolved">Resolved</option>
        </select>
      </div>
      <div className="panel">
        <AlertList alerts={alerts} onAcknowledge={acknowledge} onResolve={resolve} />
      </div>
    </div>
  );
}
