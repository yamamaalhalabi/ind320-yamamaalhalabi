import pathlib
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import forecasting as fm  # noqa: E402
import weather_utils as wu  # noqa: E402

st.title("Reservoir fill forecast")
st.write(
    "Online forecasting of the weekly reservoir fill with River (SNARIMAX). "
    "The area and time period are taken from the map page."
)

st.session_state.setdefault("map_type", "Price area")
st.session_state.setdefault("map_area", "NO 3")

OMR_TYPE = {"Country": "NO", "Price area": "EL", "Water area": "VASS"}
area_type = st.session_state["map_type"]
area = st.session_state["map_area"]
omrnr = 0 if area == "NO" else int(area.split()[1])
st.info(f"Data source: **{area}** ({area_type.lower()}). Change it on the Map page.")


@st.cache_data(ttl=3600)
def cached_series(omr_type, number):
    return fm.load_fill_series(omr_type, number)


@st.cache_data(show_spinner="Downloading weather data...", ttl=86400)
def cached_weather(a_type, year):
    return wu.load_area_weather(a_type, year)


try:
    series = cached_series(OMR_TYPE[area_type], omrnr)
except Exception as exc:
    st.error(f"Could not download reservoir data: {exc}")
    st.stop()

# --- Settings ---------------------------------------------------------------
with st.form("settings"):
    c1, c2, c3 = st.columns(3)
    p = c1.slider("AR order p", 0, 5, 2)
    d = c2.slider("Differencing d", 0, 2, 1)
    q = c3.slider("MA order q", 0, 5, 0)

    c4, c5, c6 = st.columns(3)
    history_weeks = c4.select_slider("Training history (weeks)", [52, 104, 156, 208, 260, 364, 520], value=260)
    horizon = c5.slider("Forecast horizon (weeks)", 1, 52, 12)
    lr = c6.select_slider("Learning rate", [0.001, 0.003, 0.01, 0.02], value=0.01)

    exog_choice = st.multiselect(
        "Exogenous weather variables",
        list(wu.WEATHER_PROPERTIES),
        default=["Temperature (°C)", "Precipitation (mm)"],
    )
    with st.expander("Seasonal terms (optional)"):
        s1, s2, s3 = st.columns(3)
        sp = s1.slider("Seasonal AR sp", 0, 2, 0)
        sd = s2.slider("Seasonal differencing sd", 0, 1, 0)
        sq = s3.slider("Seasonal MA sq", 0, 2, 0)

    use_map_period = False
    if "period" in st.session_state:
        start, end = st.session_state["period"]
        use_map_period = st.checkbox(
            f"Forecast the map period ({start} to {end}): train before it, forecast through it",
            value=True,
        )
    submitted = st.form_submit_button("Run forecast", type="primary")

# --- Training cut-off -------------------------------------------------------
cutoff = series.index.max()
if use_map_period:
    map_start, map_end = st.session_state["period"]
    cutoff = min(cutoff, pd.Timestamp(map_start))
    # The horizon follows the length of the map period (in weeks)
    horizon = int(max(1, min(52, -(-(map_end - map_start).days // 7))))
    st.caption(f"Training data ends {cutoff.date()}; forecast horizon {horizon} weeks (from the map period).")
train = series[series.index <= cutoff]
if len(train) < 30:
    st.error("Too little data before the chosen start date.")
    st.stop()

# --- Exogenous variables ----------------------------------------------------
exog = None
if exog_choice:
    try:
        first_year = (train.index[-min(history_weeks, len(train))]).year
        weather = pd.concat(
            [cached_weather(area_type, y) for y in range(first_year, min(cutoff.year, 2026) + 1)]
        )
    except Exception as exc:
        st.warning(f"Weather download failed, running without exogenous variables: {exc}")
    else:
        w = weather[weather["area"] == area].set_index("date")
        cols = {}
        for label in exog_choice:
            col = wu.WEATHER_PROPERTIES[label]
            how = "sum" if col == "precipitation_sum" else "mean"
            cols[label] = w[col].resample("W").agg(how)
        exog = pd.DataFrame(cols)

# --- Forecast ---------------------------------------------------------------
with st.spinner("Training the model..."):
    try:
        pred = fm.forecast(
            train, horizon=horizon, history_weeks=history_weeks,
            p=p, d=d, q=q, sp=sp, sd=sd, sq=sq,
            m=52 if (sp or sd or sq) else 1, lr=lr, exog=exog,
        )
    except Exception as exc:
        st.error(f"The model failed: {exc}")
        st.stop()

actual = series.reindex(pred.index)
has_actual = actual.notna().any()

if has_actual:
    mae = (pred - actual).abs().mean()
    st.metric("Mean absolute error on the known weeks", f"{mae:.3f}")
else:
    st.caption("No observed values exist for the forecast weeks yet.")

# --- Animated plot ----------------------------------------------------------
hist = train.iloc[-104:]
traces_static = go.Scatter(x=hist.index, y=hist.values, name="History", line=dict(color="#1F2933"))
actual_trace = go.Scatter(x=actual.index, y=actual.values, name="Observed",
                          line=dict(color="#0F766E", dash="dot"), visible=True if has_actual else "legendonly")


def fc_trace(k):
    return go.Scatter(x=pred.index[:k], y=pred.values[:k], name="Forecast",
                      mode="lines+markers", line=dict(color="#D97706"))


frames = [go.Frame(name=str(k), data=[traces_static, fc_trace(k), actual_trace], traces=[0, 1, 2])
          for k in range(1, len(pred) + 1)]
fig = go.Figure(data=[traces_static, fc_trace(1), actual_trace], frames=frames)
fig.update_layout(
    height=520,
    yaxis_title="Fill ratio",
    updatemenus=[dict(
        type="buttons", x=0.0, y=-0.15,
        buttons=[
            dict(label="Play", method="animate",
                 args=[None, {"frame": {"duration": 400, "redraw": True}, "fromcurrent": True}]),
            dict(label="Pause", method="animate",
                 args=[[None], {"frame": {"duration": 0}, "mode": "immediate"}]),
        ],
    )],
    sliders=[dict(
        currentvalue={"prefix": "Forecast week: "},
        steps=[dict(label=str(i + 1), method="animate",
                    args=[[str(i + 1)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}])
               for i in range(len(pred))],
    )],
)
st.plotly_chart(fig, use_container_width=True)

st.dataframe(pd.DataFrame({"forecast": pred, "observed": actual}).round(3))