"""
kepler_pipeline.py
==================
Inference-time pipeline:  KIC id  ->  MAST download  ->  FITS standardisation
-> Savitzky-Golay detrending  ->  windowing  ->  "bag" tensor for the
AttentionMIL CNN.

It re-implements, step for step, what the training notebooks did:

  Notebook 1 (fits -> npz)         : extract_lightcurve(), standardize_fits()
  Notebook 2 (savgol preprocessing): process_flux_savgol()
  Notebook 3 (CNN training)        : build_window_specs(), select_windows(),
                                     build_bag()   (x = flux_processed - 1.0)

IMPORTANT: every constant in the CONFIG block must stay identical to the values
used for training, otherwise the model sees a different input distribution.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
from astropy.io import fits
from scipy.signal import savgol_filter

log = logging.getLogger("kepler_pipeline")

# =============================================================================
# CONFIG  (must match training: Experiment B, savgol, gap 2.5)
# =============================================================================
# --- preprocessing (notebook 2) ---
GLOBAL_NORMALIZATION = True      # divide each file's flux by its median first
SAVGOL_WINDOW_POINTS = 101       # in samples (index space, not days)
SAVGOL_POLYORDER = 2

# --- windowing (notebook 3) ---
WINDOW_LENGTH = 1024
WINDOW_STRIDE = 512
GAP_FACTOR = 2.5                 # a gap > GAP_FACTOR * median cadence splits a segment
MAX_WINDOWS_PER_KIC = 32         # Experiment B; None = keep all windows

MIN_VALID_POINTS = 10            # files with fewer finite points are skipped

# Training kept BOTH long cadence (_llc) and short cadence (_slc) files.
INCLUDE_SHORT_CADENCE_DEFAULT = True

# Column priority when searching the FITS table (notebook 1)
FLUX_PRIORITY = [
    "PDCSAP_FLUX", "SAP_FLUX", "FLUX", "KSPSAP_FLUX", "COR_FLUX",
    "CORRECTED_FLUX", "NORMALIZED_FLUX", "LIGHTCURVE", "LC",
]
FLUX_ERR_PRIORITY = ["PDCSAP_FLUX_ERR", "SAP_FLUX_ERR", "FLUX_ERR"]


# =============================================================================
# Errors
# =============================================================================
class PipelineError(Exception):
    """Base class for pipeline failures (message is safe to show to a user)."""


class KICNotFoundError(PipelineError):
    """No Kepler observations exist on MAST for this KIC."""


class NoUsableDataError(PipelineError):
    """Data was found but no valid 1024-point window could be built."""


# =============================================================================
# STEP 0 - input handling
# =============================================================================
def parse_kic(value) -> int:
    """Accept 9850966, '9850966', 'KIC 9850966', 'KIC_9850966', 'kplr009850966'."""
    s = str(value).strip().upper().replace("_", " ")
    for prefix in ("KIC", "KPLR"):
        if s.startswith(prefix):
            s = s[len(prefix):].strip()
    if s.endswith(".0"):
        s = s[:-2]
    if not s.isdigit():
        raise PipelineError(f"'{value}' is not a valid KIC id.")
    return int(s)


# =============================================================================
# STEP 1 - fetch FITS files from MAST (Kepler archive)
# =============================================================================
def download_kepler_fits(
    kic: int,
    out_dir: Path,
    include_short_cadence: bool = INCLUDE_SHORT_CADENCE_DEFAULT,
    retries: int = 3,
) -> list[Path]:
    """Download all Kepler light-curve FITS (long cadence, optionally short
    cadence) for one KIC. Returns a sorted list of local file paths."""
    from astroquery.mast import Observations  # imported lazily (network dep)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cached = sorted(out_dir.rglob("*_llc.fits"))
    if include_short_cadence:
        cached_short = sorted(out_dir.rglob("*_slc.fits"))
        if cached and cached_short:
            return cached + cached_short
    elif cached:
        return cached

    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            obs = Observations.query_criteria(
                target_name=f"kplr{kic:09d}",
                obs_collection="Kepler",
            )
            if len(obs) == 0:
                raise KICNotFoundError(f"KIC {kic} has no Kepler observations on MAST.")

            products = Observations.get_product_list(obs)

            suffixes = ("_llc.fits",) + (("_slc.fits",) if include_short_cadence else ())
            keep = np.array(
                [str(name).lower().endswith(suffixes) for name in products["productFilename"]],
                dtype=bool,
            )
            products = products[keep]
            if len(products) == 0:
                raise KICNotFoundError(f"KIC {kic}: no light-curve FITS products found.")

            manifest = Observations.download_products(
                products, download_dir=str(out_dir), cache=True, mrp_only=False
            )
            paths = [
                Path(p) for p, s in zip(manifest["Local Path"], manifest["Status"])
                if s in ("COMPLETE", "SKIPPED") and Path(p).is_file()
            ]
            if not paths:
                raise PipelineError(f"KIC {kic}: download returned no files.")
            return sorted(paths, key=lambda p: p.name)

        except KICNotFoundError:
            raise                                   # no point retrying
        except Exception as e:                      # network hiccups on MAST are common
            last_err = e
            log.warning("MAST attempt %d/%d failed: %r", attempt, retries, e)
            time.sleep(2 * attempt)

    raise PipelineError(f"Could not download KIC {kic} from MAST: {last_err!r}")


# =============================================================================
# STEP 2 - FITS -> standardised light curve (notebook 1: "FITS -> NPZ")
# =============================================================================
@dataclass
class StandardizedLC:
    time: np.ndarray
    flux: np.ndarray
    flux_err: np.ndarray
    quality: np.ndarray
    cadenceno: np.ndarray
    source_file: str
    original_n_points: int
    flux_column: str

    @property
    def n_points(self) -> int:
        return len(self.time)


def _find_column(names, candidates) -> Optional[str]:
    """Case-insensitive lookup of the first matching column name."""
    upper = {str(n).upper(): n for n in names}
    for c in candidates:
        if c.upper() in upper:
            return upper[c.upper()]
    return None


def extract_lightcurve(fits_path: Path) -> dict:
    """Search all HDUs for a table with TIME + a flux column.
    No quality-flag filtering is applied (matches training)."""
    with fits.open(fits_path, memmap=True) as hdul:
        for hdu in hdul:
            data = getattr(hdu, "data", None)
            names = getattr(data, "names", None)
            if data is None or names is None:
                continue

            time_col = _find_column(names, ["TIME"])
            if time_col is None:
                continue

            original_n = len(data[time_col])

            flux_col = _find_column(names, FLUX_PRIORITY)
            if flux_col is None:
                # Fallback: accept the table only if it has exactly one numeric
                # non-bookkeeping column.
                excluded = {"TIME", "CADENCENO", "SAP_QUALITY", "QUALITY"}
                numeric = []
                for n in names:
                    if str(n).upper() in excluded:
                        continue
                    try:
                        if np.issubdtype(np.asarray(data[n]).dtype, np.number):
                            numeric.append(n)
                    except Exception:
                        continue
                if len(numeric) == 1:
                    flux_col = numeric[0]
            if flux_col is None:
                continue

            time_arr = np.asarray(data[time_col], dtype=np.float64)
            flux = np.asarray(data[flux_col], dtype=np.float64)

            err_col = _find_column(names, FLUX_ERR_PRIORITY)
            flux_err = (np.asarray(data[err_col], dtype=np.float64)
                        if err_col is not None
                        else np.full(len(flux), np.nan))

            q_col = _find_column(names, ["SAP_QUALITY", "QUALITY"])
            quality = (np.asarray(data[q_col]).astype(np.int64)
                       if q_col is not None
                       else np.zeros(len(flux), dtype=np.int64))

            c_col = _find_column(names, ["CADENCENO"])
            cadenceno = (np.asarray(data[c_col]).astype(np.int64)
                         if c_col is not None
                         else np.arange(len(flux), dtype=np.int64))

            # Drop non-finite time/flux (NaNs are Kepler's flagged cadences)
            valid = np.isfinite(time_arr) & np.isfinite(flux)
            time_arr, flux = time_arr[valid], flux[valid]
            flux_err, quality, cadenceno = flux_err[valid], quality[valid], cadenceno[valid]

            if len(time_arr) < MIN_VALID_POINTS:
                continue

            order = np.argsort(time_arr)            # chronological order
            return {
                "time": time_arr[order],
                "flux": flux[order],
                "flux_err": flux_err[order],
                "quality": quality[order],
                "cadenceno": cadenceno[order],
                "flux_column": str(flux_col),
                "original_n_points": int(original_n),
            }

    raise ValueError("No suitable TIME + FLUX table found.")


def standardize_fits(fits_path: Path) -> StandardizedLC:
    """In-memory equivalent of the notebook-1 NPZ (nothing is written to disk)."""
    r = extract_lightcurve(Path(fits_path))
    return StandardizedLC(
        time=r["time"], flux=r["flux"], flux_err=r["flux_err"],
        quality=r["quality"], cadenceno=r["cadenceno"],
        source_file=Path(fits_path).name,
        original_n_points=r["original_n_points"],
        flux_column=r["flux_column"],
    )


def save_standardized_npz(lc: StandardizedLC, kic: int, out_path: Path) -> None:
    """OPTIONAL: persist the standardised curve with the same schema as training
    (useful for caching or debugging). 'label' is unknown at inference, so -1."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(out_path.name + ".tmp")
    with open(tmp, "wb") as f:
        np.savez_compressed(
            f, time=lc.time, flux=lc.flux, flux_err=lc.flux_err,
            quality=lc.quality, cadenceno=lc.cadenceno,
            kic=np.array(f"KIC {kic}"), source_file=np.array(lc.source_file),
            original_n_points=np.array(lc.original_n_points, dtype=np.int64),
            standardized_n_points=np.array(lc.n_points, dtype=np.int64),
            target=np.array(f"KIC {kic}"), label=np.array(-1, dtype=np.int64),
        )
    tmp.replace(out_path)


# =============================================================================
# STEP 3 - Savitzky-Golay detrending (notebook 2, method="savgol")
# =============================================================================
def _make_odd(value: int) -> int:
    value = int(value)
    value = max(value, 3)
    return value + 1 if value % 2 == 0 else value


def process_flux_savgol(time_arr: np.ndarray, flux: np.ndarray) -> dict:
    """Median-normalise, fit a Savitzky-Golay baseline, divide it out.
    Applied independently to every FITS file (= one Kepler quarter/segment)."""
    t = np.asarray(time_arr, dtype=np.float64)
    f = np.asarray(flux, dtype=np.float64)

    valid = np.isfinite(t) & np.isfinite(f)
    if valid.sum() < MIN_VALID_POINTS:
        raise ValueError("Not enough valid points for processing.")
    t, f = t[valid], f[valid]

    if GLOBAL_NORMALIZATION:
        med = np.nanmedian(f)
        f_work = f / med if (np.isfinite(med) and med != 0) else f.copy()
    else:
        f_work = f.copy()

    window = _make_odd(SAVGOL_WINDOW_POINTS)
    if window >= len(f_work):                       # short segment: shrink window
        window = len(f_work) - 1
        if window % 2 == 0:
            window -= 1
    if window <= SAVGOL_POLYORDER:
        raise ValueError("Savitzky-Golay window must be greater than polynomial order.")

    baseline = savgol_filter(f_work, window_length=window, polyorder=SAVGOL_POLYORDER)
    processed = f_work / baseline

    ok = np.isfinite(t) & np.isfinite(f) & np.isfinite(baseline) & np.isfinite(processed)
    return {
        "time": t[ok],
        "flux_original": f[ok],
        "flux_processed": processed[ok],
        "baseline": baseline[ok],
    }


# =============================================================================
# STEP 4 - window index (notebook 3: get_windows_for_file)
# =============================================================================
def window_starts(time_arr: np.ndarray) -> list[int]:
    """Start indices of 1024-point windows (stride 512) that never cross a
    large time gap. Segments shorter than 1024 points are skipped (no padding).
    A tail window is added so the end of each segment is covered."""
    n = len(time_arr)
    if n < WINDOW_LENGTH:
        return []

    dt = np.diff(time_arr)
    finite_dt = dt[np.isfinite(dt) & (dt > 0)]
    if len(finite_dt):
        cadence = np.median(finite_dt)
        breakpoints = np.where(dt > GAP_FACTOR * cadence)[0] + 1
    else:
        breakpoints = np.array([], dtype=int)

    bounds = np.concatenate(([0], breakpoints, [n])).astype(int)

    starts: list[int] = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        if b - a < WINDOW_LENGTH:
            continue
        seg = list(range(a, b - WINDOW_LENGTH + 1, WINDOW_STRIDE))
        tail = b - WINDOW_LENGTH
        if seg[-1] != tail:
            seg.append(tail)
        starts.extend(seg)
    return starts


def select_windows(specs: list[dict]) -> list[dict]:
    """Deterministic spread across the whole KIC when there are too many windows
    (np.linspace over the ordered list, exactly as in training)."""
    if MAX_WINDOWS_PER_KIC is not None and len(specs) > MAX_WINDOWS_PER_KIC:
        idx = np.linspace(0, len(specs) - 1, MAX_WINDOWS_PER_KIC).round().astype(int)
        specs = [specs[i] for i in idx]
    return specs


# =============================================================================
# STEP 5 - bag construction (notebook 3: KICBagDataset._load_window)
# =============================================================================
@dataclass
class KICBag:
    kic: int
    bag: np.ndarray                         # float32, shape [W, 1024]  -> model input
    specs: list[dict]                       # per-window provenance (file, start, time range)
    n_files_downloaded: int = 0
    n_files_used: int = 0
    n_windows_before_cap: int = 0
    skipped_files: list[tuple[str, str]] = field(default_factory=list)
    preprocessing: list[dict] = field(default_factory=list)


def build_bag(kic: int, fits_paths: list[Path]) -> KICBag:
    """FITS files -> standardise -> savgol -> window index -> cap -> [W, 1024]."""
    fits_paths = sorted((Path(p) for p in fits_paths), key=lambda p: p.name)

    processed: dict[str, dict] = {}
    preprocessing: list[dict] = []
    all_specs: list[dict] = []
    skipped: list[tuple[str, str]] = []

    for path in fits_paths:
        try:
            lc = standardize_fits(path)                              # step 2
            proc = process_flux_savgol(lc.time, lc.flux)             # step 3
            starts = window_starts(proc["time"])                     # step 4
        except Exception as e:                                       # bad file: skip, like training
            skipped.append((path.name, repr(e)))
            log.warning("Skipping %s: %r", path.name, e)
            continue

        if not starts:
            continue

        flux_p = proc["flux_processed"].astype(np.float32)
        t = proc["time"]
        processed[path.name] = {"flux": flux_p}
        preprocessing.append({
            "file": path.name,
            "time": proc["time"].astype(float).tolist(),
            "original": proc["flux_original"].astype(float).tolist(),
            "processed": proc["flux_processed"].astype(float).tolist(),
        })
        for s in starts:
            all_specs.append({
                "file": path.name,
                "start": int(s),
                "length": WINDOW_LENGTH,
                "time_start": float(t[s]),
                "time_end": float(t[s + WINDOW_LENGTH - 1]),
            })

    n_before_cap = len(all_specs)
    if n_before_cap == 0:
        raise NoUsableDataError(
            f"KIC {kic}: no usable light-curve windows "
            f"(need >= {WINDOW_LENGTH} contiguous points)."
        )

    specs = select_windows(all_specs)                                # cap to 32

    windows = []
    for sp in specs:
        x = processed[sp["file"]]["flux"][sp["start"]: sp["start"] + sp["length"]]
        x = x - 1.0                                                  # centre around zero
        x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        if len(x) != WINDOW_LENGTH:
            raise RuntimeError(f"Unexpected window length {len(x)} in {sp['file']}")
        windows.append(x.astype(np.float32, copy=False))

    return KICBag(
        kic=kic,
        bag=np.stack(windows, axis=0),
        specs=specs,
        n_files_downloaded=len(fits_paths),
        n_files_used=len({sp["file"] for sp in specs}),
        n_windows_before_cap=n_before_cap,
        skipped_files=skipped,
        preprocessing=preprocessing,
    )


def prepare_kic(
    kic_input,
    work_dir: Optional[Path] = None,
    include_short_cadence: bool = INCLUDE_SHORT_CADENCE_DEFAULT,
    keep_fits: bool = False,
) -> KICBag:
    """User-facing entry: 'KIC 9850966' -> KICBag ready for the model."""
    kic = parse_kic(kic_input)
    tmp_created = work_dir is None
    work_dir = Path(tempfile.mkdtemp(prefix=f"kic_{kic}_")) if tmp_created else Path(work_dir)
    try:
        paths = download_kepler_fits(kic, work_dir, include_short_cadence)
        return build_bag(kic, paths)
    finally:
        if tmp_created and not keep_fits:
            shutil.rmtree(work_dir, ignore_errors=True)


# =============================================================================
# STEP 6 - model glue (model class itself stays in your training code)
# =============================================================================
def load_final_model(model_path, model_cls, device=None):
    """Load the payload saved by the training notebook ('final_model.pt').
    model_cls must be the AttentionMIL class (copied unchanged from training)."""
    import torch
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    payload = torch.load(model_path, map_location=device, weights_only=False)
    arch = payload["architecture"]
    model = model_cls(arch["dropout"], arch["window_chunk_size"]).to(device)
    model.load_state_dict(payload["model_state"])
    model.eval()
    return model, float(payload["validation_threshold"]), payload["data_config"]


def predict_bag(model, kic_bag: KICBag, threshold: float, top_k: int = 5) -> dict:
    """Run one KIC through the model. Returns probability, decision and the
    windows the attention head focused on (handy for the UI)."""
    import torch
    x = torch.from_numpy(kic_bag.bag)               # [W, 1024]; model moves it to its device
    model.eval()
    with torch.no_grad():
        logits, weights = model([x])                # model expects a LIST of bags
    prob = float(torch.sigmoid(logits)[0].item())
    attn = weights[0].detach().cpu().numpy()

    top = np.argsort(attn)[::-1][:top_k]
    return {
        "kic": kic_bag.kic,
        "probability": prob,
        "threshold": threshold,
        "is_candidate": prob >= threshold,
        "n_windows": int(len(attn)),
        "n_windows_before_cap": kic_bag.n_windows_before_cap,
        "n_files_used": kic_bag.n_files_used,
        "attention_weights": attn.tolist(),
        "window_specs": kic_bag.specs,
        "preprocessing": kic_bag.preprocessing,
        "top_windows": [
            {**{k: kic_bag.specs[i][k] for k in ("file", "start", "time_start", "time_end")},
             "attention": float(attn[i])}
            for i in top
        ],
    }


# =============================================================================
# CLI: python kepler_pipeline.py 9850966  [--no-short-cadence]
# (only builds the bag; useful for checking the preprocessing end to end)
# =============================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("kic")
    ap.add_argument("--no-short-cadence", action="store_true")
    ap.add_argument("--work-dir", default=None)
    args = ap.parse_args()

    result = prepare_kic(
        args.kic,
        work_dir=args.work_dir,
        include_short_cadence=not args.no_short_cadence,
    )
    print(f"KIC {result.kic}: bag shape {result.bag.shape}, "
          f"{result.n_windows_before_cap} windows before cap, "
          f"{result.n_files_used}/{result.n_files_downloaded} files used, "
          f"{len(result.skipped_files)} skipped")
