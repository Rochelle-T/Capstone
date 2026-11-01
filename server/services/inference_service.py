"""KIC inference service backed by the training-compatible Kepler pipeline."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from typing import Dict
from uuid import uuid4

import sys
import logging

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from kepler_pipeline import PipelineConfig, load_model, parse_kic, predict_kic

log = logging.getLogger("astrosense.inference")
MODEL_PATH = PROJECT_ROOT / "best_exoplanet_cnn.keras"
CONFIG = PipelineConfig(cache_dir=PROJECT_ROOT / "kepler_cache")
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="kic-inference")
_jobs: Dict[str, dict] = {}
_jobs_lock = Lock()
_kic_locks: Dict[int, Lock] = {}
_model_error: str | None = None


def _lock_for_kic(kic: int) -> Lock:
    with _jobs_lock:
        return _kic_locks.setdefault(kic, Lock())


def analyze_kic(kic_input: str) -> dict:
    """Run one KIC inference while preventing duplicate downloads per KIC."""
    if _model_error:
        raise RuntimeError(_model_error)
    kic = parse_kic(kic_input)
    with _lock_for_kic(kic):
        return predict_kic(kic, MODEL_PATH, CONFIG)


def warm_model() -> None:
    """Load the classifier once during application startup."""
    global _model_error
    try:
        load_model(MODEL_PATH)
        _model_error = None
    except ModuleNotFoundError as exc:
        _model_error = (
            "The inference model is unavailable because TensorFlow is not installed. "
            "Activate the server virtual environment and run: pip install -r requirements.txt"
        )
        log.error("%s Missing module: %s", _model_error, exc.name)
    except Exception as exc:
        _model_error = f"The inference model could not be loaded: {exc}"
        log.exception("Model startup failed")


def get_model_status() -> dict:
    """Return a safe, user-facing view of model availability."""
    return {
        "available": _model_error is None,
        "model_path": str(MODEL_PATH),
        "error": _model_error,
    }


def _run_job(job_id: str, kic_input: str) -> None:
    def update(status: str, error: str = ""):
        with _jobs_lock:
            _jobs[job_id]["status"] = status
            if error:
                _jobs[job_id]["error"] = error

    try:
        update("downloading")
        # The pipeline performs cached download and preprocessing in this worker.
        update("processing")
        result = analyze_kic(kic_input)
        update("predicting")
        with _jobs_lock:
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["result"] = result
    except Exception as exc:
        if isinstance(exc, LookupError):
            code = 404
        elif isinstance(exc, RuntimeError):
            code = 422
        elif isinstance(exc, (ConnectionError, TimeoutError)):
            code = 502
        else:
            code = 500
        with _jobs_lock:
            _jobs[job_id]["error_code"] = code
        update("error", str(exc))


def submit_kic(kic_input: str) -> str:
    """Validate and enqueue a KIC analysis, returning its job identifier."""
    parse_kic(kic_input)
    job_id = uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = {"id": job_id, "status": "queued"}
    _executor.submit(_run_job, job_id, kic_input)
    return job_id


def get_job(job_id: str) -> dict | None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None
