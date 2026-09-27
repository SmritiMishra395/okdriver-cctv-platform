const SEVERITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };

function formatTime(ts) {
  return new Date(ts).toLocaleString();
}

export default function AlertList({ alerts, onAcknowledge, onResolve, compact = false }) {
  if (!alerts.length) {
    return <div className="empty-state">No alerts to show.</div>;
  }

  const sorted = [...alerts].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9) || new Date(b.timestamp) - new Date(a.timestamp)
  );

  return (
    <div className="alert-list">
      {sorted.map((alert) => (
        <div key={alert.id} className={`alert-row severity-${alert.severity}`}>
          <div className="alert-main">
            <span className={`severity-pill severity-${alert.severity}`}>{alert.severity}</span>
            <div>
              <div className="alert-title">
                {alert.matched_identifier} · {alert.alert_type.replaceAll("_", " ")}
              </div>
              {!compact && (
                <div className="alert-meta">
                  Camera {alert.camera_id} · {formatTime(alert.timestamp)} · confidence{" "}
                  {(alert.confidence * 100).toFixed(0)}%
                </div>
              )}
            </div>
          </div>
          <div className="alert-actions">
            <span className={`status-pill status-${alert.status}`}>{alert.status}</span>
            {!compact && alert.status === "new" && (
              <button className="btn-ghost sm" onClick={() => onAcknowledge?.(alert)}>
                Acknowledge
              </button>
            )}
            {!compact && alert.status !== "resolved" && (
              <button className="btn-ghost sm" onClick={() => onResolve?.(alert)}>
                Resolve
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
