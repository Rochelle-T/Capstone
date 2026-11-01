import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import MissionSidebar from '../components/MissionSidebar';
import { inferenceService } from '../services/api';
import '../styles/Dashboard.css';

const Dashboard = () => {
  const [modelStatus, setModelStatus] = useState(null);

  useEffect(() => {
    inferenceService.getModelStatus()
      .then(setModelStatus)
      .catch(() => setModelStatus({ available: false }));
  }, []);

  return (
    <div className="dashboard-container">
      <div className="celestial-bg"></div>
      <MissionSidebar />

      <main className="dashboard-main">
        <div className="dashboard-header">
          <div>
            <span className="eyebrow">MISSION OVERVIEW</span>
            <h2>Observatory dashboard</h2>
            <p>Run a model-backed transit analysis from any Kepler target.</p>
          </div>
          <div className="header-status"><span></span> SYSTEM ONLINE</div>
        </div>
        <div className="dashboard-content">
          <section className="dashboard-welcome">
            <div>
              <span className="eyebrow">KIC INFERENCE WORKSPACE</span>
              <h3>Analyze a Kepler target</h3>
              <p>
                Enter a KIC identifier and AstroSense will retrieve the matching
                light curves from MAST, preprocess them, and score transit windows.
              </p>
            </div>
            <Link to="/exoplanet" className="btn-primary dashboard-action">Start analysis</Link>
          </section>

          <section className="dashboard-stats" aria-label="Workspace status">
            <article className="dashboard-stat">
              <span>DATA SOURCE</span>
              <strong>MAST / Kepler</strong>
              <small>Long-cadence light curves</small>
            </article>
            <article className="dashboard-stat">
              <span>MODEL INPUT</span>
              <strong>1,024 points</strong>
              <small>Sliding inference windows</small>
            </article>
            <article className="dashboard-stat">
              <span>MODEL STATUS</span>
              <strong className={modelStatus?.available ? 'status-ready' : 'status-warning'}>
                {modelStatus ? (modelStatus.available ? 'Loaded' : 'Unavailable') : 'Checking'}
              </strong>
              <small>{modelStatus?.available ? 'CNN ready for inference' : 'Check server logs and /docs'}</small>
            </article>
          </section>

          <section className="dashboard-info-card">
            <span className="eyebrow">WORKFLOW</span>
            <h3>From target ID to evidence</h3>
            <div className="workflow-steps">
              <span>01 Identify KIC</span>
              <span>02 Retrieve data</span>
              <span>03 Score windows</span>
              <span>04 Review result</span>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
