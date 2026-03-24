/**
 * ExoplanetAnalysis.jsx
 * [ASTRONOMY PROCESSING]: Exoplanet detection and signal processing dashboard
 * 
 * Features:
 * - Search and select Kepler target systems
 * - Download and visualize target pixel files
 * - Display aperture masks
 * - Convert to light curves
 * - Show signal processing plots:
 *   1. Raw flux time-series
 *   2. Detrended signal
 *   3. BLS periodogram (transit detection)
 *   4. Phase-folded transit
 *   5. Summary statistics
 */

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles/ExoplanetAnalysis.css';

const API_BASE = 'http://127.0.0.1:8000';

export default function ExoplanetAnalysis() {
  // State management
  const [targets, setTargets] = useState([]);
  const [selectedTarget, setSelectedTarget] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [step, setStep] = useState(0); // 0: select, 1: analyzing, 2: results
  const [periodRange, setPeriodRange] = useState('hot_jupiter');

  // Fetch available targets on component mount
  useEffect(() => {
    fetchTargets();
  }, []);

  const fetchTargets = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/exoplanet/targets`);
      setTargets(response.data.targets);
      setError('');
    } catch (err) {
      setError('Failed to fetch targets: ' + err.message);
    }
  };

  const runAnalysis = async () => {
    if (!selectedTarget) {
      setError('Please select a target');
      return;
    }

    setLoading(true);
    setStep(1);
    setError('');

    try {
      const response = await axios.post(`${API_BASE}/api/exoplanet/analyze`, {
        target_name: selectedTarget,
        period_range: periodRange,
      }, {
        timeout: 120000, // 2 minute timeout for long analysis
      });

      if (response.data.status === 'success') {
        setAnalysis(response.data);
        setStep(2);
      } else {
        throw new Error(response.data.message || 'Analysis failed');
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message;
      
      // Provide helpful error message for common issues
      let displayError = errorMsg;
      if (errorMsg.includes('kill state') || errorMsg.includes('session')) {
        displayError = 'Archive connection lost. The Kepler archive may be temporarily unavailable. Please try again in a moment.';
      } else if (errorMsg.includes('timeout')) {
        displayError = 'Analysis took too long. Please try a different target with less data.';
      } else if (errorMsg.includes('No light curve')) {
        displayError = 'No data found for this target. Try a different quarter or target.';
      }
      
      setError(displayError);
      setStep(0);
    } finally {
      setLoading(false);
    }
  };

  // Step 1: Target Selection
  if (step === 0) {
    return (
      <div className="exoplanet-container">
        <div className="exoplanet-header">
          <h1>🔭 AstroSense: Exoplanet Detection Pipeline</h1>
          <p>Search Kepler targets, analyze light curves, and detect transiting exoplanets</p>
        </div>

        {error && (
          <div className="error-banner">
            <div className="error-content">
              <span className="error-icon">⚠️</span>
              <div className="error-message">
                <strong>Analysis Failed</strong>
                <p>{error}</p>
              </div>
            </div>
            <button 
              onClick={() => setError('')} 
              className="close-error"
            >
              ✕
            </button>
          </div>
        )}

        <div className="selection-panel">
          <div className="select-group">
            <label htmlFor="target-select">Select Target System</label>
            <select
              id="target-select"
              value={selectedTarget || ''}
              onChange={(e) => setSelectedTarget(e.target.value)}
              className="target-select"
            >
              <option value="">-- Choose a target --</option>
              {targets.map((target) => (
                <option key={target.id} value={target.display_name}>
                  {target.display_name}
                </option>
              ))}
            </select>
          </div>

          <div className="select-group">
            <label htmlFor="period-range">Search Period Range</label>
            <select
              id="period-range"
              value={periodRange}
              onChange={(e) => setPeriodRange(e.target.value)}
              className="target-select"
            >
              <option value="hot_jupiter">Hot Jupiters (0.5-10 days)</option>
              <option value="super_earth">Super-Earths (1-100 days)</option>
              <option value="earth_like">Earth-like (200-400 days)</option>
            </select>
          </div>

          <button
            onClick={runAnalysis}
            disabled={!selectedTarget || loading}
            className="run-button"
          >
            {loading ? 'Analyzing...' : '▶ Start Analysis Pipeline'}
          </button>
        </div>

        <div className="info-box">
          <h3>Pipeline Overview</h3>
          <ol>
            <li><strong>Download:</strong> Fetch Kepler light curve from archive</li>
            <li><strong>Detrend:</strong> Remove systematics using Savitzky-Golay filter</li>
            <li><strong>Detect:</strong> Search for transits using Box Least Squares (BLS)</li>
            <li><strong>Fold:</strong> Phase-fold light curve at orbital period</li>
            <li><strong>Analyze:</strong> Calculate transit statistics and Signal-to-Noise ratio</li>
          </ol>
          <p className="warning-note">
            ⚠️ <strong>Note:</strong> The Kepler archive can be slow during peak usage. If you get a connection error, please wait a moment and try again.
          </p>
        </div>
      </div>
    );
  }

  // Step 2: Loading
  if (step === 1) {
    return (
      <div className="exoplanet-container">
        <div className="loading-panel">
          <div className="spinner"></div>
          <h2>Analyzing {selectedTarget}...</h2>
          <p>Running signal processing pipeline on Kepler archive data</p>
          <div className="progress-steps">
            <div className="step active">Download</div>
            <div className="step active">Detrend</div>
            <div className="step active">BLS Transit Search</div>
            <div className="step active">Phase-Fold</div>
            <div className="step">Generate Summary</div>
          </div>
          <p className="loading-note">
            ⏱️ This may take 30-60 seconds. Please wait...
          </p>
        </div>
      </div>
    );
  }

  // Step 3: Results
  if (step === 2 && analysis) {
    const summary = analysis.summary;
    const plots = analysis.plots;

    return (
      <div className="exoplanet-container">
        <div className="exoplanet-header">
          <h1>✅ Analysis Complete: {summary.target_name}</h1>
          <button onClick={() => setStep(0)} className="back-button">
            ← Analyze Another Target
          </button>
        </div>

        {/* Summary Statistics */}
        <div className="summary-section">
          <h2>Transit Detection Results</h2>
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-label">Orbital Period</div>
              <div className="metric-value">{summary.orbital_period_days.toFixed(4)}</div>
              <div className="metric-unit">days</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Transit Depth</div>
              <div className="metric-value">{summary.transit_depth_ppm.toFixed(1)}</div>
              <div className="metric-unit">ppm</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Transit Duration</div>
              <div className="metric-value">{summary.transit_duration_hours.toFixed(2)}</div>
              <div className="metric-unit">hours</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Signal-to-Noise</div>
              <div className="metric-value">{summary.snr.toFixed(1)}</div>
              <div className="metric-unit">σ</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Data Points</div>
              <div className="metric-value">{summary.data_points}</div>
              <div className="metric-unit">measurements</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Time Span</div>
              <div className="metric-value">{summary.time_span_days.toFixed(1)}</div>
              <div className="metric-unit">days</div>
            </div>
          </div>
        </div>

        {/* Signal Processing Plots */}
        <div className="plots-section">
          <h2>Signal Processing Pipeline</h2>

          <div className="plots-grid">
            {/* Raw Light Curve */}
            {plots.raw_lc && !plots.raw_lc.startsWith('error') && (
              <div className="plot-card">
                <h3>1. Raw Time-Series Flux</h3>
                <img src={`data:image/png;base64,${plots.raw_lc}`} alt="Raw LC" />
                <p className="plot-desc">Original Kepler light curve with systematics</p>
              </div>
            )}

            {/* Detrended Light Curve */}
            {plots.detrended_lc && !plots.detrended_lc.startsWith('error') && (
              <div className="plot-card">
                <h3>2. Detrended Signal</h3>
                <img src={`data:image/png;base64,${plots.detrended_lc}`} alt="Detrended LC" />
                <p className="plot-desc">After Savitzky-Golay filtering (window=401)</p>
              </div>
            )}

            {/* BLS Periodogram */}
            {plots.bls_periodogram && !plots.bls_periodogram.startsWith('error') && (
              <div className="plot-card">
                <h3>3. BLS Periodogram</h3>
                <img src={`data:image/png;base64,${plots.bls_periodogram}`} alt="BLS" />
                <p className="plot-desc">Box Least Squares transit detection</p>
              </div>
            )}

            {/* Phase-Folded Transit */}
            {plots.folded_lc && !plots.folded_lc.startsWith('error') && (
              <div className="plot-card">
                <h3>4. Phase-Folded Transit</h3>
                <img src={`data:image/png;base64,${plots.folded_lc}`} alt="Folded LC" />
                <p className="plot-desc">U-shaped transit signature at orbital period</p>
              </div>
            )}
          </div>
        </div>

        {error && <div className="error-banner">{error}</div>}
      </div>
    );
  }

  return null;
}
