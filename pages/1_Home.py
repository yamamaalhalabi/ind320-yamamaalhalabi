import streamlit as st

st.title("IND320 - Data to decision")
st.write(
    "Explore Norwegian reservoir filling together with weather and power flow data, "
    "and forecast the reservoir fill. Start on the map and pick an area."
)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Explore")
    st.markdown(
        """
- **Map**: areas coloured by fill or weather
- **Reservoir data**: weekly plot and overview
- **ENTSO-E flows**: cross-border power flows
"""
    )
with col2:
    st.subheader("Analysis and forecast")
    st.markdown(
        """
- **STL & spectrogram**: seasonality in the fill
- **Weather anomalies**: SPC and LOF outliers
- **Sliding window correlation**: weather vs reservoir fill
- **River forecast**: online forecast with weather
"""
    )

st.info(
    "The area, year, weather property and time period you choose on the map "
    "are shared between the pages."
)