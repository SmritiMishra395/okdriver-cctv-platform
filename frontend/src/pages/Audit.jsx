import { useEffect, useState } from "react";
import api from "../api";

export default function Audit() {
  const [logs, setLogs] = useState([]);
  const [entityType, setEntityType] = useState("");

  async function load() {
    const { data } = await api.get("/audit", { params: entityType ? { entity_type: entityType } : {} });
    setLogs(data);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entityType]);

  return (
    <div className="page">
      <div className="page-header">
        <h1>Audit log</h1>
      </div>
      <div className="filter-row">
        <select value={entityType} onChange={(e) => setEntityType(e.target.value)}>
          <option value="">All entities</option>
          <option value="camera">Cameras</option>
          <option value="watchlist_entry">Watchlist</option>
          <option value="alert">Alerts</option>
          <option value="user">Users</option>
        </select>
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Actor</th>
            <th>Action</th>
            <th>Entity</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id}>
              <td>{new Date(log.created_at).toLocaleString()}</td>
              <td>{log.actor_username || "system"}</td>
              <td>{log.action}</td>
              <td>
                {log.entity_type} {log.entity_id ? `· ${log.entity_id}` : ""}
              </td>
              <td className="details-cell">{JSON.stringify(log.details)}</td>
            </tr>
          ))}
          {logs.length === 0 && (
            <tr>
              <td colSpan={5} className="empty-state">
                No audit entries.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
