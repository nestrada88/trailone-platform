import { useState } from "react";
import { AnalyzeResponse, DistanceMethod, analyzeGpx, generateWaypoints } from "../api/client";

type Stage = 0 | 1 | 2 | 3 | 4;
const stages = [
  { label: "Import", detail: "Select & validate" },
  { label: "Configure", detail: "Set marker rules" },
  { label: "Generate", detail: "Create GPX data" },
  { label: "Review", detail: "Verify output" },
  { label: "Export", detail: "Save GPX file" },
] as const;

type GeneratedOutput = {
  blob: Blob;
  filename: string;
  count: number;
  trackPoints: number;
  waypointNames: string[];
};

function fileSize(bytes: number): string {
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(2)} MB` : `${(bytes / 1024).toFixed(1)} KB`;
}

function displayMeters(value: number): string {
  return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 }).format(value)} m`;
}

async function verifyOutput(
  blob: Blob,
  filename: string,
  generatedHeader: string | null,
  originalPoints: number,
  sourceFile: File
): Promise<GeneratedOutput> {
  const parser = new DOMParser();
  const sourceXml = parser.parseFromString(await sourceFile.text(), "application/xml");
  if (sourceXml.getElementsByTagName("parsererror").length || sourceXml.documentElement.localName !== "gpx") {
    throw new Error("Source GPX could not be re-read for marker verification.");
  }
  const originalWaypointCount = sourceXml.getElementsByTagNameNS("*", "wpt").length;
  const xml = parser.parseFromString(await blob.text(), "application/xml");
  if (xml.getElementsByTagName("parsererror").length || xml.documentElement.localName !== "gpx") {
    throw new Error("Generated output could not be parsed as GPX XML. Export has been stopped.");
  }

  const waypoints = Array.from(xml.getElementsByTagNameNS("*", "wpt"));
  const trackPoints = xml.getElementsByTagNameNS("*", "trkpt").length;
  if (trackPoints !== originalPoints) {
    throw new Error(`Track point verification failed: expected ${originalPoints}, received ${trackPoints}. Export has been stopped.`);
  }
  const generatedCount = waypoints.length - originalWaypointCount;
  if (generatedCount < 0 || generatedHeader === null || Number(generatedHeader) !== generatedCount) {
    throw new Error("Generated waypoint count is inconsistent with the source file or API metadata. Export has been stopped.");
  }
  return {
    blob,
    filename,
    count: generatedCount,
    trackPoints,
    waypointNames: waypoints.slice(originalWaypointCount).map(
      element => element.getElementsByTagNameNS("*", "name")[0]?.textContent ?? "Unnamed marker"
    ),
  };
}

export default function GuidedGPXWorkflow() {
  const [stage, setStage] = useState<Stage>(0);
  const [maxReached, setMaxReached] = useState<Stage>(0);
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [prefix, setPrefix] = useState("TRK");
  const [interval, setIntervalValue] = useState("1");
  const [method, setMethod] = useState<DistanceMethod>("auto");
  const [output, setOutput] = useState<GeneratedOutput | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const intervalNumber = Number(interval);
  const configurationValid = /^[A-Z]{3,6}$/.test(prefix) && interval.trim() !== "" && Number.isFinite(intervalNumber) && intervalNumber > 0 && intervalNumber <= 100;
  const accessible: boolean[] = [true, analysis !== null, analysis !== null && configurationValid, output !== null, output !== null && confirmed];

  function clearFeedback() { setError(""); setNotice(""); }
  function invalidateOutput() { setOutput(null); setConfirmed(false); }
  function chooseFile(next: File | null) {
    clearFeedback(); setFile(next); setAnalysis(null); invalidateOutput(); setStage(0); setMaxReached(0);
    if (next && !next.name.toLowerCase().endsWith(".gpx")) setError("Choose a file with the .gpx extension.");
  }
  function changeConfig() { clearFeedback(); invalidateOutput(); setMaxReached(1); }
  function navigate(target: Stage) {
    if (!busy && target <= maxReached && accessible[target]) { clearFeedback(); setStage(target); }
  }

  async function importFile() {
    if (!file || !file.name.toLowerCase().endsWith(".gpx")) { setError("Select a valid .gpx file before continuing."); return; }
    setBusy(true); clearFeedback();
    try {
      const result = await analyzeGpx(file);
      setAnalysis(result);
      invalidateOutput();
      setStage(1); setMaxReached(1);
      setNotice("GPX validation completed. Review the analysis and configure marker generation.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "GPX validation failed.");
    } finally { setBusy(false); }
  }

  function submitConfiguration() {
    clearFeedback();
    if (!configurationValid) { setError("Prefix must contain 3–6 uppercase letters; interval must be greater than 0 and no more than 100 km."); return; }
    setStage(2); setMaxReached(2);
  }

  async function createOutput() {
    if (!file || !analysis || !configurationValid) { setError("A validated GPX file and a valid configuration are required."); return; }
    setBusy(true); clearFeedback(); invalidateOutput();
    try {
      const response = await generateWaypoints(file, prefix, intervalNumber, method);
      const result = await verifyOutput(response.blob, response.filename ?? "trailone_waypoints.gpx", response.generatedCount, analysis.total_points, file);
      setOutput(result); setStage(3); setMaxReached(3);
      setNotice("GPX generated and structurally checked. Review the output before export.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Waypoint generation failed.");
    } finally { setBusy(false); }
  }

  function exportFile() {
    if (!output || !confirmed) { setError("Review confirmation is required before export."); return; }
    clearFeedback();
    const url = URL.createObjectURL(output.blob);
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = output.filename;
    document.body.append(anchor); anchor.click(); anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 3000);
    setNotice(`Export requested for ${output.filename}. Check your browser's download manager to confirm the file was saved.`);
  }

  return (
    <div className="workflow-layout">
      <nav className="workflow-navigation" aria-label="GPX processing stages">
        <div className="navigation-heading">PROCESS / 05 STAGES</div>
        <ol className="steps">
          {stages.map((item, index) => (
            <li key={item.label}>
              <button className={`step ${stage === index ? "is-current" : ""}`} type="button" aria-current={stage === index ? "step" : undefined} onClick={() => navigate(index as Stage)} disabled={busy || index > maxReached || !accessible[index]}>
                <span className="step-number">{String(index + 1).padStart(2, "0")}</span>
                <span className="step-body"><strong>{item.label}</strong><small>{item.detail}</small></span>
                {index < stage && accessible[index] && <span aria-hidden="true" className="step-check">✓</span>}
              </button>
            </li>
          ))}
        </ol>
        <div className="navigation-note"><strong>Working principle</strong><p>Process route data deliberately. Generated coordinates and markers require navigation review.</p></div>
      </nav>

      <section className="workflow-panel" aria-labelledby="stage-title">
        <div className="stage-heading">
          <p className="eyebrow">STAGE {String(stage + 1).padStart(2, "0")} / 05</p>
          <h2 id="stage-title">{stages[stage].label}</h2>
          <p className="stage-detail">{[
            "Load a GPX track and validate its structure and elevation information.",
            "Define waypoint naming and interval behavior before generation.",
            "Generate the enriched GPX and perform initial structural checks.",
            "Check the generated marker list and confirm the original track point count.",
            "Save the reviewed GPX to your device."
          ][stage]}</p>
        </div>

        {error && <p className="feedback feedback-error" role="alert"><strong>Attention:</strong> {error}</p>}
        {notice && <p className="feedback feedback-status" role="status" aria-live="polite">{notice}</p>}

        {stage === 0 && <div className="stage-content">
          <label className="form-label" htmlFor="gpx-file">GPX track file <span className="field-meta">REQUIRED</span></label>
          <input id="gpx-file" type="file" accept=".gpx,application/gpx+xml" onChange={event => chooseFile(event.target.files?.[0] ?? null)} />
          <p className="field-help">Select an existing .gpx track. The server validates the structure, coordinates, and elevation data.</p>
          {file && <dl className="key-value"><div><dt>File</dt><dd>{file.name}</dd></div><div><dt>File size</dt><dd>{fileSize(file.size)}</dd></div><div><dt>Status</dt><dd>{analysis ? "Validated" : "Not yet validated"}</dd></div></dl>}
          <div className="button-row"><button className="primary-button" disabled={busy || !file} onClick={importFile} type="button">{busy ? "Validating…" : "Validate GPX"}<span aria-hidden="true">→</span></button></div>
        </div>}

        {stage === 1 && analysis && <div className="stage-content">
          <section className="analysis-summary" aria-labelledby="analysis-title"><h3 id="analysis-title">SOURCE TRACK / ANALYSIS</h3>
            <div className="metric-grid">
              <div className="metric"><span>Track points</span><strong>{analysis.total_points.toLocaleString()}</strong><small>points</small></div>
              <div className="metric"><span>Positive elevation</span><strong>{displayMeters(analysis.elevation_statistics.total_ascent)}</strong><small>ascent</small></div>
              <div className="metric"><span>Negative elevation</span><strong>{displayMeters(analysis.elevation_statistics.total_descent)}</strong><small>descent</small></div>
            </div>
            <div className="summary-footer">{analysis.tracks} track(s) / {analysis.segments} segment(s) / Min {displayMeters(analysis.elevation_statistics.min_elevation)} / Max {displayMeters(analysis.elevation_statistics.max_elevation)}</div>
          </section>
          <div className="form-grid">
            <div className="form-field"><label className="form-label" htmlFor="prefix">Waypoint prefix</label><input id="prefix" value={prefix} maxLength={6} minLength={3} pattern="[A-Z]{3,6}" onChange={e => {changeConfig(); setPrefix(e.target.value.toUpperCase().replace(/[^A-Z]/g, "").slice(0, 6));}} aria-describedby="prefix-help"/><p className="field-help" id="prefix-help">3–6 uppercase letters. Example: LCST.</p></div>
            <div className="form-field"><label className="form-label" htmlFor="interval">Waypoint interval <span className="unit">KM</span></label><input id="interval" type="number" min="0.000001" max="100" step="any" value={interval} onChange={e => {changeConfig(); setIntervalValue(e.target.value);}} aria-describedby="interval-help"/><p className="field-help" id="interval-help">Greater than 0 and at most 100 km.</p></div>
            <div className="form-field full-span"><label className="form-label" htmlFor="method">Distance calculation</label><select id="method" value={method} onChange={e => {changeConfig(); setMethod(e.target.value as DistanceMethod);}}><option value="auto">Automatic — recommended</option><option value="geodesic">Geodesic</option><option value="haversine">Haversine</option></select><p className="field-help">Automatic selection delegates algorithm selection to the existing GPX engine.</p></div>
          </div>
          <div className="button-row"><button className="secondary-button" onClick={() => navigate(0)}>← Back</button><button className="primary-button" onClick={submitConfiguration}>Continue <span aria-hidden="true">→</span></button></div>
        </div>}

        {stage === 2 && analysis && <div className="stage-content">
          <h3 className="section-title">GENERATION PARAMETERS</h3>
          <dl className="key-value"><div><dt>Input</dt><dd>{file?.name}</dd></div><div><dt>Prefix</dt><dd>{prefix}</dd></div><div><dt>Waypoint spacing</dt><dd>{intervalNumber.toLocaleString()} km</dd></div><div><dt>Method</dt><dd>{method}</dd></div><div><dt>Original track points</dt><dd>{analysis.total_points.toLocaleString()}</dd></div></dl>
          <p className="notice-band">No download will start at generation. The resulting file is inspected during the Review stage.</p>
          <div className="button-row"><button className="secondary-button" onClick={() => navigate(1)} disabled={busy}>← Back</button><button className="primary-button" onClick={createOutput} disabled={busy}>{busy ? "Generating…" : "Generate waypoints"}<span aria-hidden="true">→</span></button></div>
        </div>}

        {stage === 3 && output && <div className="stage-content">
          <div className="metric-grid"><div className="metric"><span>Generated waypoints</span><strong>{output.count.toLocaleString()}</strong><small>GPX marker elements</small></div><div className="metric"><span>Original track points</span><strong>{analysis?.total_points.toLocaleString()}</strong><small>source file</small></div><div className="metric"><span>Output track points</span><strong>{output.trackPoints.toLocaleString()}</strong><small>count verified</small></div></div>
          <h3 className="section-title">GENERATED MARKERS</h3>
          <ol className="marker-list">{output.waypointNames.slice(0, 15).map((name, index) => <li key={`${index}-${name}`}><span className="marker-index">{String(index+1).padStart(2,"0")}</span><span>{name}</span></li>)}</ol>
          {output.count > 15 && <p className="field-help">Showing first 15 of {output.count} waypoints. Full marker data is contained in the GPX export.</p>}
          <label className="confirm-control"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)}/><span>I have reviewed the output summary. The structural checks do not replace independent navigation verification.</span></label>
          <div className="button-row"><button className="secondary-button" onClick={() => navigate(2)}>← Back</button><button className="primary-button" disabled={!confirmed} onClick={() => {setMaxReached(4); setStage(4); clearFeedback();}}>Proceed to export <span aria-hidden="true">→</span></button></div>
        </div>}

        {stage === 4 && output && <div className="stage-content">
          <div className="export-panel"><span className="export-glyph" aria-hidden="true">GPX</span><div><strong>{output.filename}</strong><p>{fileSize(output.blob.size)} · {output.count} waypoints · GPX XML</p></div></div>
          <p className="field-help">Your browser will prompt you to save this file or place it in its configured download location.</p>
          <div className="button-row"><button className="secondary-button" onClick={() => navigate(3)}>← Review</button><button className="primary-button" onClick={exportFile}>Download GPX <span aria-hidden="true">↓</span></button></div>
        </div>}
        <div className="panel-bottom"><span>TRAILONE / GPX TOOLKIT</span><span>STEP {stage + 1} OF 5</span></div>
      </section>
    </div>
  );
}
