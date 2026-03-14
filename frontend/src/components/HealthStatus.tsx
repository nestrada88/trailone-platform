import { useEffect, useState } from "react";
import { getReadyHealth } from "../api/client";

export default function HealthStatus() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    getReadyHealth()
      .then((payload) => {
        setStatus(payload);
        setError("");
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>API readiness</h2>
      </div>

      {error ? <p className="error">{error}</p> : null}
      {!error && !status ? <p className="muted">Loading API status...</p> : null}
      {status ? <pre className="result-block">{JSON.stringify(status, null, 2)}</pre> : null}
    </section>
  );
}
