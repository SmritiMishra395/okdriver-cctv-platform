import { useEffect, useState } from "react";
import api from "../api";
import { useAuth } from "../context/AuthContext";

const EMPTY_FORM = {
  category: "stolen_vehicle",
  identifier_type: "plate",
  identifier_value: "",
  label: "",
  description: "",
  risk_level: "medium",
};

export default function Watchlist() {
  const { isAdmin } = useAuth();
  const [entries, setEntries] = useState([]);
  const [q, setQ] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");

  async function load() {
    const { data } = await api.get("/watchlist", { params: q ? { q } : {} });
    setEntries(data);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/watchlist", form);
      setForm(EMPTY_FORM);
      setShowForm(false);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || "Could not create watchlist entry");
    }
  }

  async function deactivate(entry) {
    await api.delete(`/watchlist/${entry.id}`);
    load();
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Watchlist</h1>
        {isAdmin && (
          <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Cancel" : "+ Add record"}
          </button>
        )}
      </div>

      {showForm && (
        <form className="panel form-panel" onSubmit={handleCreate}>
          <div className="form-grid">
            <label>
              Category
              <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                <option value="stolen_vehicle">Stolen vehicle</option>
                <option value="blacklisted_vehicle">Blacklisted vehicle</option>
                <option value="wanted_person">Wanted person</option>
                <option value="missing_person">Missing person</option>
                <option value="other">Other</option>
              </select>
            </label>
            <label>
              Identifier type
              <select value={form.identifier_type} onChange={(e) => setForm({ ...form, identifier_type: e.target.value })}>
                <option value="plate">Vehicle plate</option>
                <option value="face_id">Face ID</option>
                <option value="name">Name / case reference</option>
              </select>
            </label>
            <label>
              Identifier value
              <input required value={form.identifier_value} onChange={(e) => setForm({ ...form, identifier_value: e.target.value })} placeholder="GJ01AB1234" />
            </label>
            <label>
              Risk level
              <select value={form.risk_level} onChange={(e) => setForm({ ...form, risk_level: e.target.value })}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </label>
            <label className="span-2">
              Label
              <input required value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} />
            </label>
            <label className="span-2">
              Description
              <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </label>
          </div>
          {error && <div className="form-error">{error}</div>}
          <button type="submit" className="btn-primary">
            Save record
          </button>
        </form>
      )}

      <div className="filter-row">
        <input placeholder="Search by identifier or label" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Identifier</th>
            <th>Type</th>
            <th>Category</th>
            <th>Label</th>
            <th>Risk</th>
            <th>Added</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.id}>
              <td>
                <code>{entry.identifier_value}</code>
              </td>
              <td>{entry.identifier_type}</td>
              <td>{entry.category.replaceAll("_", " ")}</td>
              <td>{entry.label}</td>
              <td>
                <span className={`severity-pill severity-${entry.risk_level}`}>{entry.risk_level}</span>
              </td>
              <td>{new Date(entry.created_at).toLocaleDateString()}</td>
              <td>
                {isAdmin && (
                  <button className="btn-ghost sm" onClick={() => deactivate(entry)}>
                    Deactivate
                  </button>
                )}
              </td>
            </tr>
          ))}
          {entries.length === 0 && (
            <tr>
              <td colSpan={7} className="empty-state">
                No watchlist entries.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
