import lightkurve as lk
import numpy as np
import pandas as pd
import tensorflow as tf
from scipy.interpolate import interp1d
import xgboost as xgb
import shap

def run_analysis_pipeline(star_id, quarter=4):
    # --- Module A: Fetching ---
    search_result = lk.search_lightcurve(star_id, author='Kepler', quarter=quarter)
    if len(search_result) == 0:
        raise Exception(f"No Kepler data found for {star_id} in Quarter {quarter}")
    
    lc = search_result.download()
    
    # --- Module B: Scrubbing ---
    clean_lc = lc.flatten(window_length=401).remove_nans().remove_outliers()
    
    # --- Module C: BLS Periodogram ---
    bls = clean_lc.to_periodogram(method='bls', period=np.linspace(1, 10, 1000))
    planet_period = bls.period_at_max_power
    planet_t0 = bls.transit_time_at_max_power
    
    # --- Module D: Phase-folding ---
    folded_lc = clean_lc.fold(period=planet_period, epoch_time=planet_t0)

    # --- Module E & F: ML & XAI Preparation ---
    flux_raw = folded_lc.flux.value
    phase_raw = folded_lc.time.value

    # Handle masked arrays/NaNs
    flux_array = np.array(flux_raw, dtype=np.float64)
    median_val = np.nanmedian(flux_array)
    flux_array = np.nan_to_num(flux_array, nan=median_val if not np.isnan(median_val) else 0.0)

    # Sort and Interpolate for CNN Input
    sort_idx = np.argsort(phase_raw)
    phase_sorted = phase_raw[sort_idx]
    flux_sorted = flux_array[sort_idx]
    phase_new = np.linspace(phase_sorted.min(), phase_sorted.max(), 1000)
    cnn_input = interp1d(phase_sorted, flux_sorted, kind='linear')(phase_new).reshape(1, 1000, 1)

    # Simple CNN for Saliency
    model = tf.keras.Sequential([
        tf.keras.layers.Conv1D(16, 3, activation='relu', input_shape=(1000, 1)),
        tf.keras.layers.MaxPooling1D(2),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])
    
    # Gradient calculation for Saliency Map
    input_tensor = tf.convert_to_tensor(cnn_input, dtype=tf.float32)
    with tf.GradientTape() as tape:
        tape.watch(input_tensor)
        pred = model(input_tensor)
    grads = tape.gradient(pred, input_tensor)
    saliency = tf.abs(grads).numpy().flatten()

    # XGBoost Logic
    current_features = pd.DataFrame({
        'Transit_Depth': [bls.depth_at_max_power.value],
        'Orbital_Period': [planet_period.value],
        'Transit_Duration': [bls.duration_at_max_power.value * 24]
    })
    
    # Dummy trainer for UI components (Replace with loaded model in production)
    X_dummy = pd.DataFrame({
        'Transit_Depth': np.random.uniform(0.001, 0.05, 100),
        'Orbital_Period': np.random.uniform(1, 10, 100),
        'Transit_Duration': np.random.uniform(1, 6, 100)
    })
    y_dummy = np.random.randint(0, 2, 100)
    xgb_model = xgb.XGBClassifier(eval_metric='logloss').fit(X_dummy, y_dummy)
    
    explainer = shap.TreeExplainer(xgb_model)
    shap_values = explainer(current_features)
    xgb_pred = xgb_model.predict_proba(current_features)[0][1] * 100

    return {
        "raw_lc": lc,
        "clean_lc": clean_lc,
        "bls": bls,
        "folded_lc": folded_lc,
        "period": planet_period,
        "phase_new": phase_new,
        "cnn_input": cnn_input,
        "saliency": saliency,
        "shap_values": shap_values,
        "xgb_pred": xgb_pred
    }

    
# import lightkurve as lk
# import streamlit as st

# @st.cache_resource
# def fetch_tpf(star_id, mission):

#     # Clean input
#     star_id = star_id.strip()

#     # Handle mission-specific formatting
#     if mission == "Kepler":
#         # Always convert to KIC format
#         query_id = f"KIC {star_id}"
#         search = lk.search_targetpixelfile(query_id, mission="Kepler")

#     else:  # TESS
#         # Always convert to TIC format
#         query_id = f"TIC {star_id}"
#         search = lk.search_targetpixelfile(query_id, mission="TESS")

#         # ✅ take only first result (fastest)
#         search = search[:1]

#     # Check if data exists
#     if len(search) == 0:
#         raise Exception(f"No data found for {mission} ID: {star_id}")

#     # Download first available file
#     tpf = search[0].download()
#     return tpf