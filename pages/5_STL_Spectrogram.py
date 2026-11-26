import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots
from scipy.signal import spectrogram
from statsmodels.tsa.seasonal import STL

st.title("Reservoir filling: STL and spectrogram")

BASE = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk"
OMR_TYPE = {"Country": "NO", "Price area": "EL", "Water area": "VASS"}

st.session_state.setdefault("map_type", "Price area")
st.session_state.setdefault("map_area", "NO 3")


@st.cache_data(ttl=3600)
def load_all():
    # One download for all areas; cached so changing a slider does not refetch
    resp = requests.get(f"{BASE}/HentOffentligData", timeout=30)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    df["dato_Id"] = pd.to_datetime(df["dato_Id"])
    return df


def fill_series(df, omr_type, omr_nr):
    """Weekly filling degree for one area as a regular weekly series."""
    sub = df[(df["omrType"] == omr_type) & (df["omrnr"] == omr_nr)]
    series = sub.drop_duplicates("dato_Id").sort_values("dato_Id")
    series = series.set_index("dato_Id")["fyllingsgrad"].rename("fill_ratio")
    return series.asfreq("W-SUN").interpolate()


def stl_decomposition(series, period=52, seasonal=13, trend=105, robust=True):
    """STL decomposition shown as four stacked Plotly panels."""
    result = STL(series, period=period, seasonal=seasonal,
                 trend=trend, robust=robust).fit()
    parts = [("Observed", series), ("Trend", result.trend),
             ("Seasonal", result.seasonal), ("Residual", result.resid)]
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04,
                        subplot_titles=[name for name, _ in parts])
    for i, (name, values) in enumerate(parts, start=1):
        mode = "markers" if name == "Residual" else "lines"
        fig.add_trace(go.Scatter(x=values.index, y=values, mode=mode, name=name,
                                 line=dict(color="#0F766E", width=1.2),
                                 marker=dict(color="#0F766E", size=3)),
                      row=i, col=1)
    fig.update_layout(height=750, showlegend=False, margin=dict(t=40),
                      title=f"STL (seasonal={seasonal}, trend={trend}, robust={robust})")
    return fig


def make_spectrogram(series, window_length=156, overlap=120, max_freq=6):
    """Spectrogram of a weekly series; frequencies in cycles per year."""
    values = series.to_numpy() - series.mean()
    freqs, times, power = spectrogram(values, fs=52, window="hann",
                                      nperseg=window_length, noverlap=overlap)
    dates = series.index[0] + pd.to_timedelta(times * 365.25, unit="D")
    keep = freqs <= max_freq
    fig = go.Figure(go.Heatmap(
        x=dates, y=freqs[keep], z=10 * np.log10(power[keep] + 1e-12),
        colorscale="Viridis", colorbar=dict(title="Power (dB)"),
    ))
    fig.update_layout(
        title=f"Spectrogram (window={window_length}, overlap={overlap} weeks)",
        xaxis_title="Date", yaxis_title="Frequency (cycles per year)", height=520,
    )
    return fig


try:
    data = load_all()
except Exception as exc:
    st.error(f"Could not download reservoir data: {exc}")
    st.stop()

# --- Area comes from the map page (shared via session state) ---------------
area_type = st.session_state["map_type"]
area = st.session_state["map_area"]
omr_nr = 0 if area == "NO" else int(area.split()[1])
st.info(f"Data source: **{area}** ({area_type.lower()}). Change it on the Map page.")
series = fill_series(data, OMR_TYPE[area_type], omr_nr)

tab_stl, tab_spec = st.tabs(["STL", "Spectrogram"])

with tab_stl:
    c1, c2, c3 = st.columns(3)
    seasonal = c1.slider("Seasonal smoother", 7, 53, 13, step=2)
    trend = c2.slider("Trend smoother", 53, 201, 105, step=2)
    robust = c3.checkbox("Robust", value=True)
    st.plotly_chart(stl_decomposition(series, seasonal=seasonal, trend=trend, robust=robust),
                    use_container_width=True)

with tab_spec:
    c1, c2 = st.columns(2)
    window = c1.slider("Window length (weeks)", 26, 312, 156, step=26)
    overlap = c2.slider("Window overlap (weeks)", 0, window - 1, int(window * 0.75))
    st.plotly_chart(make_spectrogram(series, window_length=window, overlap=overlap),
                    use_container_width=True)