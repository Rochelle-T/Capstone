import React, { useEffect, useMemo, useState } from 'react';
import MissionSidebar from '../components/MissionSidebar';
import { inferenceService } from '../services/api';
import '../styles/ExoplanetAnalysis.css';

const stages = ['queued', 'downloading', 'processing', 'predicting'];
const formatNumber = (value, digits = 3) => (
  Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : 'Unavailable'
);
const formatProbability = (value) => (
  Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(1)}%` : 'Unavailable'
);
const timeLabel = (result) => result?.diagnostics?.time_system?.label || 'Pipeline time';

function getStageSeries(result, stage) {
  if (stage === 'scaled_flux') return result?.diagnostics?.scaled_series;
  return result?.diagnostics?.stage_series?.[stage];
}

function buildRegions(result) {
  const probabilities = result?.window_probabilities || [];
  const metadata = result?.window_meta || [];
  const threshold = result?.threshold ?? 0.5;
  const regions = [];
  probabilities.forEach((probability, index) => {
    const current = metadata[index];
    if (probability < threshold || !current) return;
    const previous = regions[regions.length - 1];
    const joinsPrevious = previous
      && previous.segment === current.segment
      && current.t_start <= previous.end_time;
    if (joinsPrevious) {
      previous.window_indices.push(index);
      previous.end_time = Math.max(previous.end_time, current.t_end);
      previous.probabilities.push(probability);
      return;
    }
    regions.push({
      id: regions.length + 1,
      segment: current.segment,
      start_time: current.t_start,
      end_time: current.t_end,
      window_indices: [index],
      probabilities: [probability],
    });
  });
  return regions.map((region) => ({
    ...region,
    count: region.probabilities.length,
    mean_probability: region.probabilities.reduce((sum, value) => sum + value, 0)
      / region.probabilities.length,
    max_probability: Math.max(...region.probabilities),
    min_probability: Math.min(...region.probabilities),
    above_percentage: 100,
  }));
}

function buildSegmentStats(result) {
  const segments = result?.diagnostics?.segments || [];
  const probabilities = result?.window_probabilities || [];
  const metadata = result?.window_meta || [];
  const threshold = result?.threshold ?? 0.5;
  return segments.map((segment) => {
    const indices = metadata
      .map((item, index) => (item.segment === segment.segment ? index : -1))
      .filter((index) => index >= 0);
    const values = indices.map((index) => probabilities[index]).filter(Number.isFinite);
    const above = values.filter((value) => value >= threshold).length;
    return {
      ...segment,
      window_indices: indices,
      n_windows: values.length,
      mean_probability: values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null,
      max_probability: values.length ? Math.max(...values) : null,
      min_probability: values.length ? Math.min(...values) : null,
      above_threshold: above,
      above_percentage: values.length ? (above / values.length) * 100 : null,
    };
  });
}

function Metric({ label, value, unit }) {
  return (
    <div className="metric-card">
      <span className="metric-label">{label}</span>
      <strong className="metric-value">{value}</strong>
      {unit && <span className="metric-unit">{unit}</span>}
    </div>
  );
}

function Section({ title, eyebrow, children, open = false }) {
  return (
    <details className="analysis-section" open={open}>
      <summary>
        <span>
          <span className="eyebrow">{eyebrow}</span>
          <strong>{title}</strong>
        </span>
        <span className="details-toggle">View details</span>
      </summary>
      <div className="analysis-section-content">{children}</div>
    </details>
  );
}

function ModelTwoAttentionChart({ model }) {
  const values = model?.attention_weights || [];
  if (!values.length) return <p className="empty-state">Attention weights are unavailable.</p>;
  const width = 1000;
  const height = 260;
  const max = Math.max(...values, 0.0001);
  const barWidth = Math.max(2, (width - 70) / values.length - 2);
  return (
    <div className="chart-shell">
      <svg className="analysis-plot" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Model 2 attention by window">
        <line className="chart-axis" x1="45" y1="220" x2="980" y2="220" />
        {values.map((value, index) => {
          const barHeight = (value / max) * 175;
          return <g key={`attention-${index}`}><title>{`Window ${index + 1}: attention ${value.toFixed(5)}`}</title><rect className="attention-bar" x={50 + index * ((width - 70) / values.length)} y={215 - barHeight} width={barWidth} height={barHeight} /></g>;
        })}
        <text className="chart-label" x="500" y="250" textAnchor="middle">Chronological window index</text>
        <text className="chart-label" transform="translate(14 130) rotate(-90)" textAnchor="middle">Attention weight</text>
      </svg>
    </div>
  );
}

function ModelTwoPreprocessingChart({ model }) {
  const files = model?.preprocessing || [];
  const points = files.flatMap((file) => file.time.map((time, index) => ({ time, value: file.processed[index] })));
  if (!points.length) return <p className="empty-state">Model 2 preprocessing data is unavailable.</p>;
  const width = 1000;
  const height = 280;
  const minTime = points[0].time;
  const maxTime = points[points.length - 1].time || minTime + 1;
  const values = points.map((point) => point.value).filter(Number.isFinite);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const x = (value) => 45 + ((value - minTime) / (maxTime - minTime || 1)) * 930;
  const y = (value) => 20 + ((maxValue - value) / (maxValue - minValue || 1)) * 200;
  const path = points.map((point, index) => `${index ? 'L' : 'M'}${x(point.time).toFixed(2)},${y(point.value).toFixed(2)}`).join(' ');
  return <div className="chart-shell"><svg className="analysis-plot" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Model 2 processed light curve"><line className="chart-axis" x1="45" y1="225" x2="975" y2="225" /><path className="light-curve-path" d={path} /><text className="chart-label" x="500" y="265" textAnchor="middle">Time</text><text className="chart-label" transform="translate(14 130) rotate(-90)" textAnchor="middle">Savgol processed flux</text></svg></div>;
}

function ModelTwoAttentionSegments({ model }) {
  const values = model?.attention_weights || [];
  const specs = model?.window_specs || [];
  const bySegment = {};
  values.forEach((value, index) => {
    const file = specs[index]?.file || 'Unknown';
    bySegment[file] = (bySegment[file] || 0) + value;
  });
  const entries = Object.entries(bySegment);
  if (!entries.length) return <p className="empty-state">Segment attention is unavailable.</p>;
  const max = Math.max(...entries.map(([, value]) => value), 0.0001);
  return <div className="model2-segment-bars">{entries.map(([file, value]) => <div className="model2-segment-row" key={file}><span className="model2-segment-name" title={file}>{file}</span><span className="segment-bar-track"><i style={{ width: `${(value / max) * 100}%` }} /></span><strong>{formatNumber(value, 4)}</strong></div>)}</div>;
}

function ModelTwoAttentionDistribution({ model }) {
  const values = model?.attention_weights || [];
  if (!values.length) return <p className="empty-state">Attention distribution is unavailable.</p>;
  const bins = Array.from({ length: 10 }, () => 0);
  const max = Math.max(...values, 0.0001);
  values.forEach((value) => { bins[Math.min(9, Math.floor((value / max) * 10))] += 1; });
  const peak = Math.max(...bins, 1);
  return <div className="distribution-grid">{bins.map((count, index) => <div className="distribution-bar" key={`attention-bin-${index}`} style={{ height: `${Math.max(4, (count / peak) * 100)}%` }} title={`${count} windows`}><span>{count}</span></div>)}</div>;
}

function ModelTwoDetails({ result }) {
  const model = result?.models?.attention_mil;
  if (!model) return <p className="empty-state">Model 2 results are unavailable.</p>;
  return (
    <div className="model-tab-panel">
      <div className="prediction-callout">
        <div><span className="eyebrow">PREDICTION SUMMARY</span><h3>{model.is_candidate ? 'Candidate detected' : 'No candidate detected'}</h3><p>AttentionMIL uses its validation threshold against the KIC-level probability.</p></div>
        <strong className="verdict-badge">{model.is_candidate ? 'CANDIDATE' : 'NO CANDIDATE'}</strong>
      </div>
      <div className="metrics-grid">
        <Metric label="KIC probability" value={formatProbability(model.probability)} unit="target-level score" />
        <Metric label="Decision threshold" value={formatProbability(model.threshold)} unit="validation threshold" />
        <Metric label="Windows evaluated" value={model.n_windows} unit={`${model.n_windows_before_cap ?? 'Unavailable'} before cap`} />
        <Metric label="Files used" value={model.n_files_used} unit={`${result.n_fits_files ?? 'Unavailable'} retrieved`} />
      </div>
      <Section title="AttentionMIL model details" eyebrow="SECTION A" open>
        <div className="detail-grid">
          <div><span>Architecture</span><strong>{model.name}</strong></div>
          <div><span>Model version</span><strong>{model.version}</strong></div>
          <div><span>Framework</span><strong>{model.loading}</strong></div>
          <div><span>Preprocessing</span><strong>Savitzky-Golay · gap factor 2.5</strong></div>
          <div><span>Input</span><strong className="mono">Bag of 1024-point windows</strong></div>
          <div><span>Attention windows</span><strong>{model.n_windows}</strong></div>
        </div>
      </Section>
      <Section title="Top attention windows" eyebrow="SECTION B" open>
        {model.top_windows?.length ? (
          <div className="window-table-wrap"><table className="segment-table"><thead><tr><th>Rank</th><th>Source FITS</th><th>Start</th><th>Time range</th><th>Attention</th></tr></thead><tbody>
            {model.top_windows.map((window, index) => <tr key={`${window.file}-${window.start}`}><td>#{index + 1}</td><td>{window.file}</td><td>{window.start}</td><td>{formatNumber(window.time_start, 4)} – {formatNumber(window.time_end, 4)}</td><td>{formatNumber(window.attention, 4)}</td></tr>)}
          </tbody></table></div>
        ) : <p className="empty-state">Attention windows are unavailable.</p>}
      </Section>
      <Section title="Attention timeline" eyebrow="SECTION C" open>
        <ModelTwoAttentionChart model={model} />
        <p className="technical-note">Higher bars indicate windows that contributed more strongly to the KIC-level decision. They are not independent probabilities.</p>
      </Section>
      <Section title="Model 2 preprocessing" eyebrow="SECTION D">
        <ModelTwoPreprocessingChart model={model} />
        <p className="technical-note">This signal is the Savitzky-Golay processed flux supplied to the AttentionMIL window pipeline.</p>
      </Section>
      <Section title="Attention by FITS segment" eyebrow="SECTION E">
        <ModelTwoAttentionSegments model={model} />
      </Section>
      <Section title="Attention distribution" eyebrow="SECTION F">
        <ModelTwoAttentionDistribution model={model} />
      </Section>
      <Section title="Data processing" eyebrow="SECTION G">
        <div className="detail-grid">
          <div><span>FITS files retrieved</span><strong>{result.n_fits_files}</strong></div>
          <div><span>Files used by Model 2</span><strong>{model.n_files_used}</strong></div>
          <div><span>Windows before cap</span><strong>{model.n_windows_before_cap}</strong></div>
          <div><span>Windows after cap</span><strong>{model.n_windows}</strong></div>
          <div><span>Skipped files</span><strong>{result.skipped_files?.length ?? 0}</strong></div>
          <div><span>Model execution</span><strong>PyTorch inference</strong></div>
        </div>
      </Section>
    </div>
  );
}

function LightCurveChart({ result, stage, selectedWindow, selectedRegion, selectedSegment, zoom = 1 }) {
  const series = getStageSeries(result, stage);
  const segments = result?.diagnostics?.segments || [];
  const points = series?.time?.map((time, index) => ({ time, value: series.value[index] })) || [];
  if (!points.length) return <p className="empty-state">Processed light-curve data is unavailable.</p>;

  const width = 1000;
  const height = 330;
  const padding = { left: 58, right: 20, top: 20, bottom: 42 };
  const minTime = points[0].time;
  const maxTime = points[points.length - 1].time;
  const values = points.map((point) => point.value).filter(Number.isFinite);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const timeRange = maxTime - minTime || 1;
  const valueRange = maxValue - minValue || 1;
  const x = (time) => padding.left + ((time - minTime) / timeRange)
    * (width - padding.left - padding.right);
  const y = (value) => padding.top + ((maxValue - value) / valueRange)
    * (height - padding.top - padding.bottom);
  const path = points.map((point, index) => (
    `${index ? 'L' : 'M'}${x(point.time).toFixed(2)},${y(point.value).toFixed(2)}`
  )).join(' ');
  const selected = selectedWindow && {
    x: x(selectedWindow.t_start),
    width: Math.max(2, x(selectedWindow.t_end) - x(selectedWindow.t_start)),
  };
  const region = selectedRegion && {
    x: x(selectedRegion.start_time),
    width: Math.max(2, x(selectedRegion.end_time) - x(selectedRegion.start_time)),
  };
  const segment = selectedSegment && {
    x: x(selectedSegment.time_start),
    width: Math.max(2, x(selectedSegment.time_end) - x(selectedSegment.time_start)),
  };

  return (
    <div className="chart-shell" style={{ '--chart-scale': zoom }}>
      <svg className="analysis-plot" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Processed stitched light curve">
        <title>{`${stage} light curve with ${segments.length} FITS segments`}</title>
        <line className="chart-axis" x1={padding.left} y1={height - padding.bottom} x2={width - padding.right} y2={height - padding.bottom} />
        <line className="chart-axis" x1={padding.left} y1={padding.top} x2={padding.left} y2={height - padding.bottom} />
        {segments.map((segment) => (
          <g key={`segment-${segment.segment}`}>
            <line
              className="segment-boundary"
              x1={x(segment.time_start)}
              y1={padding.top}
              x2={x(segment.time_start)}
              y2={height - padding.bottom}
            />
            <text className="segment-label" x={x(segment.time_start) + 4} y={padding.top + 13}>S{segment.segment + 1}</text>
          </g>
        ))}
        {segment && <rect className="selected-segment" x={segment.x} y={padding.top} width={segment.width} height={height - padding.top - padding.bottom} />}
        {region && <rect className="selected-region" x={region.x} y={padding.top} width={region.width} height={height - padding.top - padding.bottom} />}
        {selected && (
          <rect className="selected-window" x={selected.x} y={padding.top} width={selected.width} height={height - padding.top - padding.bottom} />
        )}
        <path className="light-curve-path" d={path} />
        <text className="chart-label" x={width / 2} y={height - 8} textAnchor="middle">{timeLabel(result)}</text>
        <text className="chart-label" transform={`translate(14 ${height / 2}) rotate(-90)`} textAnchor="middle">Processed flux</text>
      </svg>
      <div className="chart-legend">
        <span><i className="legend-line signal" />Stitched detrended signal</span>
        <span><i className="legend-line boundary" />FITS segment boundary</span>
        {selectedSegment && <span><i className="legend-line segment-selected" />Selected segment</span>}
        {selectedRegion && <span><i className="legend-line region-selected" />High-score region</span>}
        {selectedWindow && <span><i className="legend-line selected" />Selected window</span>}
      </div>
    </div>
  );
}

function ProbabilityChart({ result, selectedIndex, onSelectWindow }) {
  const probabilities = result?.window_probabilities || [];
  if (!probabilities.length) return <p className="empty-state">Window probabilities are unavailable.</p>;
  const width = 1000;
  const height = 280;
  const padding = { left: 52, right: 20, top: 20, bottom: 42 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const threshold = result.threshold ?? 0.5;
  const barWidth = Math.max(2, chartWidth / probabilities.length - 2);
  const y = (value) => padding.top + (1 - value) * chartHeight;

  return (
    <div className="chart-shell">
      <svg className="analysis-plot" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="CNN window probabilities">
        <line className="chart-axis" x1={padding.left} y1={height - padding.bottom} x2={width - padding.right} y2={height - padding.bottom} />
        <line className="threshold-line" x1={padding.left} y1={y(threshold)} x2={width - padding.right} y2={y(threshold)} />
        {probabilities.map((probability, index) => {
          const barX = padding.left + index * (chartWidth / probabilities.length);
          const barY = y(probability);
          return (
            <g key={`probability-${index}`} onClick={() => onSelectWindow(index)} onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') onSelectWindow(index);
            }} role="button" tabIndex={0} className={index === selectedIndex ? 'probability-bar selected' : 'probability-bar'}>
              <title>{`Window ${index + 1}: ${formatProbability(probability)}`}</title>
              <rect x={barX} y={barY} width={barWidth} height={Math.max(1, height - padding.bottom - barY)} />
            </g>
          );
        })}
        <text className="chart-label" x={width / 2} y={height - 8} textAnchor="middle">Window index</text>
        <text className="chart-label" transform={`translate(14 ${height / 2}) rotate(-90)`} textAnchor="middle">CNN probability</text>
        <text className="threshold-label" x={width - padding.right - 4} y={y(threshold) - 6} textAnchor="end">
          threshold {threshold.toFixed(2)}
        </text>
      </svg>
      <p className="chart-help">Select a bar to highlight its time range in the stitched light curve.</p>
    </div>
  );
}

function WindowTimeline({ result, selectedIndex, onSelectWindow }) {
  const probabilities = result?.window_probabilities || [];
  const metadata = result?.window_meta || [];
  const threshold = result?.threshold ?? 0.5;
  if (!probabilities.length) return <p className="empty-state">Window activity is unavailable.</p>;
  return (
    <div className="timeline-shell">
      <div className="window-timeline" role="list" aria-label="CNN window activity timeline">
        {probabilities.map((probability, index) => {
          const meta = metadata[index] || {};
          const selected = index === selectedIndex;
          return (
            <button
              className={`timeline-window ${probability >= threshold ? 'above-threshold' : 'below-threshold'} ${selected ? 'selected' : ''}`}
              key={`timeline-${index}`}
              type="button"
              onClick={() => onSelectWindow(index)}
              title={`Window ${index + 1}: ${formatProbability(probability)}; ${meta.t_start ?? 'Unavailable'}–${meta.t_end ?? 'Unavailable'}; segment ${Number(meta.segment) + 1}`}
              style={{ opacity: 0.35 + (Math.max(0, Math.min(1, probability)) * 0.65) }}
            >
              <span>{index + 1}</span>
            </button>
          );
        })}
      </div>
      <div className="timeline-legend">
        <span><i className="timeline-swatch low" />Below threshold</span>
        <span><i className="timeline-swatch high" />At or above threshold</span>
        <span>Threshold {threshold.toFixed(2)} · hover for details</span>
      </div>
    </div>
  );
}

function SegmentComparison({ segments, selectedSegment, onSelectSegment }) {
  if (!segments.length) return <p className="empty-state">Segment statistics are unavailable.</p>;
  const maxProbability = Math.max(...segments.map((segment) => segment.mean_probability || 0), 1);
  return (
    <div className="segment-comparison">
      <div className="segment-bars" aria-label="Mean probability by segment">
        {segments.map((segment) => (
          <button
            className={`segment-bar-row ${selectedSegment?.segment === segment.segment ? 'selected' : ''}`}
            key={`segment-bar-${segment.segment}`}
            type="button"
            onClick={() => onSelectSegment(segment.segment)}
          >
            <span>S{segment.segment + 1}</span>
            <span className="segment-bar-track"><i style={{ width: `${((segment.mean_probability || 0) / maxProbability) * 100}%` }} /></span>
            <strong>{formatProbability(segment.mean_probability)}</strong>
          </button>
        ))}
      </div>
      <div className="segment-heatmap">
        {segments.map((segment) => (
          <div className="segment-heatmap-cell" key={`segment-heat-${segment.segment}`} title={`Segment ${segment.segment + 1}: ${segment.n_windows} windows`}>
            <span>S{segment.segment + 1}</span>
            <i style={{ opacity: 0.2 + ((segment.mean_probability || 0) * 0.8) }} />
          </div>
        ))}
      </div>
    </div>
  );
}

function SelectedWindowPanel({ result, selectedIndex, onSelectWindow }) {
  if (selectedIndex === null || !result?.window_meta?.[selectedIndex]) {
    return <p className="empty-state">Select a window from the timeline, chart, table, or ranking to inspect it.</p>;
  }
  const meta = result.window_meta[selectedIndex];
  const probability = result.window_probabilities[selectedIndex];
  const threshold = result.threshold ?? 0.5;
  return (
    <div className="selected-window-panel">
      <div className="selected-window-header">
        <div><span className="eyebrow">SELECTED WINDOW</span><h3>Window #{selectedIndex + 1}</h3></div>
        <strong className={probability >= threshold ? 'score-high' : 'score-low'}>{formatProbability(probability)}</strong>
      </div>
      <div className="detail-grid">
        <div><span>Threshold result</span><strong>{probability >= threshold ? 'At or above threshold' : 'Below threshold'}</strong></div>
        <div><span>Segment</span><strong>{Number.isFinite(meta.segment) ? meta.segment + 1 : 'Unavailable'}</strong></div>
        <div><span>Time range</span><strong>{formatNumber(meta.t_start, 4)} – {formatNumber(meta.t_end, 4)}</strong></div>
        <div><span>Observations</span><strong>{meta.segment_point_end != null && meta.segment_point_start != null ? meta.segment_point_end - meta.segment_point_start + 1 : 'Unavailable'}</strong></div>
        <div><span>Full-series points</span><strong>{meta.point_start != null ? `${meta.point_start} – ${meta.point_end}` : 'Unavailable'}</strong></div>
      </div>
      <div className="window-navigation">
        <button type="button" className="back-button" disabled={selectedIndex <= 0} onClick={() => onSelectWindow(selectedIndex - 1)}>Previous window</button>
        <button type="button" className="back-button" disabled={selectedIndex >= result.window_probabilities.length - 1} onClick={() => onSelectWindow(selectedIndex + 1)}>Next window</button>
      </div>
    </div>
  );
}

function Distribution({ values, title, color = 'var(--primary-cyan)', domain = [0, 1], valueLabel = 'Probability range' }) {
  if (!values.length) return <p className="empty-state">Distribution is unavailable.</p>;
  const [domainMin, domainMax] = domain;
  const range = domainMax - domainMin || 1;
  const bins = Array.from({ length: 10 }, (_, index) => ({
    label: formatNumber(domainMin + (index * range) / 10, 2),
    count: 0,
  }));
  values.forEach((value) => {
    const index = Math.min(9, Math.max(0, Math.floor(((value - domainMin) / range) * 10)));
    bins[index].count += 1;
  });
  const maxCount = Math.max(...bins.map((bin) => bin.count), 1);
  return (
    <div className="distribution">
      <h4>{title}</h4>
      <div className="distribution-bars">
        {bins.map((bin) => (
          <div className="distribution-bin" key={bin.label}>
            <span className="distribution-count">{bin.count || ''}</span>
            <div className="distribution-bar-track">
              <div className="distribution-bar" style={{ height: `${(bin.count / maxCount) * 100}%`, background: color }} />
            </div>
            <span>{bin.label}</span>
          </div>
        ))}
      </div>
      <small>{valueLabel}</small>
    </div>
  );
}

function RankedWindows({ result, onSelectWindow }) {
  const probabilities = result?.window_probabilities || [];
  if (!probabilities.length) return <p className="empty-state">Window ranking is unavailable.</p>;
  const ranked = probabilities.map((probability, index) => ({ probability, index }));
  const highest = [...ranked].sort((a, b) => b.probability - a.probability).slice(0, 3);
  const lowest = [...ranked].sort((a, b) => a.probability - b.probability).slice(0, 3);
  const row = (item) => {
    const meta = result.window_meta?.[item.index] || {};
    return <button type="button" className="ranked-window" key={`rank-${item.index}`} onClick={() => onSelectWindow(item.index)}><span>Window #{item.index + 1}</span><strong>{formatProbability(item.probability)}</strong><small>{formatNumber(meta.t_start, 3)} – {formatNumber(meta.t_end, 3)}</small></button>;
  };
  return (
    <div className="ranking-grid">
      <div><h4>Highest-scoring windows</h4>{highest.map(row)}</div>
      <div><h4>Lowest-scoring windows</h4>{lowest.map(row)}</div>
    </div>
  );
}

function Interpretation({ result }) {
  const probabilities = result.window_probabilities || [];
  const threshold = result.threshold ?? 0.5;
  const above = result.windows_above_threshold ?? probabilities.filter((value) => value >= threshold).length;
  const concentrated = probabilities.length > 1 && (result.max_probability - result.mean_probability) > 0.25;
  const consistency = concentrated
    ? 'Scores are concentrated in a smaller number of windows rather than being broadly consistent across the target.'
    : 'Scores are relatively consistent across the evaluated windows.';
  return (
    <div className="interpretation">
      <p>{consistency} {above} of {probabilities.length} windows meet or exceed the {threshold.toFixed(2)} decision threshold.</p>
      <p>These are CNN candidate-screening outputs. A high-scoring window is not a measurement of the probability that the entire target hosts an exoplanet, and this result is not a planet confirmation.</p>
    </div>
  );
}

function reportLightCurveSvg(result) {
  const series = result.diagnostics?.stitched_series;
  if (!series?.time?.length) return '<p>Stitched light-curve visualization unavailable.</p>';
  const width = 900;
  const height = 260;
  const times = series.time;
  const values = series.value;
  const minTime = times[0];
  const maxTime = times[times.length - 1] || minTime + 1;
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const x = (value) => 45 + ((value - minTime) / (maxTime - minTime || 1)) * 840;
  const y = (value) => 20 + ((maxValue - value) / (maxValue - minValue || 1)) * 205;
  const path = times.map((value, index) => `${index ? 'L' : 'M'}${x(value).toFixed(2)},${y(values[index]).toFixed(2)}`).join(' ');
  const label = result.diagnostics?.time_system?.label || 'Pipeline time';
  return `<svg viewBox="0 0 ${width} ${height}" style="width:100%;border:1px solid #ccd6e0"><path d="${path}" fill="none" stroke="#1769aa" stroke-width="1.5"/><text x="450" y="252" text-anchor="middle" font-size="11">${label}</text><text x="12" y="130" text-anchor="middle" font-size="11" transform="rotate(-90 12 130)">Processed flux</text></svg>`;
}

function reportProbabilitySvg(result) {
  const probabilities = result.window_probabilities || [];
  if (!probabilities.length) return '<p>Window probability visualization unavailable.</p>';
  const width = 900;
  const height = 240;
  const threshold = result.threshold ?? 0.5;
  const barWidth = 820 / probabilities.length;
  const bars = probabilities.map((probability, index) => {
    const heightValue = Math.max(1, probability * 180);
    return `<rect x="${45 + index * barWidth}" y="${200 - heightValue}" width="${Math.max(1, barWidth - 2)}" height="${heightValue}" fill="#1769aa"><title>Window ${index + 1}: ${probability.toFixed(6)}</title></rect>`;
  }).join('');
  const thresholdY = 200 - threshold * 180;
  return `<svg viewBox="0 0 ${width} ${height}" style="width:100%;border:1px solid #ccd6e0">${bars}<line x1="45" y1="${thresholdY}" x2="865" y2="${thresholdY}" stroke="#b7791f" stroke-dasharray="6 4"/><text x="450" y="228" text-anchor="middle" font-size="11">Window index</text><text x="55" y="${thresholdY - 5}" font-size="11">Threshold ${threshold.toFixed(2)}</text></svg>`;
}

function PrintableReport({ result }) {
  const diagnostics = result.diagnostics || {};
  const windows = result.window_probabilities || [];
  const regions = buildRegions(result);
  const rows = windows.map((probability, index) => {
    const meta = result.window_meta?.[index] || {};
    return `<tr><td>${index + 1}</td><td>${probability.toFixed(6)}</td><td>${meta.t_start ?? 'Unavailable'}</td><td>${meta.t_end ?? 'Unavailable'}</td><td>${meta.segment ?? 'Unavailable'}</td></tr>`;
  }).join('');
  const interpretation = windows.length
    ? `${result.windows_above_threshold} of ${windows.length} windows meet or exceed the ${result.threshold.toFixed(2)} threshold.`
    : 'Window interpretation unavailable.';
  return `<!doctype html><html><head><title>AstroSense report - KIC ${result.kic}</title>
    <style>body{font-family:Arial,sans-serif;color:#172033;margin:36px}h1{color:#1769aa}h2{border-bottom:1px solid #ccd6e0;padding-bottom:6px;margin-top:28px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.metric{border:1px solid #ccd6e0;padding:12px}.label{display:block;color:#5d6b7b;font-size:12px;text-transform:uppercase}.value{font-size:20px;font-weight:bold}table{border-collapse:collapse;width:100%;font-size:11px}th,td{border:1px solid #ccd6e0;padding:5px;text-align:left}th{background:#edf4fa}.note{background:#f3f6f9;padding:12px}@media print{body{margin:18px}}</style></head>
    <body><h1>AstroSense CNN analysis report</h1><p>KIC ${result.kic} &middot; ${result.analysis_timestamp || 'Timestamp unavailable'}</p>
    <h2>Prediction summary</h2><div class="grid"><div class="metric"><span class="label">Verdict</span><span class="value">${result.pred_max ? 'Candidate' : 'No candidate'}</span></div><div class="metric"><span class="label">Mean probability</span><span class="value">${formatProbability(result.mean_probability)}</span></div><div class="metric"><span class="label">Maximum probability</span><span class="value">${formatProbability(result.max_probability)}</span></div><div class="metric"><span class="label">Minimum probability</span><span class="value">${formatProbability(result.min_probability)}</span></div><div class="metric"><span class="label">Above threshold</span><span class="value">${result.windows_above_threshold} / ${windows.length}</span></div><div class="metric"><span class="label">Duration</span><span class="value">${formatNumber(result.timing?.total_seconds, 2)} s</span></div></div>
    <h2>Data quality</h2><p>Retrieved ${result.n_fits_files} FITS files and processed ${result.n_observations_processed} observations. ${diagnostics.cleaning?.initial_observations || 'Unavailable'} observations entered extraction and ${diagnostics.cleaning?.removed_observations || 0} were removed. Failed or skipped files: ${result.skipped_files?.length || 0}.</p>
    <h2>Preprocessing</h2><p>Stages: MAST retrieval, FITS extraction, invalid-observation removal, median normalization, Savitzky-Golay detrending, file-level stitching, robust scaling, and CNN window generation. Savitzky-Golay window ${diagnostics.detrending?.window_length ?? 101}, polynomial order ${diagnostics.detrending?.polyorder ?? 2}; window size ${diagnostics.windows?.window_size ?? 1024}, stride ${diagnostics.windows?.stride ?? 512}; input shape ${JSON.stringify(result.model?.input_shape || [null, 1024, 1])}.</p><p>Time convention: ${diagnostics.time_system?.label || 'Pipeline time'}. ${diagnostics.time_system?.explanation || 'No time conversion information is available.'}</p>
    <h2>CNN model</h2><p>${result.model?.name || 'Stage 1 CNN'} (${result.model?.version || 'version unavailable'}), input ${JSON.stringify(result.model?.input_shape || [null, 1024, 1])}, ${result.model?.parameters || 'Unavailable'} parameters. Preparation: ${formatNumber(result.timing?.preparation_seconds, 2)} s; inference: ${formatNumber(result.timing?.inference_seconds, 2)} s.</p>
    <h2>Light-curve visualization</h2>${reportLightCurveSvg(result)}
    <h2>Window probability visualization</h2>${reportProbabilitySvg(result)}
    <h2>High-scoring regions</h2><p>These regions represent groups of overlapping windows receiving relatively high CNN scores. They are not independently confirmed transit events.</p><table><thead><tr><th>Region</th><th>Segment</th><th>Start</th><th>End</th><th>Windows</th><th>Mean</th><th>Maximum</th></tr></thead><tbody>${regions.map((region) => `<tr><td>${region.id}</td><td>${region.segment + 1}</td><td>${region.start_time}</td><td>${region.end_time}</td><td>${region.count}</td><td>${region.mean_probability.toFixed(6)}</td><td>${region.max_probability.toFixed(6)}</td></tr>`).join('')}</tbody></table>
    <h2>Window probabilities</h2><table><thead><tr><th>Window</th><th>Probability</th><th>Start JD</th><th>End JD</th><th>Segment</th></tr></thead><tbody>${rows}</tbody></table>
    <h2>Interpretation and limitations</h2><div class="note"><p>${interpretation}</p><p>CNN scores support candidate screening only. They do not establish that the target hosts a confirmed exoplanet. Results depend on the retrieved data and the training-compatible preprocessing pipeline.</p></div></body></html>`;
}

function openPrintableReport(result) {
  // Keep the popup same-origin so its document can be populated before printing.
  const reportWindow = window.open('', '_blank');
  if (!reportWindow) {
    window.alert('Please allow pop-ups for AstroSense to export the PDF report.');
    return false;
  }
  reportWindow.document.open();
  reportWindow.document.write(PrintableReport({ result }));
  reportWindow.document.close();
  reportWindow.focus();
  reportWindow.setTimeout(() => reportWindow.print(), 250);
  return true;
}

function downloadWindowCsv(result) {
  const rows = [['window_index', 'probability', 'above_threshold', 'segment', 'start_time', 'end_time', 'point_start', 'point_end']];
  (result.window_probabilities || []).forEach((probability, index) => {
    const meta = result.window_meta?.[index] || {};
    rows.push([
      index + 1,
      probability,
      probability >= (result.threshold ?? 0.5),
      meta.segment ?? '',
      meta.t_start ?? '',
      meta.t_end ?? '',
      meta.point_start ?? '',
      meta.point_end ?? '',
    ]);
  });
  const csv = rows.map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = `astrosense-kic-${result.kic}-window-predictions.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export default function ExoplanetAnalysis() {
  const [kic, setKic] = useState('');
  const [job, setJob] = useState(null);
  const [result, setResult] = useState(null);
  const [selectedWindowIndex, setSelectedWindowIndex] = useState(null);
  const [selectedRegionId, setSelectedRegionId] = useState(null);
  const [selectedSegmentId, setSelectedSegmentId] = useState(null);
  const [stage, setStage] = useState('scaled_flux');
  const [zoom, setZoom] = useState(1);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [activeModel, setActiveModel] = useState('model1');

  useEffect(() => {
    if (!job || ['done', 'error'].includes(job.status)) return undefined;
    const timer = window.setInterval(async () => {
      try {
        const nextJob = await inferenceService.getJob(job.id);
        setJob(nextJob);
        if (nextJob.status === 'done') {
          setResult(nextJob.result);
          setSelectedWindowIndex(null);
          setSelectedRegionId(null);
          setSelectedSegmentId(null);
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
    setSelectedWindowIndex(null);
    setSelectedRegionId(null);
    setSelectedSegmentId(null);
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

  const selectedWindow = useMemo(() => (
    selectedWindowIndex === null ? null : result?.window_meta?.[selectedWindowIndex]
  ), [result, selectedWindowIndex]);
  const regions = useMemo(() => buildRegions(result), [result]);
  const segmentStats = useMemo(() => buildSegmentStats(result), [result]);
  const selectedRegion = regions.find((region) => region.id === selectedRegionId) || null;
  const selectedSegment = segmentStats.find((segment) => segment.segment === selectedSegmentId) || null;
  const lowestWindowIndex = result?.window_probabilities
    ? result.window_probabilities.indexOf(Math.min(...result.window_probabilities))
    : -1;
  const highestWindowIndex = result?.window_probabilities
    ? result.window_probabilities.indexOf(Math.max(...result.window_probabilities))
    : -1;
  const stageIndex = stages.indexOf(job?.status);
  const diagnostics = result?.diagnostics || {};
  const probabilities = result?.window_probabilities || [];
  const visibleWindowIndices = selectedSegment
    ? selectedSegment.window_indices
    : probabilities.map((_, index) => index);
  const medianProbability = probabilities.length
    ? [...probabilities].sort((a, b) => a - b)[Math.floor(probabilities.length / 2)]
    : null;

  return (
    <div className="dashboard-container analysis-layout">
      <div className="celestial-bg" />
      <MissionSidebar />
      <main className="dashboard-main exoplanet-container">
        <div className="exoplanet-header">
          <span className="eyebrow">MODEL INFERENCE</span>
          <h1>Analyze a Kepler target</h1>
          <p>Retrieve a KIC light curve and inspect the existing CNN candidate-screening result.</p>
        </div>

        {!result && (
          <form className="kic-form" onSubmit={runAnalysis}>
            <label htmlFor="kic-input">Kepler Input Catalog number</label>
            <div className="kic-input-row">
              <input id="kic-input" value={kic} onChange={(event) => setKic(event.target.value)} placeholder="For example, 9850966" inputMode="numeric" disabled={submitting} />
              <button type="submit" className="run-button" disabled={submitting}>{submitting ? 'Analysis running' : 'Analyze KIC'}</button>
            </div>
            <small>Cached MAST data is reused on repeated requests.</small>
          </form>
        )}

        {error && <div className="error-banner"><strong>Analysis unavailable</strong><p>{error}</p></div>}

        {job && !result && job.status !== 'error' && (
          <section className="job-panel">
            <span className="eyebrow">JOB {job.id.slice(0, 8).toUpperCase()}</span>
            <h2>{job.status === 'queued' ? 'Analysis queued' : 'Processing KIC data'}</h2>
            <div className="job-progress">{stages.map((stage, index) => <div className={`job-stage ${index <= stageIndex ? 'active' : ''}`} key={stage}><span>{String(index + 1).padStart(2, '0')}</span>{stage}</div>)}</div>
            <p>MAST retrieval and model inference can take several minutes for a new target.</p>
          </section>
        )}

        {result && (
          <section className="analysis-results">
            <div className="result-heading">
              <div><span className="eyebrow">INFERENCE COMPLETE</span><h2>KIC {result.kic}</h2><p className="result-subtitle">{result.analysis_timestamp || 'Analysis timestamp unavailable'} · CNN candidate screening</p></div>
              <div className="result-actions">
                <button className="back-button" onClick={() => openPrintableReport(result)} type="button">Export PDF report</button>
                <button className="back-button" onClick={() => { setResult(null); setJob(null); setKic(''); }} type="button">Analyze another KIC</button>
              </div>
            </div>

            <div className="model-tabs" role="tablist" aria-label="Model results">
              <button type="button" className={activeModel === 'model1' ? 'model-tab active' : 'model-tab'} onClick={() => setActiveModel('model1')} role="tab" aria-selected={activeModel === 'model1'}>Model 1 · Stage 1 CNN</button>
              <button type="button" className={activeModel === 'model2' ? 'model-tab active' : 'model-tab'} onClick={() => setActiveModel('model2')} role="tab" aria-selected={activeModel === 'model2'} disabled={!result.models?.attention_mil}>Model 2 · AttentionMIL</button>
            </div>

            {activeModel === 'model1' ? (
            <div className="model-tab-panel">
            <div className="prediction-callout">
              <div><span className="eyebrow">PREDICTION SUMMARY</span><h3>{result.pred_max ? 'Candidate window detected' : 'No candidate window above threshold'}</h3><p>Classification uses the maximum window score and the actual {result.threshold ?? 0.5} decision threshold.</p></div>
              <strong className="verdict-badge">{result.pred_max ? 'CANDIDATE' : 'NO CANDIDATE'}</strong>
            </div>

            <div className="metrics-grid">
              <Metric label="Mean probability" value={formatProbability(result.mean_probability)} unit="all windows" />
              <Metric label="Maximum probability" value={formatProbability(result.max_probability)} unit="strongest window" />
              <Metric label="Minimum probability" value={formatProbability(result.min_probability)} unit="lowest window" />
              <Metric label="Decision threshold" value={formatProbability(result.threshold)} unit="maximum-score rule" />
              <Metric label="Windows evaluated" value={result.n_windows} unit={`${result.windows_above_threshold ?? 0} above threshold (${result.n_windows ? ((result.windows_above_threshold / result.n_windows) * 100).toFixed(1) : '0.0'}%)`} />
            </div>

            {result.models?.attention_mil && (
              <div className="prediction-callout">
                <div>
                  <span className="eyebrow">SECOND MODEL</span>
                  <h3>AttentionMIL CNN</h3>
                  <p>
                    Model 2 probability: {formatProbability(result.models.attention_mil.probability)}
                    {' · '}
                    threshold: {formatProbability(result.models.attention_mil.threshold)}
                  </p>
                </div>
                <strong className="verdict-badge">
                  {result.models.attention_mil.is_candidate ? 'CANDIDATE' : 'NO CANDIDATE'}
                </strong>
              </div>
            )}

            <Section title="Target overview" eyebrow="SECTION A" open>
              <div className="detail-grid">
                <div><span>Analysis status</span><strong>Complete</strong></div>
                <div><span>Model</span><strong>{result.model?.name || 'Stage 1 CNN'}</strong></div>
                <div><span>Model version</span><strong>{result.model?.version || 'Unavailable'}</strong></div>
                <div><span>Processing duration</span><strong>{formatNumber(result.timing?.total_seconds, 2)} s</strong></div>
                <div><span>FITS files retrieved</span><strong>{result.n_fits_files}</strong></div>
                <div><span>Observations before / after cleaning</span><strong>{diagnostics.cleaning?.initial_observations ?? 'Unavailable'} / {result.n_observations_processed ?? 'Unavailable'}</strong></div>
                <div><span>Time convention</span><strong>{timeLabel(result)}</strong></div>
              </div>
            </Section>

            <Section title="Data retrieval and preprocessing" eyebrow="SECTION B">
              <div className="stage-list">
                <div><strong>1. MAST data retrieval</strong><span>{diagnostics.retrieval?.n_files_retrieved ?? result.n_fits_files} files retrieved; {diagnostics.retrieval?.n_files_failed ?? result.skipped_files?.length ?? 0} failed or skipped.</span></div>
                <div><strong>2. FITS extraction and cleaning</strong><span>{diagnostics.cleaning?.retained_observations ?? 'Unavailable'} observations retained from {diagnostics.cleaning?.initial_observations ?? 'Unavailable'}; {diagnostics.cleaning?.removed_observations ?? 'Unavailable'} invalid observations removed.</span></div>
                <div><strong>3. Global median normalization</strong><span>{diagnostics.normalization?.method || 'Unavailable'}</span></div>
                <div><strong>4. Savitzky-Golay detrending</strong><span>Window length {diagnostics.detrending?.window_length ?? 101}; polynomial order {diagnostics.detrending?.polyorder ?? 2}.</span></div>
                <div><strong>5. File-level segment stitching</strong><span>{diagnostics.stitching?.n_segments ?? 'Unavailable'} FITS-level segments. Time gaps are diagnostic only; they do not alter segmentation.</span></div>
                <div><strong>6. Robust scaling</strong><span>{diagnostics.scaling?.method || 'Unavailable'}; clip range ±{diagnostics.scaling?.clip ?? 10}.</span></div>
                <div><strong>7. Window generation</strong><span>{diagnostics.windows?.n_windows ?? result.n_windows} windows, size {diagnostics.windows?.window_size ?? 1024}, stride {diagnostics.windows?.stride ?? 512}, overlap {diagnostics.windows?.overlap ?? 512}.</span></div>
              </div>
              {result.skipped_files?.length > 0 && <div className="warning-note"><strong>Data-quality warnings</strong><ul>{result.skipped_files.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}
              <p className="technical-note">{diagnostics.time_system?.explanation || 'Time conversion information is unavailable.'} {diagnostics.time_system?.timesys ? `FITS TIMESYS: ${diagnostics.time_system.timesys}.` : ''}</p>
            </Section>

            <Section title="CNN model and inference details" eyebrow="SECTION C">
              <div className="detail-grid">
                <div><span>Architecture</span><strong>{result.model?.name || 'Stage 1 CNN'}</strong></div>
                <div><span>Input shape</span><strong className="mono">{JSON.stringify(result.model?.input_shape || [null, 1024, 1])}</strong></div>
                <div><span>Total parameters</span><strong>{result.model?.parameters?.toLocaleString() || '64,961'}</strong></div>
                <div><span>Loading status</span><strong>Loaded</strong></div>
                <div><span>Preparation time</span><strong>{formatNumber(result.timing?.preparation_seconds, 2)} s</strong></div>
                <div><span>CNN execution time</span><strong>{formatNumber(result.timing?.inference_seconds, 2)} s</strong></div>
              </div>
              <p className="technical-note">The configuration above describes the loaded model. The timings and window count are measurements from this analysis.</p>
            </Section>

            <Section title="Interactive prediction visualizations" eyebrow="SECTION D" open>
              <div className="visualization-toolbar">
                <label htmlFor="stage-select">Displayed preprocessing stage</label>
                <select id="stage-select" value={stage} onChange={(event) => setStage(event.target.value)}>
                  <option value="retrieved_flux">Retrieved flux</option>
                  <option value="normalized_flux">Median-normalized flux</option>
                  <option value="detrended_flux">Detrended flux</option>
                  <option value="scaled_flux">Final scaled flux supplied to CNN</option>
                </select>
                <span>{getStageSeries(result, stage)?.sampled_points || 0} bounded display points · {timeLabel(result)}</span>
                <label htmlFor="light-curve-zoom">Zoom</label>
                <input id="light-curve-zoom" type="range" min="1" max="4" step="0.5" value={zoom} onChange={(event) => setZoom(Number(event.target.value))} />
                <button type="button" className="back-button compact-button" onClick={() => setZoom(1)}>Reset zoom</button>
              </div>
              <div className="plot-card enhanced-plot-card"><div className="plot-heading"><div><span className="eyebrow">PROCESSED LIGHT CURVE</span><h3>Full stitched signal</h3></div><span className="plot-meta">{getStageSeries(result, stage)?.sampled_points || 0} plotted points</span></div><LightCurveChart result={result} stage={stage} selectedWindow={selectedWindow} selectedRegion={selectedRegion} selectedSegment={selectedSegment} zoom={zoom} /></div>
              <div className="plot-card enhanced-plot-card"><div className="plot-heading"><div><span className="eyebrow">WINDOW ACTIVITY</span><h3>Chronological CNN window timeline</h3></div><span className="plot-meta">Select a window</span></div><WindowTimeline result={result} selectedIndex={selectedWindowIndex} onSelectWindow={(index) => { setSelectedWindowIndex(index); setSelectedRegionId(null); }} /></div>
              <div className="plot-card enhanced-plot-card"><div className="plot-heading"><div><span className="eyebrow">WINDOW OUTPUTS</span><h3>CNN probability by window</h3></div><span className="plot-meta">Click a bar to link the plots</span></div><ProbabilityChart result={result} selectedIndex={selectedWindowIndex} onSelectWindow={setSelectedWindowIndex} /></div>
              <SelectedWindowPanel result={result} selectedIndex={selectedWindowIndex} onSelectWindow={setSelectedWindowIndex} />
              <div className="distribution-grid"><Distribution values={result.window_probabilities || []} title="Window probability distribution" /><Distribution values={getStageSeries(result, stage)?.value || []} title="Displayed flux distribution" color="var(--success)" domain={(() => { const values = getStageSeries(result, stage)?.value || []; return values.length ? [Math.min(...values), Math.max(...values)] : [0, 1]; })()} valueLabel="Displayed flux range" /></div>
              <div className="distribution-summary"><strong>{probabilities.length - (result.windows_above_threshold ?? 0)}</strong> windows below threshold · <strong>{result.windows_above_threshold ?? 0}</strong> above threshold · median <strong>{formatProbability(medianProbability)}</strong></div>
              <RankedWindows result={result} onSelectWindow={(index) => { setSelectedWindowIndex(index); setSelectedRegionId(null); }} />
            </Section>

            <Section title="High-scoring regions" eyebrow="SECTION E">
              <p className="technical-note">These regions represent groups of overlapping windows receiving relatively high CNN scores. They are not independently confirmed transit events.</p>
              {regions.length ? <div className="segment-table-wrap"><table className="segment-table"><thead><tr><th>Region</th><th>Segment</th><th>Time range</th><th>Windows</th><th>Mean</th><th>Maximum</th><th>Minimum</th></tr></thead><tbody>{regions.map((region) => <tr className={selectedRegionId === region.id ? 'selected-row' : ''} key={`region-${region.id}`} onClick={() => { setSelectedRegionId(region.id); setSelectedWindowIndex(region.window_indices[0]); }}><td>R{region.id}</td><td>{region.segment + 1}</td><td>{formatNumber(region.start_time, 4)} – {formatNumber(region.end_time, 4)}</td><td>{region.count}</td><td>{formatProbability(region.mean_probability)}</td><td>{formatProbability(region.max_probability)}</td><td>{formatProbability(region.min_probability)}</td></tr>)}</tbody></table></div> : <p className="empty-state">No above-threshold overlapping regions were found.</p>}
            </Section>

            <Section title="Segment comparison" eyebrow="SECTION F">
              <SegmentComparison segments={segmentStats} selectedSegment={selectedSegment} onSelectSegment={(segment) => { setSelectedSegmentId(segment); setSelectedRegionId(null); }} />
              <div className="segment-table-wrap"><table className="segment-table"><thead><tr><th>Segment</th><th>Source FITS</th><th>Observations</th><th>Windows</th><th>Mean</th><th>Maximum</th><th>Above threshold</th><th>Gap</th></tr></thead><tbody>{segmentStats.map((segment) => <tr className={selectedSegmentId === segment.segment ? 'selected-row' : ''} key={`segment-row-${segment.segment}`} onClick={() => setSelectedSegmentId(segment.segment)}><td>S{segment.segment + 1}</td><td>{segment.source_file || 'Unavailable'}</td><td>{segment.length}</td><td>{segment.n_windows}</td><td>{formatProbability(segment.mean_probability)}</td><td>{formatProbability(segment.max_probability)}</td><td>{segment.above_threshold} ({formatNumber(segment.above_percentage, 1)}%)</td><td>{formatNumber(segment.max_time_gap, 5)}</td></tr>)}</tbody></table></div>
            </Section>

            <Section title="How was this verdict reached?" eyebrow="SECTION G" open>
              <div className="metrics-grid compact-metrics">
                <Metric label="Minimum probability" value={formatProbability(result.min_probability)} />
                <Metric label="Median probability" value={formatProbability(medianProbability)} />
                <Metric label="Above threshold" value={`${result.windows_above_threshold ?? 'Unavailable'} / ${result.n_windows}`} />
                <Metric label="Highest window" value={highestWindowIndex >= 0 ? `#${highestWindowIndex + 1}` : 'Unavailable'} />
                <Metric label="Lowest window" value={lowestWindowIndex >= 0 ? `#${lowestWindowIndex + 1}` : 'Unavailable'} />
              </div>
              <Interpretation result={result} />
              <p className="technical-note">The backend computes the mean and maximum across individual CNN window probabilities. The final target-level verdict is <strong>pred_max</strong>: candidate when the maximum probability is at least the {formatProbability(result.threshold)} threshold; otherwise no candidate. The mean is reported for context and does not determine this verdict.</p>
              <div className="top-window"><span className="eyebrow">HIGHEST-SCORING WINDOW</span><p>{result.top_window ? `${formatNumber(result.top_window.t_start, 3)} to ${formatNumber(result.top_window.t_end, 3)} ${timeLabel(result)} · segment ${Number(result.top_window.segment) + 1}` : 'Unavailable'}</p><strong>{formatProbability(result.max_probability)} window probability</strong></div>
            </Section>

            <Section title="Individual window predictions" eyebrow="ADVANCED">
              <div className="table-actions"><button type="button" className="back-button" onClick={() => downloadWindowCsv(result)}>Download window CSV</button></div>
              <div className="window-table-wrap"><table className="segment-table"><thead><tr><th>Window</th><th>Probability</th><th>Threshold</th><th>Segment</th><th>Start</th><th>End</th></tr></thead><tbody>{visibleWindowIndices.map((index) => { const probability = result.window_probabilities[index]; const meta = result.window_meta?.[index] || {}; return <tr className={index === selectedWindowIndex ? 'selected-row' : ''} key={`window-row-${index}`} onClick={() => setSelectedWindowIndex(index)}><td>#{index + 1}</td><td>{formatProbability(probability)}</td><td>{probability >= (result.threshold ?? 0.5) ? 'Above' : 'Below'}</td><td>{Number.isFinite(meta.segment) ? meta.segment + 1 : 'Unavailable'}</td><td>{formatNumber(meta.t_start, 3)}</td><td>{formatNumber(meta.t_end, 3)}</td></tr>; })}</tbody></table></div>
            </Section>
            </div>
            ) : (
              <ModelTwoDetails result={result} />
            )}
          </section>
        )}
      </main>
    </div>
  );
}
