import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import requests
import json
from io import StringIO

# ---- KONFIGURATSIOON ----
STATISTIKAAMETI_API_URL = "https://andmed.stat.ee/api/v1/et/stat/RV032"
GEOJSON_FAIL = "maakonnad_simplified.geojson"

JSON_PAYLOAD_STR = """{
  "query": [
    {
      "code": "Aasta",
      "selection": {
        "filter": "item",
        "values": ["2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023"]
      }
    },
    {
      "code": "Maakond",
      "selection": {
        "filter": "item",
        "values": ["39", "44", "49", "51", "57", "59", "65", "67", "70", "74", "78", "82", "84", "86"]
      }
    },
    {
      "code": "Sugu",
      "selection": {
        "filter": "item",
        "values": ["2", "3"]
      }
    }
  ],
  "response": {
    "format": "csv"
  }
}
"""

# ---- ANDMETE LAADIMINE ----
@st.cache_data
def import_data():
    headers = {'Content-Type': 'application/json'}
    response = requests.post(STATISTIKAAMETI_API_URL, json=json.loads(JSON_PAYLOAD_STR), headers=headers)
    if response.status_code == 200:
        df = pd.read_csv(StringIO(response.content.decode('utf-8-sig')))
        return df
    else:
        st.error(f"Viga andmete laadimisel: {response.status_code}")
        return pd.DataFrame()

@st.cache_data
def import_geojson():
    return gpd.read_file(GEOJSON_FAIL)

# ---- TÖÖLAUD ----
st.title("Loomulik iive maakonniti")

# Külgriba – aasta valik
valitud_aasta = st.sidebar.selectbox("Vali aasta", [str(aasta) for aasta in range(2014, 2024)])

# Lae andmed
df = import_data()
gdf = import_geojson()

# Ühenda geoandmed ja statistikaandmed
gdf_merged = gdf.merge(df, left_on="MNIMI", right_on="Maakond")

# Kontrolli, kas merge õnnestus
if gdf_merged.empty:
    st.error("Andmete ühendamine ebaõnnestus – kontrolli maakondade nimesid.")
    st.stop()

# Arvuta "Loomulik iive"
try:
    gdf_merged["Loomulik iive"] = gdf_merged["Mehed Loomulik iive"] + gdf_merged["Naised Loomulik iive"]
except KeyError as e:
    st.error(f"Puuduv veerg: {e}")
    st.stop()

# Filtreeri valitud aasta järgi
gdf_aasta = gdf_merged[gdf_merged["Aasta"] == valitud_aasta]

# Kui andmed puuduvad, anna märku
if gdf_aasta.empty or gdf_aasta.geometry.is_empty.all():
    st.warning(f"Aastal {valitud_aasta} ei ole visualiseeritavaid andmeid.")
else:
    fig, ax = plt.subplots(figsize=(10, 7))
    gdf_aasta.plot(
        column="Loomulik iive",
        cmap="viridis",
        linewidth=0.8,
        ax=ax,
        edgecolor='0.8',
        legend=True,
        legend_kwds={'label': "Loomulik iive", 'shrink': 0.6}
    )
    ax.set_title(f"Loomulik iive maakondade kaupa, {valitud_aasta}")
    ax.axis("off")
    st.pyplot(fig)
