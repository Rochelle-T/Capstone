"""
kepler_pipeline.py
==================
KIC number  ->  MAST download  ->  FITS->NPZ standardization  ->  Savitzky-Golay
detrending  ->  segment stitching  ->  robust scaling  ->  1024-pt windows  ->  CNN.

Every numeric constant below is copied from the training notebooks. Do NOT change
them unless you retrain the model:

  * flux column priority      : PDCSAP_FLUX first            (standardization notebook)
  * normalisation             : flux / median(flux)          (processing notebook)
  * Savitzky-Golay            : window=101 points, polyorder=2, processed = flux / baseline
  * robust scaling per segment: (x - median) / (1.4826 * MAD), std fallback, clip [-10, 10]
  * windows                   : size 1024, stride 512, never crossing a segment boundary
  * model input               : (N, 1024, 1) float32

ASSUMPTION (the stitching code was not in the notebooks you sent):
  one segment = one Kepler quarter file; Savitzky-Golay is applied per file;
  files are sorted by time and concatenated; segment_id = index of the source file.
  If your original stitching differs, edit `stitch_segments()` only.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
from astropy.io import fits
from scipy.signal import savgol_filter

log = logging.getLogger("kepler_pipeline")


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PipelineConfig:
    # --- must match training ---
    window_size: int = 1024
    stride: int = 512
    savgol_window: int = 101
    savgol_polyorder: int = 2
    clip: float = 10.0
    global_normalization: bool = True
    min_points: int = 10
    # --- inference-time choices ---
    lc_only: bool = True               # long cadence only (windows of 1024 pts assume LC spacing)
    apply_quality_mask: bool = False   # training did NOT mask quality flags; keep False for parity
    dedupe_quarters: bool = True       # keep one file per quarter if MAST returns several versions
    cache_dir: Path = Path("./kepler_cache")


FLUX_PRIORITY = ["PDCSAP_FLUX", "SAP_FLUX", "FLUX", "KSPSAP_FLUX",
                 "COR_FLUX", "CORRECTED_FLUX", "NORMALIZED_FLUX"]
FLUX_ERR_PRIORITY = ["PDCSAP_FLUX_ERR", "SAP_FLUX_ERR", "FLUX_ERR"]


# --------------------------------------------------------------------------- #
# 1. KIC parsing + MAST download
# --------------------------------------------------------------------------- #
def parse_kic(value) -> int:
    """Accepts 9850966, '9850966', 'KIC 9850966', 'KIC_9850966', 'kplr009850966'."""
    m = re.search(r"(\d+)", str(value))
    if not m:
        raise ValueError(f"Cannot parse a KIC number from {value!r}")
    return int(m.group(1))


def download_fits(kic: int, cfg: PipelineConfig) -> list[Path]:
    """Download (or reuse cached) Kepler light-curve FITS files for one KIC from MAST."""
    from astroquery.mast import Observations  # lazy import

    raw_dir = Path(cfg.cache_dir) / "raw" / f"KIC_{kic}"
    suffixes = ("_llc.fits",) if cfg.lc_only else ("_llc.fits", "_slc.fits")

    def local_files() -> list[Path]:
        return sorted(p for p in raw_dir.rglob("*.fits") if p.name.lower().endswith(suffixes))

    cached = local_files()
    if cached:
        log.info("KIC %s: using %d cached FITS files", kic, len(cached))
        return cached

    raw_dir.mkdir(parents=True, exist_ok=True)
    obs = Observations.query_criteria(obs_collection="Kepler", target_name=f"kplr{kic:09d}")
    if len(obs) == 0:
        raise LookupError(f"KIC {kic}: no Kepler observations found on MAST")

    products = Observations.get_product_list(obs)
    keep = np.array([str(f).lower().endswith(suffixes) for f in products["productFilename"]])
    products = products[keep]
    if len(products) == 0:
        raise LookupError(f"KIC {kic}: no light-curve FITS products on MAST")

    Observations.download_products(products, download_dir=str(raw_dir), mrp_only=False)
    files = local_files()
    if not files:
        raise RuntimeError(f"KIC {kic}: download finished but no FITS files found in {raw_dir}")
    log.info("KIC %s: downloaded %d FITS files", kic, len(files))
    return files


# --------------------------------------------------------------------------- #
# 2. FITS -> standardized arrays (-> optional NPZ)
# --------------------------------------------------------------------------- #
def _find_column(data, candidates) -> Optional[str]:
    names = getattr(data, "names", None)
    if names is None:
        return None
    upper = {str(n).upper(): n for n in names}
    for c in candidates:
        if c.upper() in upper:
            return upper[c.upper()]
    return None


def extract_lightcurve(fits_path: Path, apply_quality_mask: bool = False,
                       min_points: int = 10) -> dict:
    """Same logic as the standardization notebook: first HDU holding TIME + a flux column."""
    with fits.open(fits_path, memmap=True) as hdul:
        primary_header = hdul[0].header
        quarter = primary_header.get("QUARTER", None)
        time_metadata = {
            "timesys": primary_header.get("TIMESYS"),
            "timeunit": primary_header.get("TIMEUNIT"),
            "bjdrefi": primary_header.get("BJDREFI"),
            "bjdreff": primary_header.get("BJDREFF"),
        }
        for hdu in hdul:
            data = getattr(hdu, "data", None)
            if data is None or getattr(data, "names", None) is None:
                continue
            tcol = _find_column(data, ["TIME"])
            fcol = _find_column(data, FLUX_PRIORITY)
            if tcol is None or fcol is None:
                continue
            table_header = hdu.header
            for key in ("TIMESYS", "TIMEUNIT", "BJDREFI", "BJDREFF"):
                metadata_key = key.lower()
                if time_metadata[metadata_key] is None and key in table_header:
                    time_metadata[metadata_key] = table_header[key]

            time = np.asarray(data[tcol], dtype=np.float64)
            flux = np.asarray(data[fcol], dtype=np.float64)
            n_original = len(time)

            ecol = _find_column(data, FLUX_ERR_PRIORITY)
            flux_err = (np.asarray(data[ecol], dtype=np.float64) if ecol
                        else np.full(len(flux), np.nan))
            qcol = _find_column(data, ["SAP_QUALITY", "QUALITY"])
            quality = (np.asarray(data[qcol]).astype(np.int32) if qcol
                       else np.zeros(len(flux), np.int32))
            ccol = _find_column(data, ["CADENCENO"])
            cadenceno = (np.asarray(data[ccol]).astype(np.int64) if ccol
                         else np.arange(len(flux), dtype=np.int64))

            valid = np.isfinite(time) & np.isfinite(flux)
            if apply_quality_mask:
                valid &= quality == 0
            time, flux, flux_err, quality, cadenceno = (
                a[valid] for a in (time, flux, flux_err, quality, cadenceno))
            if len(time) < min_points:
                continue

            order = np.argsort(time)
            return {
                "time": time[order], "flux": flux[order], "flux_err": flux_err[order],
                "quality": quality[order], "cadenceno": cadenceno[order],
                "flux_column": str(fcol), "quarter": quarter,
                "original_n_points": n_original,
                "standardized_n_points": int(len(time)),
                "source_file": fits_path.name,
                "time_metadata": time_metadata,
            }
    raise ValueError(f"{fits_path.name}: no suitable TIME + FLUX table found")


def save_standardized_npz(lc: dict, out_path: Path, kic: int, label: int = -1) -> Path:
    """Write the exact NPZ schema used in training (label=-1 means unknown at inference)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(out_path.name + ".tmp")
    with open(tmp, "wb") as f:
        np.savez_compressed(
            f, time=lc["time"], flux=lc["flux"], flux_err=lc["flux_err"],
            quality=lc["quality"], cadenceno=lc["cadenceno"],
            kic=np.array(f"KIC {kic}"), source_file=np.array(lc["source_file"]),
            original_n_points=np.array(lc["original_n_points"], dtype=np.int64),
            standardized_n_points=np.array(lc["standardized_n_points"], dtype=np.int64),
            target=np.array(f"KIC {kic}"), label=np.array(label, dtype=np.int64))
    tmp.replace(out_path)
    return out_path


# --------------------------------------------------------------------------- #
# 3. Savitzky-Golay detrending (per file, as in the processing notebook)
# --------------------------------------------------------------------------- #
def _make_odd(v: int) -> int:
    v = max(3, int(v))
    return v + 1 if v % 2 == 0 else v


def savgol_detrend(time, flux, cfg: PipelineConfig) -> dict:
    t = np.asarray(time, dtype=np.float64)
    f = np.asarray(flux, dtype=np.float64)
    ok = np.isfinite(t) & np.isfinite(f)
    if ok.sum() < cfg.min_points:
        raise ValueError("Not enough valid points for processing.")
    t, f = t[ok], f[ok]

    normalization_median = None
    f_work = f
    if cfg.global_normalization:
        med = np.nanmedian(f)
        if np.isfinite(med) and med != 0:
            normalization_median = float(med)
            f_work = f / med

    window = _make_odd(cfg.savgol_window)
    if window >= len(f_work):
        window = len(f_work) - 1
        if window % 2 == 0:
            window -= 1
    if window <= cfg.savgol_polyorder:
        raise ValueError("Savitzky-Golay window must exceed polynomial order.")

    baseline = savgol_filter(f_work, window_length=window, polyorder=cfg.savgol_polyorder)
    processed = f_work / baseline

    good = np.isfinite(processed) & np.isfinite(baseline)
    return {
        "time": t[good],
        "flux_processed": processed[good],
        "baseline": baseline[good],
        "flux_normalized": f_work[good],
        "normalization_median": normalization_median,
    }


# --------------------------------------------------------------------------- #
# 4. Stitching  (EDIT HERE if your original stitching was different)
# --------------------------------------------------------------------------- #
def stitch_segments(per_file: list[dict]) -> dict:
    """per_file: list of {'time','flux_processed','quarter',...}.
    Returns a stitched dict with time, flux, segment_id (one id per source file)."""
    per_file = sorted(per_file, key=lambda d: d["time"][0])
    time = np.concatenate([d["time"] for d in per_file])
    flux = np.concatenate([d["flux_processed"] for d in per_file])
    seg = np.concatenate([np.full(len(d["time"]), i, dtype=np.int32)
                          for i, d in enumerate(per_file)])
    return {"time": time, "flux": flux, "segment_id": seg,
            "source_files": [d["source_file"] for d in per_file]}


# --------------------------------------------------------------------------- #
# 5. Final preprocessing before the CNN (same as training notebook, cells 4-5)
# --------------------------------------------------------------------------- #
def robust_scale_segments(stitched: dict, cfg: PipelineConfig) -> list[tuple[np.ndarray, np.ndarray]]:
    """Per-segment median/MAD scaling (std fallback), clipped. Returns [(time, scaled_flux)]."""
    time, flux, seg = stitched["time"], stitched["flux"], stitched["segment_id"]
    out = []
    for sid in dict.fromkeys(seg.tolist()):
        m = seg == sid
        t = time[m]
        v = flux[m].astype(np.float64)
        fin = np.isfinite(v)
        t, v = t[fin], v[fin]
        if len(v) < 2:
            continue
        med = np.median(v)
        scale = 1.4826 * np.median(np.abs(v - med))
        if not np.isfinite(scale) or scale < 1e-12:
            scale = np.std(v)
        if not np.isfinite(scale) or scale < 1e-12:
            continue
        v = np.clip((v - med) / scale, -cfg.clip, cfg.clip).astype(np.float32)
        if np.isfinite(v).all():
            out.append((t, v))
    return out


def make_windows(scaled_segments, cfg: PipelineConfig):
    """Sliding windows inside each segment. Returns X (N,1024,1) float32 and window metadata."""
    parts, meta = [], []
    global_offset = 0
    for si, (t, v) in enumerate(scaled_segments):
        if len(v) < cfg.window_size:
            global_offset += len(v)
            continue
        view = np.lib.stride_tricks.sliding_window_view(v, cfg.window_size)[::cfg.stride]
        starts = np.arange(0, len(v) - cfg.window_size + 1, cfg.stride)
        parts.append(np.asarray(view, dtype=np.float32).copy())
        for s in starts:
            meta.append({
                "segment": si,
                "point_start": int(global_offset + s),
                "point_end": int(global_offset + s + cfg.window_size - 1),
                "segment_point_start": int(s),
                "segment_point_end": int(s + cfg.window_size - 1),
                "t_start": float(t[s]),
                "t_end": float(t[s + cfg.window_size - 1]),
            })
        global_offset += len(v)
    if not parts:
        return np.empty((0, cfg.window_size, 1), np.float32), []
    X = np.concatenate(parts, axis=0)[..., None]
    return X, meta


# --------------------------------------------------------------------------- #
# 6. End-to-end
# --------------------------------------------------------------------------- #
@dataclass
class PreparedKIC:
    kic: int
    X: np.ndarray                      # (N, 1024, 1) ready for model.predict
    window_meta: list[dict]
    stitched: dict                     # detrended, unscaled (for plotting)
    fits_files: list[Path]
    skipped: list[str] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)


def _sample_series(time_values, value_values, max_points: int = 2500) -> dict:
    """Return a bounded, faithful sample for diagnostics and browser rendering."""
    times = np.asarray(time_values)
    values = np.asarray(value_values)
    if len(times) <= max_points:
        indices = np.arange(len(times))
    else:
        indices = np.linspace(0, len(times) - 1, max_points, dtype=np.int64)
    return {
        "time": times[indices].astype(float).tolist(),
        "value": values[indices].astype(float).tolist(),
        "n_points": int(len(times)),
        "sampled_points": int(len(indices)),
    }


def prepare_kic(kic_input, cfg: PipelineConfig = PipelineConfig(),
                save_npz: bool = True) -> PreparedKIC:
    kic = parse_kic(kic_input)
    files = download_fits(kic, cfg)

    per_file, skipped, seen_quarters = [], [], {}
    initial_observations = 0
    retained_observations = 0
    file_diagnostics = []
    for fp in files:
        try:
            lc = extract_lightcurve(fp, cfg.apply_quality_mask, cfg.min_points)
            initial_observations += int(lc["original_n_points"])
            retained_observations += int(lc["standardized_n_points"])
            if save_npz:
                save_standardized_npz(
                    lc, Path(cfg.cache_dir) / "standardized" / f"KIC_{kic}" / (fp.stem + ".npz"), kic)
            det = savgol_detrend(lc["time"], lc["flux"], cfg)
            det["source_file"] = fp.name
            det["quarter"] = lc["quarter"]
            det["time_metadata"] = lc["time_metadata"]
            file_diagnostics.append({
                "source_file": fp.name,
                "quarter": lc["quarter"],
                "initial_observations": int(lc["original_n_points"]),
                "retained_observations": int(lc["standardized_n_points"]),
                "removed_observations": int(
                    lc["original_n_points"] - lc["standardized_n_points"]
                ),
                "normalization_median": det["normalization_median"],
                "time_metadata": lc["time_metadata"],
                "raw_series": _sample_series(lc["time"], lc["flux"]),
                "normalized_series": _sample_series(
                    det["time"], det["flux_normalized"]
                ),
                "detrended_series": _sample_series(
                    det["time"], det["flux_processed"]
                ),
            })
            if cfg.dedupe_quarters and lc["quarter"] is not None:
                seen_quarters[lc["quarter"]] = det     # later filename wins
            else:
                per_file.append(det)
        except Exception as e:                          # one bad quarter must not kill the run
            skipped.append(f"{fp.name}: {e}")
            log.warning("skipping %s: %s", fp.name, e)
    per_file.extend(seen_quarters.values())
    if not per_file:
        raise RuntimeError(f"KIC {kic}: no usable light-curve files ({len(skipped)} failed)")

    stitched = stitch_segments(per_file)
    scaled = robust_scale_segments(stitched, cfg)
    X, meta = make_windows(scaled, cfg)
    if len(X) == 0:
        raise RuntimeError(f"KIC {kic}: no segment is long enough for a {cfg.window_size}-point window")
    segment_diagnostics = []
    scaled_flux_parts = []
    for segment_index, (segment_time, segment_flux) in enumerate(scaled):
        source_mask = stitched["segment_id"] == segment_index
        source_files = stitched["source_files"]
        source_file = source_files[segment_index] if segment_index < len(source_files) else None
        gaps = np.diff(segment_time)
        scaled_flux_parts.append(segment_flux)
        segment_diagnostics.append({
            "segment": segment_index,
            "source_file": source_file,
            "length": int(len(segment_time)),
            "time_start": float(segment_time[0]),
            "time_end": float(segment_time[-1]),
            "max_time_gap": float(np.max(gaps)) if len(gaps) else 0.0,
            "median_time_gap": float(np.median(gaps)) if len(gaps) else 0.0,
            "scaled_min": float(np.min(segment_flux)),
            "scaled_max": float(np.max(segment_flux)),
            "scaled_mean": float(np.mean(segment_flux)),
            "scaled_series": _sample_series(segment_time, segment_flux),
            "stitched_points": int(np.count_nonzero(source_mask)),
        })

    diagnostics = {
        "retrieval": {
            "target": f"KIC {kic}",
            "n_files_retrieved": int(len(files)),
            "n_files_processed": int(len(per_file)),
            "n_files_failed": int(len(skipped)),
            "failed_files": skipped,
        },
        "cleaning": {
            "initial_observations": int(initial_observations),
            "retained_observations": int(retained_observations),
            "removed_observations": int(initial_observations - retained_observations),
            "quality_mask_applied": bool(cfg.apply_quality_mask),
        },
        "normalization": {
            "method": "global median normalization per FITS segment",
            "enabled": bool(cfg.global_normalization),
            "segment_medians": [
                {"source_file": item["source_file"], "median": item["normalization_median"]}
                for item in file_diagnostics
            ],
        },
        "detrending": {
            "method": "Savitzky-Golay baseline division",
            "window_length": int(cfg.savgol_window),
            "polyorder": int(cfg.savgol_polyorder),
        },
        "files": file_diagnostics,
        "time_system": {
            "label": "Pipeline time",
            "timesys": next(
                (item["time_metadata"].get("timesys")
                 for item in file_diagnostics
                 if item.get("time_metadata", {}).get("timesys")),
                None,
            ),
            "timeunit": next(
                (item["time_metadata"].get("timeunit")
                 for item in file_diagnostics
                 if item.get("time_metadata", {}).get("timeunit")),
                None,
            ),
            "bjdref": next(
                (
                    {
                        "integer": item["time_metadata"].get("bjdrefi"),
                        "fraction": item["time_metadata"].get("bjdreff"),
                    }
                    for item in file_diagnostics
                    if item.get("time_metadata", {}).get("bjdrefi") is not None
                    or item.get("time_metadata", {}).get("bjdreff") is not None
                ),
                None,
            ),
            "explanation": (
                "FITS TIME values are passed through unchanged; no BJD conversion is performed."
            ),
        },
        "segments": segment_diagnostics,
        "stitching": {
            "n_segments": int(len(segment_diagnostics)),
            "source_files": stitched["source_files"],
        },
        "scaling": {
            "method": "per-segment median/MAD with standard-deviation fallback",
            "mad_constant": 1.4826,
            "clip": float(cfg.clip),
        },
        "windows": {
            "window_size": int(cfg.window_size),
            "stride": int(cfg.stride),
            "overlap": int(cfg.window_size - cfg.stride),
            "n_windows": int(len(X)),
        },
        "stitched_series": _sample_series(
            stitched["time"], stitched["flux"]
        ),
        "scaled_series": _sample_series(
            np.concatenate([segment[0] for segment in scaled]),
            np.concatenate(scaled_flux_parts),
        ),
    }
    stage_series = {}
    for key, source_key in (
        ("retrieved_flux", "raw_series"),
        ("normalized_flux", "normalized_series"),
        ("detrended_flux", "detrended_series"),
    ):
        stage_series[key] = {
            "time": [
                value
                for item in file_diagnostics
                for value in item[source_key]["time"]
            ],
            "value": [
                value
                for item in file_diagnostics
                for value in item[source_key]["value"]
            ],
            "sampled_points": sum(
                item[source_key]["sampled_points"] for item in file_diagnostics
            ),
        }
    diagnostics["stage_series"] = stage_series
    return PreparedKIC(kic, X, meta, stitched, files, skipped, diagnostics)


_MODEL = {}


def load_model(model_path):
    import tensorflow as tf
    key = str(model_path)
    if key not in _MODEL:
        _MODEL[key] = tf.keras.models.load_model(key, compile=False)
    return _MODEL[key]


def predict_kic(kic_input, model_path, cfg: PipelineConfig = PipelineConfig(),
                threshold: float = 0.5, batch_size: int = 128) -> dict:
    started_at = time.time()
    preparation_started = time.perf_counter()
    prep = prepare_kic(kic_input, cfg)
    preparation_seconds = time.perf_counter() - preparation_started
    model = load_model(model_path)
    inference_started = time.perf_counter()
    probs = model.predict(prep.X, batch_size=batch_size, verbose=0).reshape(-1)
    inference_seconds = time.perf_counter() - inference_started
    mean_p, max_p = float(np.mean(probs)), float(np.max(probs))
    best = int(np.argmax(probs))
    min_p = float(np.min(probs))
    above_threshold = int(np.count_nonzero(probs >= threshold))
    model_metadata = {
        "name": "Stage 1 CNN",
        "version": Path(model_path).name,
        "input_shape": [None, 1024, 1],
        "output_shape": [None, 1],
        "parameters": int(model.count_params()),
        "loading": "TensorFlow/Keras",
    }
    return {
        "kic": prep.kic,
        "analysis_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": model_metadata,
        "threshold": float(threshold),
        "n_windows": int(len(probs)),
        "mean_probability": mean_p,
        "max_probability": max_p,
        "min_probability": min_p,
        "windows_above_threshold": above_threshold,
        "pred_mean": int(mean_p >= threshold),
        "pred_max": int(max_p >= threshold),
        "window_probabilities": probs.tolist(),
        "window_meta": prep.window_meta,
        "top_window": {**prep.window_meta[best], "probability": float(probs[best])},
        "n_fits_files": len(prep.fits_files),
        "skipped_files": prep.skipped,
        "n_observations_processed": prep.diagnostics["cleaning"]["retained_observations"],
        "timing": {
            "preparation_seconds": float(preparation_seconds),
            "inference_seconds": float(inference_seconds),
            "total_seconds": float(time.time() - started_at),
        },
        "diagnostics": prep.diagnostics,
        "_fits_files": prep.fits_files,
        "stitched": {
            "time": prep.stitched["time"].tolist(),
            "flux": prep.stitched["flux"].tolist(),
            "segment_id": prep.stitched["segment_id"].tolist(),
        },
    }


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("kic")
    ap.add_argument("--model", required=True)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    r = predict_kic(a.kic, a.model)
    r.pop("window_probabilities"); r.pop("window_meta")
    print(json.dumps(r, indent=2))
