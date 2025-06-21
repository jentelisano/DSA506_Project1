pip install folium streamlit_folium --quiet
import plotly.express as px
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd, folium, json
from folium.features import GeoJsonTooltip
from streamlit_folium import st_folium
import streamlit as st
import json, requests

# Load data
df = pd.read_csv("rain-agriculture.csv")
df.columns = df.columns.map(str).str.strip().str.lower().str.replace(" ", "_")

# Clean up the headers
def tidy_headers(series: pd.Index) -> pd.Index:
    return (
        series
        .str.strip()
        .str.lower()
        .str.replace(r"\s*\(.*\)", "", regex=True)
        .str.replace(" ", "_")
        .str.replace("__", "_")
        .str.rstrip("_")
    )

df.columns = tidy_headers(df.columns)
df = df.loc[:, ~df.columns.duplicated()]

# Get Sum for total monsoon rain
# Get Average crop yield
yield_columns = [c for c in df.columns if c.endswith("_yield")]
df["total_monsoon_rain"] = df[["jun", "jul", "aug", "sep"]].sum(axis=1)
df["average_crop_yield"] = df[yield_columns].mean(axis=1, skipna=True)
df[["state_name", "year", "total_monsoon_rain", "average_crop_yield"] + yield_columns]

# Get the lat/long of the states so we can make the polygons with GeoJson
GEO_URL = "https://raw.githubusercontent.com/geohacker/india/master/state/india_telengana.geojson"

india_geo_text = requests.get(GEO_URL, timeout=30).text
india_geo = json.loads(india_geo_text)

# Use NAME_1 for state names in geojson
name_key = "NAME_1"

# Fix state names in your dataframe exactly as they appear in the GeoJSON
fix = {
    "andhra pradesh": "Andhra Pradesh",
    "arunachal pradesh": "Arunachal Pradesh",
    "assam": "Assam",
    "bihar": "Bihar",
    "chhattisgarh": "Chhattisgarh",
    "goa": "Goa",
    "gujarat": "Gujarat",
    "haryana": "Haryana",
    "himachal pradesh": "Himachal Pradesh",
    "jammu & kashmir": "Jammu and Kashmir",
    "jharkhand": "Jharkhand",
    "karnataka": "Karnataka",
    "kerala": "Kerala",
    "madhya pradesh": "Madhya Pradesh",
    "maharashtra": "Maharashtra",
    "manipur": "Manipur",
    "meghalaya": "Meghalaya",
    "mizoram": "Mizoram",
    "nagaland": "Nagaland",
    "odisha": "Orissa",
    "orissa": "Orissa",
    "punjab": "Punjab",
    "rajasthan": "Rajasthan",
    "sikkim": "Sikkim",
    "tamil nadu": "Tamil Nadu",
    "telangana": "Telangana",
    "tripura": "Tripura",
    "uttar pradesh": "Uttar Pradesh",
    "uttarakhand": "Uttaranchal",
    "west bengal": "West Bengal"
}

# Apply clean mapping without forcing lowercase
df["state_name"] = df["state_name"].str.strip().str.lower().replace(fix)

# Capitalize to match GeoJSON
df["state_name"] = df["state_name"].map(lambda x: fix.get(x, x)).str.title()

# GeoJSON state set (title case from NAME_1)
geo_states = {f["properties"][name_key] for f in india_geo["features"]}
data_states = set(df["state_name"])

# Make the map
def draw_crop_map(data, geo, crop, year, name_key="NAME_1"):

    # average per state for that year
    sub = (
        data.loc[data["year"] == year, ["state_name", crop]]
            .assign(state_name=lambda d: d.state_name.str.strip().str.title())
            .groupby("state_name", as_index=False)[crop]
            .mean()
    )

    m = folium.Map(location=[22.8, 80.9], zoom_start=5, tiles="cartodbpositron")

    folium.Choropleth(
        geo_data=geo,
        data=sub,
        columns=["state_name", crop],
        key_on=f"feature.properties.{name_key}",
        fill_color="YlGn",
        nan_fill_color="lightgrey",
        legend_name=f"{crop.replace('_yield','').title().replace('_',' ')} — {year}",
        highlight=True,
    ).add_to(m)

    folium.GeoJson(
        geo,
        style_function=lambda _: {"fillOpacity": 0, "color": "transparent"},
        tooltip=GeoJsonTooltip(fields=[name_key], aliases=["State:"]),
    ).add_to(m)

    return m

# Make the year slider in streamlit
st.title("🗺️ Indian Crop-Yield Map")

# sidebar year slider
selected_year = st.sidebar.slider(
    "Select Year:",
    int(df.year.min()),
    int(df.year.max()),
    2000           # default = 2000 (your current static view)
)

# crop dropdown
selected_crop = st.sidebar.selectbox(
    "Crop Yield Column:",
    ["average_crop_yield"] + yield_cols,
    index=0
)

# draw & show map
folium_map = draw_crop_map(df, india_geo, selected_crop, selected_year)
st_folium(folium_map, use_container_width=True)
