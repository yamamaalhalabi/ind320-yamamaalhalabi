import numpy as np
import pandas as pd
import requests
import streamlit as st
import matplotlib.pyplot as plt
from scipy.signal import spectrogram
from statsmodels.tsa.seasonal import STL

st.set_page_config(page_title="STL and spectrogram", page_icon="📈", layout="wide")
st.title("Reservoir filling: STL and spectrogram")

BASE = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk"


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
    """STL decomposition; returns the figure."""
    result = STL(series, period=period, seasonal=seasonal,
                 trend=trend, robust=robust).fit()
    fig = result.plot()
    fig.set_size_inches(10, 8)
    fig.suptitle(f"STL (seasonal={seasonal}, trend={trend}, robust={robust})", y=1.01)
    plt.tight_layout()
    return fig


def make_spectrogram(series, window_length=156, overlap=120, max_freq=6):
    """Spectrogram of a weekly series; frequencies in cycles per year."""
    values = series.to_numpy() - series.mean()
    freqs, times, power = spectrogram(values, fs=52, window="hann",
                                      nperseg=window_length, noverlap=overlap)
    dates = series.index[0] + pd.to_timedelta(times * 365.25, unit="D")
    fig, ax = plt.subplots(figsize=(10, 5))
    mesh = ax.pcolormesh(dates, freqs, 10 * np.log10(power + 1e-12), shading="auto")
    ax.set_ylim(0, max_freq)
    ax.set_xlabel("Date")
    ax.set_ylabel("Frequency (cycles per year)")
    ax.set_title(f"Spectrogram (window={window_length}, overlap={overlap} weeks)")
    fig.colorbar(mesh, ax=ax, label="Power (dB)")
    plt.tight_layout()
    return fig


data = load_all()

# --- Area selector (local to this page) -----------------------------------
omr_type = st.radio("Area type", ["NO", "EL", "VASS"], horizontal=True)
numbers = sorted(data.loc[data["omrType"] == omr_type, "omrnr"].unique())
omr_nr = st.selectbox("Area number", numbers)
series = fill_series(data, omr_type, int(omr_nr))

tab_stl, tab_spec = st.tabs(["STL", "Spectrogram"])

with tab_stl:
    c1, c2, c3 = st.columns(3)
    seasonal = c1.slider("Seasonal smoother", 7, 53, 13, step=2)
    trend = c2.slider("Trend smoother", 53, 201, 105, step=2)
    robust = c3.checkbox("Robust", value=True)
    st.pyplot(stl_decomposition(series, seasonal=seasonal, trend=trend, robust=robust))

with tab_spec:
    c1, c2 = st.columns(2)
    window = c1.slider("Window length (weeks)", 26, 312, 156, step=26)
    overlap = c2.slider("Window overlap (weeks)", 0, window - 1, int(window * 0.75))
    st.pyplot(make_spectrogram(series, window_length=window, overlap=overlap))