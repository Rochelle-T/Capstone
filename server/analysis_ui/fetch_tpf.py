
import lightkurve as lk
import streamlit as st

@st.cache_resource
def fetch_tpf(star_id, mission):

    # Clean input
    star_id = star_id.strip()

    # Handle mission-specific formatting
    if mission == "Kepler":
        # Always convert to KIC format
        query_id = f"KIC {star_id}"
        search = lk.search_targetpixelfile(query_id, mission="Kepler")

    else:  # TESS
        # Always convert to TIC format
        query_id = f"TIC {star_id}"
        search = lk.search_targetpixelfile(query_id, mission="TESS")

        # ✅ take only first result (fastest)
        search = search[:1]

    # Check if data exists
    if len(search) == 0:
        raise Exception(f"No data found for {mission} ID: {star_id}")

    # Download first available file
    tpf = search[0].download()
    return tpf