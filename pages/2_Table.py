import pandas as pd
import requests
import streamlit as st

BASE = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk"

st.title("Reservoir data: first month")


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
df = df_all[df_all["omrType"] == area_type]

# Keep only the first month of data for the chosen area type
columns = ["fill_ratio", "capacity_twh", "fill_twh",
           "fill_ratio_prev_week", "fill_ratio_change"]
first_month = df[df["date"] < df["date"].min() + pd.DateOffset(months=1)]

# One row per area number, one sparkline column per data column
rows = []
for area_nr, group in first_month.groupby("omrnr"):
    row = {"area": f"{area_type} {area_nr}"}
    for col in columns:
        row[col] = group[col].tolist()
    rows.append(row)
table = pd.DataFrame(rows)

st.dataframe(
    table,
    column_config={col: st.column_config.LineChartColumn(col) for col in columns},
    hide_index=True,
    use_container_width=True,
)