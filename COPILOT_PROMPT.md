# Prompt for GitHub Copilot (paste into Copilot Chat, with `kepler_pipeline.py` open / attached)

---

## Context
I'm building a web app for exoplanet transit vetting. The user types a **KIC number** (e.g. `9850966`). The backend must automatically download the Kepler light-curve FITS files from MAST, preprocess them **exactly** as in my training pipeline, and feed them to my trained Keras 1D-CNN (`best_exoplanet_cnn.keras`, input shape `(N, 1024, 1)`, sigmoid output = planet probability).

I already have `kepler_pipeline.py`, which implements the whole chain:
`parse_kic -> download_fits (astroquery/MAST) -> extract_lightcurve (FITS->arrays/NPZ) -> savgol_detrend -> stitch_segments -> robust_scale_segments -> make_windows -> predict_kic`.

## Your task
Integrate `kepler_pipeline.py` into my application as a clean service layer. Do the following:

1. Create a thin `services/inference_service.py` that exposes one function, `analyze_kic(kic_input: str) -> dict`, which calls `predict_kic(...)` from `kepler_pipeline.py`. Load the model **once at startup** (module-level singleton or app lifespan event), not per request.
2. Expose it through my existing API layer (adapt to whatever framework is in this repo: FastAPI/Flask/Streamlit/Gradio):
   - `POST /analyze {"kic": "9850966"}` returns JSON: `kic`, `n_windows`, `mean_probability`, `max_probability`, `pred_mean`, `pred_max`, `top_window` (time range + probability), `skipped_files`.
   - Validate input with `parse_kic`; return HTTP 400 for unparseable KICs, 404 when MAST has no Kepler data (`LookupError`), 422 when no segment is long enough for a 1024-point window (`RuntimeError`), and 502 for MAST/network failures.
3. Because the MAST download can take 30 seconds to several minutes, run it as a **background job** (thread pool or task queue) with a status endpoint (`GET /jobs/{id}` → `queued | downloading | processing | predicting | done | error`), or at minimum run it off the event loop. Show progress in the UI.
4. Keep the on-disk cache (`PipelineConfig.cache_dir`). Repeated requests for the same KIC must not re-download. Add a lock per KIC so two simultaneous requests do not download the same files twice.
5. In the UI, after results: show the verdict, mean and max probability, and plot the stitched detrended light curve (`PreparedKIC.stitched`: `time`, `flux`, `segment_id`) with the top-scoring window highlighted (`top_window.t_start` / `t_end`). Return `window_probabilities` + `window_meta` so I can plot probability vs. time.
6. Add `requirements.txt` entries: `astropy`, `astroquery`, `numpy`, `scipy`, `tensorflow` (or `tensorflow-cpu`), plus whatever the web framework needs.
7. Write pytest tests in `tests/test_pipeline.py` that **do not touch the network**: build synthetic light curves (sinusoid + noise + box-shaped transits, NaNs, two segments with a gap) and test `savgol_detrend`, `stitch_segments`, `robust_scale_segments`, and `make_windows` (shapes `(N,1024,1)`, dtype float32, values within [-10, 10], no window crosses a segment boundary, segments shorter than 1024 produce no windows). Mock `download_fits` for an end-to-end `prepare_kic` test.

## Hard constraints (do NOT violate)
- **Do not modify any preprocessing constant or algorithm** in `kepler_pipeline.py`: window 1024, stride 512, Savitzky-Golay window 101 / polyorder 2, flux/median normalization, per-segment median/MAD (×1.4826, std fallback) scaling, clip ±10, PDCSAP_FLUX priority, no quality-flag masking, long cadence only. They must stay identical to training, otherwise the model's predictions are invalid. If you think one should change, tell me instead of changing it.
- Windows must never cross a segment boundary.
- Do not call the model on an empty array; raise a clear error.
- Don't load TensorFlow at import time of the API module if it slows startup unnecessarily. Use the lazy `load_model` already in the file, and warm it up in the startup hook.
- All errors must be reported to the user in plain language, never as a raw traceback.

## Known open point
`stitch_segments()` assumes one segment per Kepler quarter file, with Savitzky-Golay applied per file. If my original training stitching used a different segment definition (for example splitting on time gaps), I will edit only that function. Keep it isolated so that's easy.

## Deliverables
List the files you created or changed, then show how to run the app locally and how to test with KIC `9850966`.
