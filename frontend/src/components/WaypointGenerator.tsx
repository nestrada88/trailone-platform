import { useState } from "react";
import { DistanceMethod, generateWaypoints } from "../api/client";

function triggerDownload(blob: Blob, filename: string) {
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(objectUrl);
}

export default function WaypointGenerator() {
  const [file, setFile] = useState<File | null>(null);
  const [trailPrefix, setTrailPrefix] = useState("TRK");
  const [stepSize, setStepSize] = useState(1);
  const [distanceMethod, setDistanceMethod] = useState<DistanceMethod>("auto");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function onGenerate() {
    if (!file) {
      setError("Select a GPX file before waypoint generation.");
      return;
    }

    setBusy(true);
    setError("");
    setMessage("");

    try {
      const payload = await generateWaypoints(file, trailPrefix, stepSize, distanceMethod);
      const filename = payload.filename ?? "generated_waypoints.gpx";
      triggerDownload(payload.blob, filename);
      setMessage(
        `Generated waypoint GPX downloaded as ${filename}${
          payload.generatedCount ? ` (${payload.generatedCount} waypoints)` : ""
        }.`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Waypoint generation failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Generate waypoints</h2>
      </div>

      <div className="grid two-col">
        <label className="field">
          <span>GPX file</span>
          <input
            type="file"
            accept=".gpx,application/gpx+xml"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>

        <label className="field">
          <span>Trail prefix</span>
          <input
            value={trailPrefix}
            maxLength={6}
            onChange={(event) => setTrailPrefix(event.target.value.toUpperCase())}
            placeholder="LCST"
          />
        </label>

        <label className="field">
          <span>Step size (km)</span>
          <input
            type="number"
            min="0.1"
            max="100"
            step="0.1"
            value={stepSize}
            onChange={(event) => setStepSize(Number(event.target.value))}
          />
        </label>

        <label className="field">
          <span>Distance method</span>
          <select
            value={distanceMethod}
            onChange={(event) => setDistanceMethod(event.target.value as DistanceMethod)}
          >
            <option value="auto">auto</option>
            <option value="geodesic">geodesic</option>
            <option value="haversine">haversine</option>
          </select>
        </label>
      </div>

      <div className="actions">
        <button className="button" onClick={onGenerate} disabled={busy}>
          {busy ? "Generating..." : "Generate and download"}
        </button>
      </div>

      {message ? <p className="success">{message}</p> : null}
      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}
