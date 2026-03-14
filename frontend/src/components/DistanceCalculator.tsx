import { useState } from "react";
import { DistanceMethod, DistanceResponse, calculateDistance } from "../api/client";

type PointState = {
  latitude: string;
  longitude: string;
  elevation: string;
};

const initialPointA: PointState = {
  latitude: "12.1483",
  longitude: "-86.2711",
  elevation: "56"
};

const initialPointB: PointState = {
  latitude: "12.1612",
  longitude: "-86.2417",
  elevation: "89"
};

function normalizePoint(point: PointState) {
  return {
    latitude: Number(point.latitude),
    longitude: Number(point.longitude),
    elevation: point.elevation === "" ? null : Number(point.elevation)
  };
}

export default function DistanceCalculator() {
  const [point1, setPoint1] = useState<PointState>(initialPointA);
  const [point2, setPoint2] = useState<PointState>(initialPointB);
  const [distanceMethod, setDistanceMethod] = useState<DistanceMethod>("auto");
  const [datasetSize, setDatasetSize] = useState("2");
  const [result, setResult] = useState<DistanceResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function onCalculate() {
    setBusy(true);
    setError("");
    setResult(null);

    try {
      const payload = await calculateDistance({
        point1: normalizePoint(point1),
        point2: normalizePoint(point2),
        distance_method: distanceMethod,
        dataset_size: datasetSize ? Number(datasetSize) : undefined
      });
      setResult(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Distance calculation failed.");
    } finally {
      setBusy(false);
    }
  }

  const renderPointInputs = (
    label: string,
    point: PointState,
    setPoint: React.Dispatch<React.SetStateAction<PointState>>
  ) => (
    <fieldset className="fieldset">
      <legend>{label}</legend>
      <label className="field">
        <span>Latitude</span>
        <input
          type="number"
          step="0.000001"
          value={point.latitude}
          onChange={(event) => setPoint((current) => ({ ...current, latitude: event.target.value }))}
        />
      </label>
      <label className="field">
        <span>Longitude</span>
        <input
          type="number"
          step="0.000001"
          value={point.longitude}
          onChange={(event) => setPoint((current) => ({ ...current, longitude: event.target.value }))}
        />
      </label>
      <label className="field">
        <span>Elevation (m)</span>
        <input
          type="number"
          step="0.1"
          value={point.elevation}
          onChange={(event) => setPoint((current) => ({ ...current, elevation: event.target.value }))}
        />
      </label>
    </fieldset>
  );

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>3D distance calculator</h2>
      </div>

      <div className="grid two-col">
        {renderPointInputs("Point A", point1, setPoint1)}
        {renderPointInputs("Point B", point2, setPoint2)}

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

        <label className="field">
          <span>Dataset size</span>
          <input
            type="number"
            min="2"
            value={datasetSize}
            onChange={(event) => setDatasetSize(event.target.value)}
          />
        </label>
      </div>

      <div className="actions">
        <button className="button" onClick={onCalculate} disabled={busy}>
          {busy ? "Calculating..." : "Calculate distance"}
        </button>
      </div>

      {error ? <p className="error">{error}</p> : null}
      {result ? <pre className="result-block">{JSON.stringify(result, null, 2)}</pre> : null}
    </section>
  );
}
