import pandas as pd
import plotly.express as px
import streamlit as st
from pymongo import MongoClient

st.set_page_config(page_title="ENTSO-E flows", page_icon="⚡", layout="wide")
st.title("Cross-border electricity flows")


# --- Database access ------------------------------------------------------
@st.cache_resource
def get_collection():
    # The connection string is read from Streamlit secrets, never from the code
    client = MongoClient(st.secrets["mongo"]["uri"], serverSelectionTimeoutMS=10000)
    return client["ind320"]["entsoe_flows"]


@st.cache_data(ttl=3600)
def get_links_and_years():
    # A "link" is a pair of zones, regardless of direction (e.g. NO2 and DE_LU)
    coll = get_collection()
    pairs = coll.aggregate([{"$group": {"_id": {"f": "$from_zone", "t": "$to_zone"}}}])
    links = sorted({tuple(sorted((p["_id"]["f"], p["_id"]["t"]))) for p in pairs})
    years = sorted(coll.distinct("year"))
    return links, years


@st.cache_data(ttl=3600)
def load_flows(zone_a, zone_b, year):
    # Only the chosen link and year are fetched, so the page stays fast
    coll = get_collection()
    query = {"from_zone": {"$in": [zone_a, zone_b]},
             "to_zone": {"$in": [zone_a, zone_b]},
             "year": int(year)}
    fields = {"_id": 0, "from_zone": 1, "to_zone": 1, "ts": 1, "flow_mw": 1, "month": 1}
    df = pd.DataFrame(list(coll.find(query, fields)))
    if not df.empty:
        df["direction"] = df["from_zone"] + " → " + df["to_zone"]
        # Norwegian zones start with "NO", so flow from a NO zone leaves Norway
        df["leaves_norway"] = df["from_zone"].str.startswith("NO")
    return df


links, years = get_links_and_years()
link_labels = {f"{a} ↔ {b}": (a, b) for a, b in links}

left, right = st.columns(2)

# --- Left column: connection, year and pie chart --------------------------
with left:
    st.subheader("Yearly transfer")
    link_label = st.radio("Connection", list(link_labels))
    # Default to the second-last year: the last year is only partly in the data
    year = st.selectbox("Year", years, index=max(len(years) - 2, 0))

zone_a, zone_b = link_labels[link_label]
flows = load_flows(zone_a, zone_b, year)

with left:
    if flows.empty:
        st.info("No data for this connection and year.")
    else:
        # Hourly mean power (MW) times one hour gives energy (MWh)
        energy = flows.groupby("leaves_norway")["flow_mw"].sum()
        pie_df = pd.DataFrame({
            "Direction": ["Out of Norway", "Into Norway"],
            "Energy (MWh)": [energy.get(True, 0), energy.get(False, 0)],
        })
        fig_pie = px.pie(pie_df, names="Direction", values="Energy (MWh)",
                         title=f"{link_label}, {year}")
        st.plotly_chart(fig_pie, width="stretch")

# --- Right column: months and line plot -----------------------------------
month_names = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
               7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}

with right:
    st.subheader("Flow during selected months")
    selected = st.pills("Months", options=list(month_names.values()),
                        selection_mode="multi", default=["Jan"])
    selected_numbers = [m for m, name in month_names.items() if name in selected]

    subset = pd.DataFrame()
    if not flows.empty:
        subset = flows[flows["month"].isin(selected_numbers)].sort_values("ts")

    if subset.empty:
        st.info("No data for the selected months.")
    else:
        fig_line = px.line(subset, x="ts", y="flow_mw", color="direction",
                           title=f"{link_label}, {year}",
                           labels={"ts": "Time (UTC)", "flow_mw": "Flow (MW)",
                                   "direction": "Direction"})
        st.plotly_chart(fig_line, width="stretch")

# --- Data documentation ---------------------------------------------------
with st.expander("About the data"):
    st.markdown(
        "- **Source:** ENTSO-E Transparency Platform, cross-border electricity "
        "flows to and from Norway for the last two years.\n"
        "- **Processing:** downloaded with the ENTSO-E API, inserted into "
        "Cassandra with Spark, extracted with Spark, and stored as hourly "
        "averages in MongoDB.\n"
        "- **Units:** flow is power in MW. The pie chart sums hourly averages "
        "into energy (MWh), so it is an estimate, not an official yearly result."
    )