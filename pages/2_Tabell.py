import streamlit as st
import pandas as pd

st.title("Side 2 - Tabell")

@st.cache_data
def load_data():
    # Read weekly reservoir data and keep only the national ("NO") level
    df = pd.read_csv("reservoirs.csv", parse_dates=["dato_Id"])
    df = df[df["omrType"] == "NO"].copy()
    df = df.sort_values("dato_Id")
    df = df.rename(columns={
        "dato_Id": "date",
        "fyllingsgrad": "fill_ratio",
        "kapasitet_TWh": "capacity_twh",
        "fylling_TWh": "fill_twh",
        "fyllingsgrad_forrige_uke": "fill_ratio_prev_week",
        "endring_fyllingsgrad": "fill_ratio_change",
    })
    df = df.set_index("date")
    return df[["fill_ratio", "capacity_twh", "fill_twh",
                "fill_ratio_prev_week", "fill_ratio_change"]]

df = load_data()

# Build one row per column, each with a sparkline of the first month's values
first_month_end = df.index.min() + pd.DateOffset(months=1)
first_month = df[df.index <= first_month_end]

table_data = pd.DataFrame({
    "column": df.columns,
    "first_month": [first_month[col].tolist() for col in df.columns],
})

st.dataframe(
    table_data,
    column_config={
        "first_month": st.column_config.LineChartColumn("First month", width="medium"),
    },
    hide_index=True,
)
