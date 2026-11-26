import streamlit as st

st.title("About")

st.write(
    "This app is the compulsory project in IND320 (Data to decision) at NMBU. "
    "It explores Norwegian reservoir filling, hydropower-related weather and "
    "power flows, and forecasts the reservoir fill."
)

st.subheader("Pages")
st.markdown(
    """
- **Map**: price areas, water areas or the whole country, coloured by reservoir fill or a weather property. A click selects an area for all other pages.
- **Reservoir data**: weekly reservoir statistics as a plot and a first-month overview.
- **ENTSO-E flows**: cross-border power flows stored in MongoDB.
- **STL & spectrogram**: seasonal decomposition and frequency content of the fill series.
- **Weather anomalies**: SPC outliers (seasonally adjusted variation) and LOF anomalies for a chosen weather property.
- **Sliding window correlation**: correlation between a weather property and the reservoir fill, with selectable lag and window length.
- **River forecast**: online SNARIMAX forecast with optional weather as exogenous variables and an animated forecast plot.
"""
)

st.subheader("Data sources")
st.markdown(
    """
- NVE Magasinstatistikk API (weekly reservoir fill, price areas, water areas and country)
- NVE map services (price area outlines, catchment areas)
- open-meteo ERA5 archive (weather)
- ENTSO-E (power flows, stored in MongoDB Atlas)
- Norges Bank (exchange rates, used in the notebook)
"""
)

st.subheader("Notes")
st.markdown(
    """
- Time is handled in UTC. Weekly and daily sources are joined on dates.
- The four water areas (VASS 1-4) are built from catchment polygons using the NVE area descriptions. The border inside Rogaland is an assumption.
- Weather per area uses one representative point per area, which approximates an area average.
- Forecasts use the mean of the same week of the year as future weather.
"""
)

st.subheader("Links")
st.markdown("[GitHub repository](https://github.com/yamamaalhalabi/ind320-yamamaalhalabi)")