import pathlib
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import weather_utils as wu  # noqa: E402

BASE = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk"
AREAS = [f"NO {i}" for i in range(1, 6)]
YEARS = list(range(2019, 2025))

st.title("Sliding window correlation")
st.write(
    "Correlation between a weather property and the reservoir fill, "
    "computed in a moving window. The weather is shifted by the chosen lag."
)

st.session_state.setdefault("area", "NO 3")
st.session_state.setdefault("weather_property", "Temperature (°C)")


@st.cache_data(ttl=3600)
def load_fill():
    resp = requests.get(f"{BASE}/HentOffentligData", timeout=30)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    df["date"] = pd.to_datetime(df["dato_Id"])
    df = df[df["omrType"] == "EL"]
    return df[["date", "omrnr", "fyllingsgrad"]].rename(columns={"fyllingsgrad": "fill_ratio"})


@st.cache_data(show_spinner="Downloading weather data...", ttl=86400)
def cached_weather(year):
    return wu.load_area_weather("Price area", year)


# --- Controls -------------------------------------------------------------
c1, c2, c3 = st.columns(3)
area = c1.selectbox("Price area", AREAS, index=AREAS.index(st.session_state["area"]))
props = list(wu.WEATHER_PROPERTIES)
prop = c2.selectbox(
    "Weather property", props, index=props.index(st.session_state["weather_property"])
)
reservoir_var = c3.selectbox("Reservoir variable", ["Fill ratio", "Weekly change in fill ratio"])
st.session_state["area"] = area
st.session_state["weather_property"] = prop

start_year, end_year = st.select_slider("Years", options=YEARS, value=(2021, 2024))
c4, c5 = st.columns(2)
lag = c4.slider("Lag (weeks, weather leads the reservoir)", 0, 12, 0)
window = c5.slider("Window length (weeks)", 4, 52, 12)

# --- Data -----------------------------------------------------------------
try:
    weather = pd.concat([cached_weather(y) for y in range(start_year, end_year + 1)])
    fill_all = load_fill()
except Exception as exc:
    st.error(f"Could not download data: {exc}")
    st.stop()

column = wu.WEATHER_PROPERTIES[prop]
how = "sum" if column == "precipitation_sum" else "mean"
weekly_weather = (
    weather[weather["area"] == area].set_index("date")[column].resample("W").agg(how)
)
weekly_weather = weekly_weather.rename("weather").reset_index()

number = int(area.split()[1])
fill = fill_all[fill_all["omrnr"] == number].sort_values("date").copy()
fill = fill[(fill["date"].dt.year >= start_year) & (fill["date"].dt.year <= end_year)]
fill["reservoir"] = fill["fill_ratio"]
if reservoir_var != "Fill ratio":
    fill["reservoir"] = fill["fill_ratio"].diff()

# Weather weeks end on Sunday; match each fill date to the nearest weather week
data = pd.merge_asof(
    fill[["date", "reservoir"]],
    weekly_weather,
    on="date",
    direction="nearest",
    tolerance=pd.Timedelta("3D"),
).dropna()

if len(data) < window + lag + 2:
    st.warning("Not enough data for this window and lag. Choose more years or a shorter window.")
    st.stop()

data["weather_lagged"] = data["weather"].shift(lag)
data["rolling_corr"] = data["weather_lagged"].rolling(window).corr(data["reservoir"])

# --- Plots ----------------------------------------------------------------
fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
    row_heights=[0.55, 0.45], specs=[[{"secondary_y": True}], [{}]],
)
fig.add_trace(go.Scatter(x=data["date"], y=data["reservoir"], name=reservoir_var,
                         line=dict(color="#0F766E")), row=1, col=1, secondary_y=False)
fig.add_trace(go.Scatter(x=data["date"], y=data["weather_lagged"], name=f"{prop} (lag {lag} w)",
                         line=dict(color="#D97706")), row=1, col=1, secondary_y=True)
fig.add_trace(go.Scatter(x=data["date"], y=data["rolling_corr"], name="Rolling correlation",
                         line=dict(color="#1F2933")), row=2, col=1)
fig.add_hline(y=0, line_dash="dash", line_color="grey", row=2, col=1)
fig.update_yaxes(title_text=reservoir_var, row=1, col=1, secondary_y=False)
fig.update_yaxes(title_text=prop, row=1, col=1, secondary_y=True)
fig.update_yaxes(title_text="Correlation", range=[-1, 1], row=2, col=1)
fig.update_layout(height=650, hovermode="x unified", margin=dict(t=30))
st.plotly_chart(fig, use_container_width=True)

# Overall correlation for each lag, to see which lag fits best
overall = []
for k in range(0, 13):
    r = data["weather"].shift(k).corr(data["reservoir"])
    overall.append({"lag (weeks)": k, "correlation": r})
overall = pd.DataFrame(overall)

st.subheader("Overall correlation per lag")
bar = px.bar(overall, x="lag (weeks)", y="correlation", range_y=[-1, 1])
bar.update_traces(marker_color="#0F766E")
bar.update_layout(height=300, margin=dict(t=10))
st.plotly_chart(bar, use_container_width=True)