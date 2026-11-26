import streamlit as st

# Page settings must be the first Streamlit call; the pages below do not set their own
st.set_page_config(page_title="IND320", page_icon=":material/bolt:", layout="wide")

# Shared selections used by several pages (updated by the map and the selectors)
st.session_state.setdefault("area", "NO 3")      # selected price area
st.session_state.setdefault("year", 2024)        # selected year

# Sidebar menu with groups (Explore, Analysis, ...). More pages are added below as they are built.
pages = {
    "Overview": [
        st.Page("pages/1_Home.py", title="Home", icon=":material/home:", default=True),
    ],
    "Explore": [
        st.Page("pages/7_Map.py", title="Map", icon=":material/map:"),
        st.Page("pages/2_Table.py", title="Reservoir table", icon=":material/table_chart:"),
        st.Page("pages/3_Plot.py", title="Reservoir plot", icon=":material/show_chart:"),
        st.Page("pages/4_ENTSOE.py", title="ENTSO-E flows", icon=":material/bolt:"),
    ],
    "Analysis": [
        st.Page("pages/5_STL_Spectrogram.py", title="STL & spectrogram", icon=":material/graphic_eq:"),
        st.Page("pages/6_SPC_LOF.py", title="Weather anomalies", icon=":material/thunderstorm:"),
        st.Page("pages/8_Correlation.py", title="Sliding window correlation", icon=":material/query_stats:"),
    ],
    "Forecast": [
        st.Page("pages/10_Forecast.py", title="River forecast", icon=":material/trending_up:"),
    ],
    "Info": [
        st.Page("pages/9_About.py", title="About", icon=":material/info:"),
    ],
}

navigation = st.navigation(pages)
navigation.run()