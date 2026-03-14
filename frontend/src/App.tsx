import WaypointGenerator from "./components/WaypointGenerator";

export default function App() {
  return (
    <main className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">TrailOne</p>
          <h1>GPX Toolkit</h1>
          <p className="lead">
            GPX trail enrichment utility for hiking datasets. It ingests a GPX track, validates structural integrity,
            computes elevation statistics and cumulative 3D distance, generates trail markers at fixed intervals and
            key topographic locations, and outputs an enriched GPX 1.1 file that preserves original geometry while
            adding structured navigation metadata.
          </p>
          <ul>
            <li>3D cumulative path distance computation</li>
            <li>Elevation statistics and terrain metrics</li>
            <li>Automated waypoint interpolation</li>
            <li>Topographic marker generation</li>
            <li>GPX 1.1 compliant enriched output</li>
          </ul>
        </div>
      </header>
      <WaypointGenerator />
    </main>
  );
}
