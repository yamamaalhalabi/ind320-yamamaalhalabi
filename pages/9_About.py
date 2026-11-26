import streamlit as st

st.title("About")

st.write(
    "This app is part of the compulsory project in IND320 (Data to decision) at NMBU, "
    "by Yamama Alhalabi. It started as a dashboard of weekly Norwegian reservoir "
    "fill-level data (reservoirs.csv) and has grown with new data sources and analyses."
)

st.subheader("Pages")
st.markdown(
    "- **Table** and **Plot**: weekly reservoir fill-level data and plots (part 1)\n"
    "- **ENTSO-E**: power flows to and from Norway, read from MongoDB (part 2)\n"
    "- **STL Spectrogram**: STL decomposition and spectrogram of the reservoir "
    "filling degree from NVE (part 3)\n"
    "- **SPC LOF**: hourly ERA5 weather from open-meteo for an electricity price "
    "area (EL 1-5 = NO1-NO5), with SPC outliers and LOF anomalies (part 3)"
)

st.subheader("Data sources")
st.markdown(
    "- NVE magasinstatistikk (reservoir filling degree)\n"
    "- NVE map services (electricity price areas and NVE regions)\n"
    "- open-meteo ERA5 archive (weather)\n"
    "- ENTSO-E (power flows)"
)

st.subheader("Links")
st.markdown("- GitHub: https://github.com/yamamaalhalabi/ind320-yamamaalhalabi")