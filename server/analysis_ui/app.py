import streamlit as st
import matplotlib.pyplot as plt
from fetch_tpf import fetch_tpf

st.title("🔭 Fetch Space Telescope FITS")

# 🔹 Input: Only ID (number)
star_id = st.text_input(
    "Enter Star ID (number only)",
    placeholder="e.g., 11446443 (Kepler) or 25155310 (TESS)"
)

# 🔹 Dropdown: Mission
mission = st.selectbox("Select Mission", ["Kepler", "TESS"])

if st.button("Fetch Data"):

    if not star_id:
        st.warning("Please enter a Star ID")
    else:
        try:
            with st.spinner("Fetching data from NASA..."):

                # Call backend function
                tpf = fetch_tpf(star_id, mission)

            st.success(f"{mission} data downloaded successfully!")

            # Convert to lightcurve
            lc = tpf.to_lightcurve()

            # Plot lightcurve
            fig, ax = plt.subplots()
            lc.plot(ax=ax)
            st.pyplot(fig)

        except Exception as e:
            st.error(str(e))