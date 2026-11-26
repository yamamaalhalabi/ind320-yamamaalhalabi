import pandas as pd
import plotly.express as px
import requests
import streamlit as st

BASE = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk"
OMR_TYPE = {"Country": "NO", "Price area": "EL", "Water area": "VASS"}
TYPE_NAME = {v: k for k, v in OMR_TYPE.items()}

st.title("Reservoir data")

st.session_state.setdefault("map_type", "Price area")
st.session_state.setdefault("map_area", "NO 3")


@st.cache_data(ttl=3600)
def load_data():
    """Download the full weekly history from the NVE API (cached for 1 hour)."""
    resp = requests.get(f"{BASE}/HentOffentligData", timeout=30)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())

    # The API returns dates as text, so convert them explicitly
    df["dato_Id"] = pd.to_datetime(df["dato_Id"])

    # Rename columns to English names, as in the notebook
    df = df.rename(columns={
        "dato_Id": "date",
        "fyllingsgrad": "fill_ratio",
        "kapasitet_TWh": "capacity_twh",
        "fylling_TWh": "fill_twh",
        "fyllingsgrad_forrige_uke": "fill_ratio_prev_week",
        "endring_fyllingsgrad": "fill_ratio_change",
    })
    return df.sort_values("date")


def area_label(omr_type, number):
    """Same names as on the map: NO, NO 1..5, VASS 1..4."""
    if omr_type == "NO":
        return "NO"
    if omr_type == "EL":
        return f"NO {number}"
    return f"VASS {number}"


try:
    df_all = load_data()
except Exception as exc:
    st.error(f"Could not download reservoir data: {exc}")
    st.stop()

# Area type defaults to the one chosen on the map page
types = list(OMR_TYPE.values())
default_type = OMR_TYPE[st.session_state["map_type"]]
area_type = st.radio("Area type", types, index=types.index(default_type), horizontal=True)
selected = st.session_state["map_area"]

df = df_all[df_all["omrType"] == area_type].copy()
df["area"] = [area_label(area_type, n) for n in df["omrnr"]]

columns = ["fill_ratio", "capacity_twh", "fill_twh",
           "fill_ratio_prev_week", "fill_ratio_change"]

tab_plot, tab_table = st.tabs(["Time series", "First-month overview"])

with tab_plot:
    column = st.selectbox("Column", columns)
    years = list(range(df["date"].dt.year.min(), df["date"].dt.year.max() + 1))
    start_year, end_year = st.select_slider(
        "Time period (years)", options=years, value=(years[-10], years[-1])
    )
    period = df[(df["date"].dt.year >= start_year) & (df["date"].dt.year <= end_year)]

    fig = px.line(period, x="date", y=column, color="area",
                  title=f"{column} for {area_type}, {start_year}-{end_year}")
    for trace in fig.data:  # highlight the area selected on the map
        trace.line.width = 4 if trace.name == selected else 1.5
    fig.update_layout(height=520, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"The thick line is the area selected on the map ({selected}).")

with tab_table:
    st.write("Sparklines for the first month of data, one row per area.")
    first_month = df[df["date"] < df["date"].min() + pd.DateOffset(months=1)]
    rows = []
    for area, group in first_month.groupby("area"):
        row = {"area": area}
        for col in columns:
            row[col] = group[col].tolist()
        rows.append(row)
    st.dataframe(
        pd.DataFrame(rows),
        column_config={col: st.column_config.LineChartColumn(col) for col in columns},
        hide_index=True,
        use_container_width=True,
    )