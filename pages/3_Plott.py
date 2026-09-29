import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Side 3 - Plott")

@st.cache_data
def load_data():
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

# One label per month present in the data, used by the slider
months = df.index.to_period("M").unique()
month_labels = [str(m) for m in months]

column_choice = st.selectbox("Velg kolonne", options=["Alle"] + list(df.columns))

start_label, end_label = st.select_slider(
    "Velg periode (måneder)",
    options=month_labels,
    value=(month_labels[0], month_labels[0]),
)

start_time = pd.Period(start_label, freq="M").start_time
end_time = pd.Period(end_label, freq="M").end_time
subset = df.loc[start_time:end_time]

if column_choice == "Alle":
    fig = px.line(subset, x=subset.index, y=subset.columns, title="Reservoir data - alle kolonner")
else:
    fig = px.line(subset, x=subset.index, y=column_choice, title=f"Reservoir data - {column_choice}")

fig.update_layout(xaxis_title="Dato", yaxis_title="Verdi")
st.plotly_chart(fig, width='stretch')