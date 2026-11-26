import json
import pathlib
import sys

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import weather_utils as wu  # noqa: E402

GEO_DIR = ROOT / "geodata"
BASE = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk"

# Area type -> (GeoJSON file, default selection, omrType in the NVE API)
LAYERS = {
    "Country": ("country.geojson", "NO", "NO"),
    "Price area": ("price_areas.geojson", "NO 3", "EL"),
    "Water area": ("water_areas.geojson", "VASS 1", "VASS"),
}
YEARS = list(range(2019, 2027))

st.title("Map")

st.session_state.setdefault("map_type", "Price area")
st.session_state.setdefault("map_area", "NO 3")
st.session_state.setdefault("weather_property", "Temperature (°C)")


@st.cache_data
def load_geojson(filename):
    with open(GEO_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=3600)
def load_fill():
    """Weekly reservoir fill for all areas (cached for 1 hour)."""
    resp = requests.get(f"{BASE}/HentOffentligData", timeout=30)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    df["date"] = pd.to_datetime(df["dato_Id"])
    return df[["date", "omrType", "omrnr", "fyllingsgrad"]].rename(
        columns={"fyllingsgrad": "fill_ratio"}
    )


@st.cache_data(show_spinner="Downloading weather data...", ttl=86400)
def cached_weather(area_type, year):
    return wu.load_area_weather(area_type, year)


def area_label(omr_type, number):
    """Same names as in the GeoJSON files: NO, NO 1..5, VASS 1..4."""
    if omr_type == "NO":
        return "NO"
    if omr_type == "EL":
        return f"NO {number}"
    return f"VASS {number}"


area_type = st.radio(
    "Area type",
    list(LAYERS),
    index=list(LAYERS).index(st.session_state["map_type"]),
    horizontal=True,
)
if area_type != st.session_state["map_type"]:
    st.session_state["map_type"] = area_type
    st.session_state["map_area"] = LAYERS[area_type][1]
    st.rerun()

colour_by = st.radio(
    "Colour by",
    ["Selection only", "Reservoir fill ratio", "Weather property"],
    horizontal=True,
)

filename, _, omr_type = LAYERS[area_type]
geojson = load_geojson(filename)
names = [feat["properties"]["area"] for feat in geojson["features"]]
selected = st.session_state["map_area"]

df = pd.DataFrame({"area": names})
params = dict(
    geojson=geojson,
    locations="area",
    featureidkey="properties.area",
    hover_name="area",
    opacity=0.65,
    center={"lat": 64.5, "lon": 15.0},
    zoom=2.3,
    height=650,
)

if colour_by == "Reservoir fill ratio":
    fill = load_fill()
    fill = fill[fill["omrType"] == omr_type].copy()
    fill["area"] = [area_label(omr_type, n) for n in fill["omrnr"]]

    weeks = sorted(fill["date"].dt.date.unique())
    week = st.select_slider("Week", options=weeks, value=weeks[-1])
    week_df = fill[fill["date"].dt.date == week][["area", "fill_ratio"]]
    df = df.merge(week_df, on="area", how="left")
    params.update(color="fill_ratio", color_continuous_scale="Teal")

elif colour_by == "Weather property":
    col1, col2 = st.columns(2)
    props = list(wu.WEATHER_PROPERTIES)
    prop = col1.selectbox(
        "Weather property", props, index=props.index(st.session_state["weather_property"])
    )
    year = col2.selectbox(
        "Year", YEARS, index=YEARS.index(st.session_state.get("year", 2024))
    )
    st.session_state["weather_property"] = prop
    st.session_state["year"] = year

    try:
        weather = cached_weather(area_type, year)
    except Exception as exc:  # network problem, rate limit, ...
        st.error(f"Could not download weather data: {exc}")
        st.stop()

    first, last = weather["date"].min().date(), weather["date"].max().date()
    start, end = st.slider(
        "Period", min_value=first, max_value=last, value=(first, last)
    )
    st.session_state["period"] = (start, end)

    column = wu.WEATHER_PROPERTIES[prop]
    period = weather[(weather["date"].dt.date >= start) & (weather["date"].dt.date <= end)]
    # Precipitation is summed over the period, everything else is averaged
    how = "sum" if column == "precipitation_sum" else "mean"
    agg = period.groupby("area")[column].agg(how).rename("value").reset_index()
    df = df.merge(agg, on="area", how="left")
    label = f"{prop}, {'total' if how == 'sum' else 'mean'}"
    params.update(
        color="value",
        color_continuous_scale="RdYlBu_r" if column == "temperature_2m_mean" else "Blues",
        labels={"value": label},
    )

else:
    df["group"] = df["area"].eq(selected).map({True: "Selected", False: "Other"})
    params.update(
        color="group",
        color_discrete_map={"Selected": "#0F766E", "Other": "#B7C9C6"},
    )

try:
    fig = px.choropleth_map(df, map_style="carto-positron", **params)
except AttributeError:  # older Plotly versions
    fig = px.choropleth_mapbox(df, mapbox_style="carto-positron", **params)

fig.update_traces(marker_line_width=1.5, marker_line_color="#1F2933")
if colour_by != "Selection only" and selected in names:
    # Highlight the selected area by fading the others
    fig.update_traces(
        selectedpoints=[names.index(selected)],
        selected={"marker": {"opacity": 1.0}},
        unselected={"marker": {"opacity": 0.4}},
    )
fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend=False)

event = st.plotly_chart(fig, on_select="rerun", key="map_chart", use_container_width=True)

# A click on an area stores the selection for the other pages
points = event.selection.points if event and event.selection else []
if points:
    clicked = points[0].get("location")
    if clicked and clicked != selected:
        st.session_state["map_area"] = clicked
        if area_type == "Price area":
            st.session_state["area"] = clicked  # same key the other pages use
        st.rerun()

st.write(f"Selected: **{selected}** ({area_type.lower()})")