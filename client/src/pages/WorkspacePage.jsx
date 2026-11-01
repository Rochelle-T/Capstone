import React from 'react';
import { Link } from 'react-router-dom';
import MissionSidebar from '../components/MissionSidebar';
import '../styles/Dashboard.css';

export default function WorkspacePage({ type }) {
  const isResults = type === 'results';

  return (
    <div className="dashboard-container">
      <div className="celestial-bg" />
      <MissionSidebar />
      <main className="dashboard-main">
        <div className="dashboard-header">
          <div>
            <span className="eyebrow">{isResults ? 'RESULTS ARCHIVE' : 'WORKSPACE SETTINGS'}</span>
            <h2>{isResults ? 'Analysis results' : 'Settings'}</h2>
            <p>
              {isResults
                ? 'Completed KIC analyses will be available here for review.'
                : 'Manage your AstroSense workspace preferences.'}
            </p>
          </div>
        </div>
        <div className="dashboard-content">
          <section className="dashboard-info-card workspace-placeholder">
            <span className="eyebrow">{isResults ? 'NO SAVED RESULTS' : 'CONFIGURATION'}</span>
            <h3>{isResults ? 'Run an analysis to create a result' : 'Workspace settings are coming next'}</h3>
            <p>
              {isResults
                ? 'Start a KIC analysis and review its live result on the Analysis screen.'
                : 'Your authenticated workspace is ready. Additional preferences will be added here.'}
            </p>
            {isResults && <Link to="/exoplanet" className="btn-primary dashboard-action">Start analysis</Link>}
          </section>
        </div>
      </main>
    </div>
  );
}
