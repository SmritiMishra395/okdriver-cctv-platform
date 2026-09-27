import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(username, password);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-screen">
      <form className="login-card" onSubmit={handleSubmit}>
        <h1>okDriver</h1>
        <p className="login-sub">CCTV Monitoring &amp; Video Analytics Platform</p>

        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>

        {error && <div className="form-error">{error}</div>}

        <button type="submit" className="btn-primary" disabled={busy}>
          {busy ? "Signing in..." : "Sign in"}
        </button>

        <div className="login-hint">
          Demo accounts: <code>admin / Admin@12345</code> (full access) or{" "}
          <code>operator / Operator@12345</code> (monitoring &amp; alert triage)
        </div>
      </form>
    </div>
  );
}
