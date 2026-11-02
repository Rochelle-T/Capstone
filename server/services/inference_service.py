"""KIC inference service backed by the training-compatible Kepler pipeline."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from typing import Dict
from uuid import uuid4

import sys
import logging
import importlib.util

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from kepler_pipeline import PipelineConfig, load_model, parse_kic, predict_kic

log = logging.getLogger("astrosense.inference")
MODEL_PATH = PROJECT_ROOT / "best_exoplanet_cnn.keras"
MODEL2_PATH = PROJECT_ROOT / "cnn_savgol_gap2p5_expB_seed456.pt"
MODEL2_PIPELINE_PATH = PROJECT_ROOT / "kepler_pipeline 2.py"
CONFIG = PipelineConfig(cache_dir=PROJECT_ROOT / "kepler_cache")
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="kic-inference")
_jobs: Dict[str, dict] = {}
_jobs_lock = Lock()
_kic_locks: Dict[int, Lock] = {}
_model_error: str | None = None
_model2_error: str | None = None
_model2 = None
_model2_threshold = None
_model2_pipeline = None


def _load_model2_pipeline():
    global _model2_pipeline
    if _model2_pipeline is None:
        spec = importlib.util.spec_from_file_location(
            "kepler_pipeline_model2", MODEL2_PIPELINE_PATH
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load Model 2 pipeline from {MODEL2_PIPELINE_PATH}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _model2_pipeline = module
    return _model2_pipeline


def _lock_for_kic(kic: int) -> Lock:
    with _jobs_lock:
        return _kic_locks.setdefault(kic, Lock())


def analyze_kic(kic_input: str) -> dict:
    """Run one KIC inference while preventing duplicate downloads per KIC."""
    if _model_error or _model2_error:
        raise RuntimeError(_model_error or _model2_error)
    kic = parse_kic(kic_input)
    with _lock_for_kic(kic):
        pipeline2 = _load_model2_pipeline()
        model2_files = pipeline2.download_kepler_fits(
            kic,
            CONFIG.cache_dir / "raw" / f"KIC_{kic}",
            include_short_cadence=True,
        )
        model1_result = predict_kic(kic, MODEL_PATH, CONFIG)
        bag = pipeline2.build_bag(kic, model2_files)
        model2_result = pipeline2.predict_bag(
            _model2, bag, _model2_threshold
        )
        model1_result.pop("_fits_files", None)
        model1_result["models"] = {
            "stage_1_cnn": model1_result["model"],
            "attention_mil": {
                "name": "AttentionMIL CNN",
                "version": MODEL2_PATH.name,
                "loading": "PyTorch",
                **model2_result,
            },
        }
        return model1_result


def warm_model() -> None:
    """Load the classifier once during application startup."""
    global _model_error, _model2_error, _model2, _model2_threshold
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
    try:
        from model_def import AttentionMIL, DEVICE

        pipeline2 = _load_model2_pipeline()
        _model2, _model2_threshold, model2_config = pipeline2.load_final_model(
            MODEL2_PATH, AttentionMIL, device=DEVICE
        )
        if model2_config.get("method") != "savgol":
            raise RuntimeError(
                "Model 2 checkpoint preprocessing is not 'savgol'; "
                "the configured pipeline cannot safely use it."
            )
        _model2_error = None
    except ModuleNotFoundError as exc:
        _model2_error = (
            "The second inference model is unavailable because PyTorch is not installed. "
            "Run: pip install -r requirements.txt"
        )
        log.error("%s Missing module: %s", _model2_error, exc.name)
    except Exception as exc:
        _model2_error = f"The second inference model could not be loaded: {exc}"
        log.exception("Second model startup failed")


def get_model_status() -> dict:
    """Return a safe, user-facing view of model availability."""
    return {
        "available": _model_error is None and _model2_error is None,
        "models": {
            "stage_1_cnn": {"available": _model_error is None, "path": str(MODEL_PATH), "error": _model_error},
            "attention_mil": {"available": _model2_error is None, "path": str(MODEL2_PATH), "error": _model2_error},
        },
        "model_path": str(MODEL_PATH),
        "error": _model_error or _model2_error,
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
