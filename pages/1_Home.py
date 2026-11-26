import streamlit as st

st.title("IND320 - Data to decision")
st.write(
    "An app for Norwegian reservoir filling, electricity and weather data. "
    "Use the menu on the left. The pages are grouped by the type of task."
)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Explore")
    st.markdown(
        "- Reservoir table and plot\n"
        "- ENTSO-E power flows"
    )
with col2:
    st.subheader("Analysis")
    st.markdown(
        "- STL decomposition and spectrogram of the filling degree\n"
        "- Weather anomalies: SPC outliers and LOF"
    )

st.info("Selections such as the area and the year are shared between the pages.")