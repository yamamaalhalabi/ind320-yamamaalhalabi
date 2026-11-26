import datetime as dt
import json
import pathlib

import pandas as pd
import requests
from shapely.geometry import shape

GEO_DIR = pathlib.Path(__file__).resolve().parent / "geodata"
GEO_FILES = {
    "Country": "country.geojson",
    "Price area": "price_areas.geojson",
    "Water area": "water_areas.geojson",
}

# Label shown in the app -> open-meteo daily variable
WEATHER_PROPERTIES = {
    "Temperature (°C)": "temperature_2m_mean",
    "Precipitation (mm)": "precipitation_sum",
    "Wind speed (m/s)": "wind_speed_10m_max",
    "Wind gusts (m/s)": "wind_gusts_10m_max",
}


def area_points(area_type):
    """One representative point (always inside the polygon) per area."""
    with open(GEO_DIR / GEO_FILES[area_type], encoding="utf-8") as f:
        geojson = json.load(f)
    points = {}
    for feat in geojson["features"]:
        p = shape(feat["geometry"]).representative_point()
        points[feat["properties"]["area"]] = (p.y, p.x)  # (lat, lon)
    return points


def load_area_weather(area_type, year):
    """Daily weather for one year, one point per area (ERA5 via open-meteo)."""
    points = area_points(area_type)
    names = list(points)
    last_day = min(dt.date(year, 12, 31), dt.date.today() - dt.timedelta(days=7))

    resp = requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": ",".join(f"{points[n][0]:.4f}" for n in names),
            "longitude": ",".join(f"{points[n][1]:.4f}" for n in names),
            "start_date": f"{year}-01-01",
            "end_date": last_day.isoformat(),
            "daily": ",".join(WEATHER_PROPERTIES.values()),
            "wind_speed_unit": "ms",
            "timezone": "UTC",
        },
        timeout=60,
    )
    if resp.status_code == 429:
        raise RuntimeError("open-meteo request limit reached, try again later.")
    resp.raise_for_status()

    data = resp.json()
    if isinstance(data, dict):  # a single location returns a dict, not a list
        data = [data]

    frames = []
    for name, item in zip(names, data):
        df = pd.DataFrame(item["daily"])
        df["time"] = pd.to_datetime(df["time"])
        df["area"] = name
        frames.append(df)
    return pd.concat(frames, ignore_index=True).rename(columns={"time": "date"})