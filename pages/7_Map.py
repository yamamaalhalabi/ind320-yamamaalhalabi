import json
import pathlib

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

GEO_DIR = pathlib.Path(__file__).resolve().parent.parent / "geodata"
BASE = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk"

# Area type -> (GeoJSON file, default selection, omrType in the NVE API)
LAYERS = {
    "Country": ("country.geojson", "NO", "NO"),
    "Price area": ("price_areas.geojson", "NO 3", "EL"),
    "Water area": ("water_areas.geojson", "VASS 1", "VASS"),
}

st.title("Map")

st.session_state.setdefault("map_type", "Price area")
st.session_state.setdefault("map_area", "NO 3")


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

colour_by = st.radio("Colour by", ["Selection only", "Reservoir fill ratio"], horizontal=True)

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
if colour_by == "Reservoir fill ratio" and selected in names:
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