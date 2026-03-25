import streamlit as st
import matplotlib.pyplot as plt
import traceback
import shap
from fetch_tpf import run_analysis_pipeline

st.set_page_config(page_title="AstroSense", layout="wide")
st.title("🔭 AstroSense: End-to-End Exoplanet Pipeline")

targets = {
    "Kepler-8 (Hot Jupiter)": ("Kepler-8", 4),
    "Kepler-1 (TrES-2b)": ("Kepler-1", 4),
    "Kepler-2 (HAT-P-7b)": ("Kepler-2", 4)
}

selected_star = st.selectbox("Select a Target Star System", list(targets.keys()))

if st.button("Initiate AstroSense Pipeline"):
    star_id, quarter = targets[selected_star]
    
    try:
        with st.spinner("Processing Data through NASA Pipeline..."):
            res = run_analysis_pipeline(star_id, quarter)

        st.success("Analysis Complete!")
        
        # --- ROW 1: LIGHTCURVE DATA ---
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("1. Raw Time-Series Flux")
            fig1, ax1 = plt.subplots(figsize=(8, 4))
            res["raw_lc"].plot(ax=ax1, color='gray')
            st.pyplot(fig1)

            st.subheader("2. Detrended Signal")
            fig2, ax2 = plt.subplots(figsize=(8, 4))
            res["clean_lc"].plot(ax=ax2, color='blue')
            st.pyplot(fig2)

        with col2:
            st.subheader(f"3. BLS (Orbit: {res['period'].value:.2f} days)")
            fig3, ax3 = plt.subplots(figsize=(8, 4))
            res["bls"].plot(ax=ax3, color='black')
            st.pyplot(fig3)

            st.subheader("4. Phase-Folded Transit")
            fig4, ax4 = plt.subplots(figsize=(8, 4))
            res["folded_lc"].scatter(ax=ax4, color='black', s=5)
            ax4.set_xlim(-0.2, 0.2)
            st.pyplot(fig4)

        # --- ROW 2: ML METRICS ---
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Model Verdict", "Confirmed Exoplanet" if res["xgb_pred"] > 50 else "False Positive")
        m2.metric("Ensemble Confidence", f"{res['xgb_pred']:.1f}%")
        m3.metric("Orbital Period", f"{res['period'].value:.2f} Days")

        # --- ROW 3: XAI DASHBOARDS ---
        st.subheader("5. Explainable AI (XAI) Dashboard")
        xai_col1, xai_col2 = st.columns(2)

        with xai_col1:
            st.markdown("**CNN Saliency Map (Spatial Patterns)**")
            fig5, ax5 = plt.subplots(figsize=(8, 5))
            ax5.plot(res["phase_new"], res["cnn_input"].flatten(), color='gray', alpha=0.5)
            scatter = ax5.scatter(res["phase_new"], res["cnn_input"].flatten(), c=res["saliency"], cmap='hot', s=40)
            ax5.set_xlim(-0.2, 0.2)
            plt.colorbar(scatter, ax=ax5, label="Neural Importance")
            st.pyplot(fig5)

        with xai_col2:
            st.markdown("**SHAP Waterfall (Feature Importance)**")
            fig6 = plt.figure(figsize=(8, 5))
            shap.plots.waterfall(res["shap_values"][0], show=False)
            st.pyplot(fig6)

    except Exception as e:
        st.error("🚨 Pipeline Error.")
        st.code(traceback.format_exc())

# import streamlit as st
# import matplotlib.pyplot as plt
# from fetch_tpf import fetch_tpf

# st.title("🔭 Fetch Space Telescope FITS")

# # 🔹 Input: Only ID (number)
# star_id = st.text_input(
#     "Enter Star ID (number only)",
#     placeholder="e.g., 11446443 (Kepler) or 25155310 (TESS)"
# )

# # 🔹 Dropdown: Mission
# mission = st.selectbox("Select Mission", ["Kepler", "TESS"])

# if st.button("Fetch Data"):

#     if not star_id:
#         st.warning("Please enter a Star ID")
#     else:
#         try:
#             with st.spinner("Fetching data from NASA..."):

#                 # Call backend function
#                 tpf = fetch_tpf(star_id, mission)

#             st.success(f"{mission} data downloaded successfully!")

#             # Convert to lightcurve
#             lc = tpf.to_lightcurve()

#             # Plot lightcurve
#             fig, ax = plt.subplots()
#             lc.plot(ax=ax)
#             st.pyplot(fig)

#         except Exception as e:
#             st.error(str(e))