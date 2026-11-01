import React, { useEffect, useMemo, useState } from 'react';
import MissionSidebar from '../components/MissionSidebar';
import { inferenceService } from '../services/api';
import '../styles/ExoplanetAnalysis.css';

const stages = ['queued', 'downloading', 'processing', 'predicting'];

function LightCurve({ result }) {
  const points = useMemo(() => {
    const flux = result?.stitched?.flux || [];
    if (!flux.length) return '';
    const stride = Math.max(1, Math.floor(flux.length / 500));
    const sampled = flux.filter((_, index) => index % stride === 0);
    const min = Math.min(...sampled);
    const max = Math.max(...sampled);
    const range = max - min || 1;
    return sampled.map((value, index) => {
      const x = (index / Math.max(1, sampled.length - 1)) * 1000;
      const y = 260 - ((value - min) / range) * 220;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
  }, [result]);

  if (!points) return null;
  return (
    <div className="light-curve-card">
      <div className="plot-heading">
        <div>
          <span className="eyebrow">STITCHED DETRENDED SIGNAL</span>
          <h3>Light curve</h3>
        </div>
        <span className="plot-meta">KIC {result.kic}</span>
      </div>
      <svg className="light-curve" viewBox="0 0 1000 280" role="img" aria-label="Stitched detrended light curve">
        <line x1="0" y1="260" x2="1000" y2="260" />
        <polyline points={points} />
      </svg>
    </div>
  );
}

export default function ExoplanetAnalysis() {
  const [kic, setKic] = useState('');
  const [job, setJob] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!job || ['done', 'error'].includes(job.status)) return undefined;
    const timer = window.setInterval(async () => {
      try {
        const nextJob = await inferenceService.getJob(job.id);
        setJob(nextJob);
        if (nextJob.status === 'done') {
          setResult(nextJob.result);
          setSubmitting(false);
        }
        if (nextJob.status === 'error') {
          setError(nextJob.error || 'The analysis could not be completed.');
          setSubmitting(false);
        }
      } catch (requestError) {
        setError(requestError.response?.data?.detail || 'Unable to retrieve analysis status.');
        setSubmitting(false);
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [job]);

  const runAnalysis = async (event) => {
    event.preventDefault();
    setError('');
    setResult(null);
    setJob(null);
    if (!kic.trim()) {
      setError('Enter a KIC number to begin analysis.');
      return;
    }
    setSubmitting(true);
    try {
      const response = await inferenceService.submit(kic.trim());
      setJob({ id: response.job_id, status: response.status });
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Unable to start analysis.');
      setSubmitting(false);
    }
  };

  const stageIndex = stages.indexOf(job?.status);

  return (
    <div className="dashboard-container analysis-layout">
      <div className="celestial-bg" />
      <MissionSidebar />
      <main className="dashboard-main exoplanet-container">
      <div className="exoplanet-header">
        <span className="eyebrow">MODEL INFERENCE</span>
        <h1>Analyze a Kepler target</h1>
        <p>Enter a KIC identifier to retrieve light curves from MAST and score transit windows.</p>
      </div>

      {!result && (
        <form className="kic-form" onSubmit={runAnalysis}>
          <label htmlFor="kic-input">Kepler Input Catalog number</label>
          <div className="kic-input-row">
            <input
              id="kic-input"
              value={kic}
              onChange={(event) => setKic(event.target.value)}
              placeholder="For example, 9850966"
              inputMode="numeric"
              disabled={submitting}
            />
            <button type="submit" className="run-button" disabled={submitting}>
              {submitting ? 'Analysis running' : 'Analyze KIC'}
            </button>
          </div>
          <small>Cached MAST data is reused on repeated requests.</small>
        </form>
      )}

      {error && <div className="error-banner"><strong>Analysis unavailable</strong><p>{error}</p></div>}

      {job && !result && job.status !== 'error' && (
        <section className="job-panel">
          <span className="eyebrow">JOB {job.id.slice(0, 8).toUpperCase()}</span>
          <h2>{job.status === 'queued' ? 'Analysis queued' : 'Processing KIC data'}</h2>
          <div className="job-progress">
            {stages.map((stage, index) => (
              <div className={`job-stage ${index <= stageIndex ? 'active' : ''}`} key={stage}>
                <span>{String(index + 1).padStart(2, '0')}</span>
                {stage}
              </div>
            ))}
          </div>
          <p>MAST retrieval and model inference can take several minutes for a new target.</p>
        </section>
      )}

      {result && (
        <section className="analysis-results">
          <div className="result-heading">
            <div>
              <span className="eyebrow">INFERENCE COMPLETE</span>
              <h2>KIC {result.kic}</h2>
            </div>
            <button className="back-button" onClick={() => { setResult(null); setJob(null); setKic(''); }}>
              Analyze another KIC
            </button>
          </div>
          <div className="metrics-grid">
            <div className="metric-card"><span className="metric-label">Mean probability</span><strong className="metric-value">{(result.mean_probability * 100).toFixed(1)}%</strong><span className="metric-unit">all windows</span></div>
            <div className="metric-card"><span className="metric-label">Peak probability</span><strong className="metric-value">{(result.max_probability * 100).toFixed(1)}%</strong><span className="metric-unit">top window</span></div>
            <div className="metric-card"><span className="metric-label">Inference windows</span><strong className="metric-value">{result.n_windows}</strong><span className="metric-unit">1,024 points each</span></div>
            <div className="metric-card"><span className="metric-label">Model verdict</span><strong className="metric-value">{result.pred_max ? 'Candidate' : 'No candidate'}</strong><span className="metric-unit">threshold assessment</span></div>
          </div>
          <LightCurve result={result} />
          <div className="top-window">
            <span className="eyebrow">TOP-SCORING WINDOW</span>
            <p>{result.top_window.t_start.toFixed(3)} to {result.top_window.t_end.toFixed(3)} JD</p>
            <strong>{(result.top_window.probability * 100).toFixed(1)}% probability</strong>
          </div>
        </section>
      )}
      </main>
    </div>
  );
}
