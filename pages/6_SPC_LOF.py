"""Streamlit page: SPC outliers and LOF anomalies for ERA5 weather data.

The weather follows the same area selection as the reservoir statistics:
electricity area EL n in the magasinstatistikk corresponds to price area NOn.
"""
import time
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import shapely
import streamlit as st
from scipy.fft import dct, idct
from sklearn.neighbors import LocalOutlierFactor

st.set_page_config(page_title="SPC and LOF", layout="wide")

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
PRICE_AREA_URL = ("https://kart.nve.no/enterprise/rest/services/Nettomraader/"
                  "MapServer/0/query?where=1%3D1&outFields=*&f=geojson")
WEATHER_VARS = ["temperature_2m", "precipitation"]
CACHE_DIR = Path("weather_cache")        # local cache of downloaded batches
CACHE_DIR.mkdir(exist_ok=True)


# ----------------------------------------------------------------------------
# Regions and sample points
# ----------------------------------------------------------------------------
@st.cache_data(ttl=24 * 3600, show_spinner="Loading price areas from NVE ...")
def load_price_areas():
    """Electricity price areas NO1-NO5 (NVE layer 'Budområder'), EPSG:25833."""
    return gpd.read_file(PRICE_AREA_URL).to_crs(epsg=25833)


@st.cache_data(show_spinner="Sampling points ...")
def sample_points(area_name, n_points=1000, seed=42):
    """Random points strictly inside one price area (rejection sampling).

    Points are drawn uniformly in the bounding box and kept if they fall inside
    the polygon. The seed makes the sample reproducible. Returns lat/lon lists.
    """
    areas = load_price_areas()
    polygon = areas.loc[areas["budomr"] == area_name, "geometry"].iloc[0]
    rng = np.random.default_rng(seed)
    minx, miny, maxx, maxy = polygon.bounds
    xs, ys = [], []
    while len(xs) < n_points:
        x = rng.uniform(minx, maxx, n_points * 2)
        y = rng.uniform(miny, maxy, n_points * 2)
        inside = shapely.contains_xy(polygon, x, y)
        xs.extend(x[inside])
        ys.extend(y[inside])
    pts = gpd.GeoSeries(gpd.points_from_xy(xs[:n_points], ys[:n_points]),
                        crs="EPSG:25833").to_crs(epsg=4326)
    return pts.y.round(4).tolist(), pts.x.round(4).tolist()


# ----------------------------------------------------------------------------
# Weather download
# ----------------------------------------------------------------------------
def download_weather(area_name, start, end, progress=None, batch_size=50):
    """Hourly ERA5 weather for one price area, averaged over 1000 sample points.

    The points are downloaded in batches because open-meteo limits the number of
    requests. Every batch is cached on disk, so an interrupted download (for
    example by the hourly limit) continues where it stopped.
    """
    tag = area_name.replace(" ", "")
    final_file = CACHE_DIR / f"{tag}_{start}_{end}.csv"
    if final_file.exists():
        return pd.read_csv(final_file, index_col=0, parse_dates=True)

    lats, lons = sample_points(area_name)
    n_points = len(lats)
    batch_sums = []
    for i in range(0, n_points, batch_size):
        batch_file = CACHE_DIR / f"{tag}_{start}_{end}_batch{i:04d}.csv"
        if batch_file.exists():
            batch_sums.append(pd.read_csv(batch_file, index_col=0, parse_dates=True))
        else:
            params = {
                "latitude": ",".join(map(str, lats[i:i + batch_size])),
                "longitude": ",".join(map(str, lons[i:i + batch_size])),
                "start_date": start, "end_date": end,
                "hourly": ",".join(WEATHER_VARS),
                "models": "era5", "timezone": "UTC",
            }
            for _ in range(5):
                resp = requests.get(ARCHIVE_URL, params=params, timeout=120)
                if resp.status_code == 200:
                    break
                try:
                    reason = resp.json().get("reason", "")
                except ValueError:
                    reason = resp.text[:200]
                if resp.status_code == 429 and "Minutely" in reason:
                    time.sleep(60)               # minute limit: wait and retry
                    continue
                raise RuntimeError(f"open-meteo refused (HTTP {resp.status_code}): "
                                   f"{reason}. Try again later; progress is saved.")
            else:
                raise RuntimeError("open-meteo kept refusing the request. "
                                   "Try again later; progress is saved.")
            data = resp.json()
            if isinstance(data, dict):
                data = [data]
            frames = [pd.DataFrame({v: loc["hourly"][v] for v in WEATHER_VARS},
                                   index=pd.to_datetime(loc["hourly"]["time"]))
                      for loc in data]
            batch_sum = pd.concat(frames).groupby(level=0).sum()
            batch_sum.to_csv(batch_file)
            batch_sums.append(batch_sum)
            time.sleep(1)
        if progress:
            progress(min(i + batch_size, n_points) / n_points)

    mean_df = sum(batch_sums) / n_points
    mean_df.index.name = "time"
    mean_df.to_csv(final_file)
    return mean_df


# ----------------------------------------------------------------------------
# SPC and LOF
# ----------------------------------------------------------------------------
def spc_outliers(weather, column, cutoff, n_std):
    """SPC outliers on the seasonally adjusted variation (SATV).

    A DCT high-pass filter sets the first `cutoff` coefficients to zero. The
    rest (SATV) is compared with robust limits: median +/- n_std * 1.4826 * MAD.
    Returns the figure and a summary dictionary.
    """
    series = weather[column]
    coeffs = dct(series.to_numpy(), type=2, norm="ortho")
    coeffs[:cutoff] = 0
    satv = idct(coeffs, type=2, norm="ortho")

    median = np.median(satv)
    robust_std = 1.4826 * np.median(np.abs(satv - median))
    upper = median + n_std * robust_std
    lower = median - n_std * robust_std
    is_outlier = (satv > upper) | (satv < lower)

    trend = series.to_numpy() - satv          # slow variation of the series
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(series.index, series, color="tab:blue", lw=0.8, label=column)
    ax.plot(series.index, trend + upper, color="tab:orange", ls="--", label="SPC limits")
    ax.plot(series.index, trend + lower, color="tab:orange", ls="--")
    ax.scatter(series.index[is_outlier], series[is_outlier], color="red",
               s=12, zorder=5, label="Outliers")
    ax.set_title(f"SPC outliers: {column} (cutoff={cutoff}, {n_std} robust std)")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel(column)
    ax.legend()
    fig.tight_layout()
    return fig, {"n_points": len(series), "n_outliers": int(is_outlier.sum()),
                 "upper_limit_satv": float(upper), "lower_limit_satv": float(lower)}


def lof_outliers(weather, column, contamination, n_neighbors):
    """Local Outlier Factor anomalies; `contamination` is the share of outliers."""
    series = weather[column]
    lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=contamination)
    is_outlier = lof.fit_predict(series.to_numpy().reshape(-1, 1)) == -1

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(series.index, series, color="tab:blue", lw=0.8, label=column)
    ax.scatter(series.index[is_outlier], series[is_outlier], color="red",
               s=12, zorder=5, label="Anomalies")
    ax.set_title(f"LOF anomalies: {column} (proportion of outliers = {contamination:.1%})")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel(column)
    ax.legend()
    fig.tight_layout()
    return fig, {"n_points": len(series), "n_outliers": int(is_outlier.sum()),
                 "contamination": contamination}


# ----------------------------------------------------------------------------
# Page
# ----------------------------------------------------------------------------
st.title("Weather: SPC outliers and LOF anomalies")
st.write(
    "Hourly ERA5 weather from open-meteo, averaged over 1000 random points inside "
    "an electricity price area. The area selection follows the reservoir pages: "
    "electricity area EL n corresponds to price area NOn."
)

col_area, col_year = st.columns(2)
el_number = col_area.selectbox("Electricity area (EL)", [1, 2, 3, 4, 5], index=2)
year = col_year.selectbox("Year", list(range(2024, 2018, -1)))
area_name = f"NO {el_number}"
start, end = f"{year}-01-01", f"{year}-12-31"
state_key = f"weather_{area_name}_{year}"

st.caption(
    "The first download of an area and year takes several minutes because open-meteo "
    "limits the number of requests. Downloaded data is cached."
)

if st.button(f"Load weather for {area_name}, {year}"):
    bar = st.progress(0.0, text="Downloading weather ...")
    try:
        st.session_state[state_key] = download_weather(
            area_name, start, end, progress=lambda p: bar.progress(p, text="Downloading weather ..."))
        bar.empty()
    except RuntimeError as err:
        bar.empty()
        st.error(str(err))

weather = st.session_state.get(state_key)
if weather is None:
    st.info("Select an area and a year, then press the button to load the weather.")
    st.stop()

tab_spc, tab_lof = st.tabs(["SPC outliers", "LOF anomalies"])

with tab_spc:
    st.subheader(f"SPC outliers, {area_name}, {year}")
    c1, c2, c3 = st.columns(3)
    spc_col = c1.selectbox("Variable", WEATHER_VARS, index=0, key="spc_col")
    cutoff = c2.slider("DCT cutoff (coefficients removed)", 1, 200, 20)
    n_std = c3.slider("Number of robust standard deviations", 1.0, 6.0, 3.0, 0.5)
    fig, summary = spc_outliers(weather, spc_col, cutoff, n_std)
    st.pyplot(fig)
    m1, m2, m3 = st.columns(3)
    m1.metric("Outliers", summary["n_outliers"])
    m2.metric("Upper limit (SATV)", f"{summary['upper_limit_satv']:.2f}")
    m3.metric("Lower limit (SATV)", f"{summary['lower_limit_satv']:.2f}")

with tab_lof:
    st.subheader(f"LOF anomalies, {area_name}, {year}")
    c1, c2, c3 = st.columns(3)
    lof_col = c1.selectbox("Variable", WEATHER_VARS, index=1, key="lof_col")
    contamination = c2.slider("Proportion of outliers (%)", 0.1, 10.0, 1.0, 0.1) / 100
    n_neighbors = c3.slider("Number of neighbours", 5, 100, 20)
    fig, summary = lof_outliers(weather, lof_col, contamination, n_neighbors)
    st.pyplot(fig)
    st.metric("Anomalies", summary["n_outliers"])
