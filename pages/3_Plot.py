import pandas as pd
import plotly.express as px
import requests
import streamlit as st

BASE = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk"

st.title("Reservoir fill levels (NVE)")


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


df_all = load_data()

# Radio buttons: choose the type of area (national, price areas, watercourses)
area_type = st.radio("Area type", ["NO", "EL", "VASS"], horizontal=True)

# Select box: choose which column to plot
columns = ["fill_ratio", "capacity_twh", "fill_twh",
           "fill_ratio_prev_week", "fill_ratio_change"]
column = st.selectbox("Column", columns)

# Slider: choose the time interval (years) that is used for the data
years = list(range(df_all["date"].dt.year.min(), df_all["date"].dt.year.max() + 1))
start_year, end_year = st.select_slider(
    "Time period (years)", options=years, value=(years[-10], years[-1])
)

# Keep only the chosen area type and time interval
df = df_all[
    (df_all["omrType"] == area_type)
    & (df_all["date"].dt.year >= start_year)
    & (df_all["date"].dt.year <= end_year)
].copy()

# One line per area number (e.g. NO 1 ... NO 5 for EL)
df["area"] = df["omrnr"].astype(str)

fig = px.line(df, x="date", y=column, color="area",
              title=f"{column} for {area_type}, {start_year}-{end_year}")
st.plotly_chart(fig, use_container_width=True)