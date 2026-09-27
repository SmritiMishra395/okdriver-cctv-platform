import { useState } from "react";
import api from "../api";
import MapView from "../components/MapView";

export default function Trace() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [trace, setTrace] = useState(null);
  const [error, setError] = useState("");

  async function handleSearch(e) {
    e.preventDefault();
    if (!query.trim()) return;
    const { data } = await api.get("/entities/search", { params: { q: query } });
    setSuggestions(data);
    if (data.length === 1) {
      loadTrace(data[0].identifier);
    }
  }

  async function loadTrace(identifier) {
    setError("");
    try {
      const { data } = await api.get(`/trace/${identifier}`);
      setTrace(data);
      setSuggestions([]);
      setQuery(identifier);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not load trace");
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Vehicle / entity trace</h1>
      </div>

      <form className="panel form-panel" onSubmit={handleSearch}>
        <div className="filter-row">
          <input
            placeholder="Enter a vehicle number, e.g. GJ01AB1234"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button className="btn-primary" type="submit">
            Search
          </button>
        </div>
      </form>

      {suggestions.length > 1 && (
        <div className="panel">
          <h3>Matches</h3>
          <ul className="suggestion-list">
            {suggestions.map((s) => (
              <li key={s.identifier}>
                <button className="btn-ghost sm" onClick={() => loadTrace(s.identifier)}>
                  {s.identifier} {s.is_watchlisted && <span className="severity-pill severity-high">watchlisted</span>} - {s.sightings} sightings
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {error && <div className="form-error">{error}</div>}

      {trace && (
        <>
          <div className="panel">
            <div className="page-header">
              <h2>
                {trace.identifier}{" "}
                {trace.is_watchlisted && <span className="severity-pill severity-high">Watchlisted</span>}
              </h2>
            </div>
            {trace.watchlist_entry && (
              <p className="trace-watchlist-note">
                {trace.watchlist_entry.label} - {trace.watchlist_entry.description}
              </p>
            )}
            <MapView traceHits={trace.hits} cameras={[]} height={380} />
          </div>

          <div className="panel">
            <h2>Movement history</h2>
            {trace.hits.length === 0 ? (
              <div className="empty-state">No detections recorded for this identifier yet.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Time</th>
                    <th>Camera</th>
                    <th>Event type</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {trace.hits.map((hit, idx) => (
                    <tr key={hit.event_id}>
                      <td>{idx + 1}</td>
                      <td>{new Date(hit.timestamp).toLocaleString()}</td>
                      <td>
                        {hit.camera_id} - {hit.camera_name}
                      </td>
                      <td>{hit.event_type}</td>
                      <td>{(hit.confidence * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
