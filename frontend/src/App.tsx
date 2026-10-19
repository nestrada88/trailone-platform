import GuidedGPXWorkflow from "./components/GuidedGPXWorkflow";

export default function App() {
  return (
    <div className="site-shell">
      <a className="skip-link" href="#workflow">Skip to GPX workflow</a>
      <header className="site-header">
        <div className="site-header-inner">
          <div className="brand-lockup">
            <img className="brand-logo" src="/trailone-primary.png" alt="TrailOne official source emblem" width="72" height="72" />
            <div className="brand-words">
              <span className="brand-name">TrailOne</span>
              <span className="brand-subtitle">GPX TOOLKIT / TRAIL PROCESSING</span>
            </div>
          </div>
          <span className="header-detail">ROUTE DATA · WAYPOINTS · GPX 1.1</span>
        </div>
      </header>
      <main id="workflow" className="app-container">
        <div className="heading-block">
          <div>
            <p className="eyebrow">TRAILONE / NAVIGATION DATA</p>
            <h1>Process a GPX track</h1>
            <p className="intro">Import, validate, configure, generate, review, and export waypoints without altering the source route geometry.</p>
          </div>
          <p className="document-identifier">TO / GPX / 01</p>
        </div>
        <GuidedGPXWorkflow />
        <footer className="site-footer">
          <span>TrailOne GPX Toolkit</span>
          <span>Navigation data requires independent field verification.</span>
        </footer>
      </main>
    </div>
  );
}
