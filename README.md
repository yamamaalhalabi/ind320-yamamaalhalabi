# IND320 – Data to decision

Compulsory project for IND320 (NMBU) by Yamama Alhalabi.

**Streamlit app:** https://ind320-yamamaalhalabi.streamlit.app/

## What the project contains

| Part | Content |
|------|---------|
| 1 | Dashboard basics: first Streamlit pages and a Jupyter notebook |
| 2 | Data sources: ENTSO-E power flows via Spark and Cassandra, stored in MongoDB Atlas and shown in the app |
| 3 | Reservoir filling degree (STL, spectrogram) and weather analysis (SPC outliers, LOF anomalies) |

## Streamlit pages

| Page | Content |
|------|---------|
| Table, Plot | Data and plots from part 1 |
| ENTSO-E | Power flows to and from Norway (data from MongoDB) |
| STL Spectrogram | STL decomposition and spectrogram of the reservoir filling degree from NVE |
| SPC LOF | Hourly ERA5 weather from open-meteo for an electricity price area (EL 1–5 = NO1–NO5), with SPC outliers and LOF anomalies |
| About | Project information |

## Notebooks

The notebooks in `notebooks/` document the work for each part (part 3: `part3_weather_analysis.ipynb`).

## Data sources

- NVE magasinstatistikk API (reservoir filling degree)
- NVE map services: price areas (Budområder) and NVE regions
- open-meteo ERA5 archive (weather)
- ENTSO-E (power flows)

## Run locally

```
pip install -r requirements.txt
streamlit run app.py
```

Secrets (MongoDB URI and ENTSO-E token) are kept in `.streamlit/secrets.toml`, which is not committed to git.