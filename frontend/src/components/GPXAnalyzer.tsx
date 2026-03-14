import { useState } from "react";
import { AnalyzeResponse, analyzeGpx } from "../api/client";

export default function GPXAnalyzer() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function onAnalyze() {
    if (!file) {
      setError("Select a GPX file before analysis.");
      return;
    }

    setBusy(true);
    setError("");
    setResult(null);

    try {
      const payload = await analyzeGpx(file);
      setResult(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Analyze GPX</h2>
      </div>

      <div className="grid">
        <label className="field">
          <span>GPX file</span>
          <input
            type="file"
            accept=".gpx,application/gpx+xml"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>
      </div>

      <div className="actions">
        <button className="button" onClick={onAnalyze} disabled={busy}>
          {busy ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {error ? <p className="error">{error}</p> : null}
      {result ? <pre className="result-block">{JSON.stringify(result, null, 2)}</pre> : null}
    </section>
  );
}
