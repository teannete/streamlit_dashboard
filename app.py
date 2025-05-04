import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import requests
import json
from io import StringIO
import tempfile
import os

# --- STATISTIKAAMETI API ---
STATISTIKAAMETI_API_URL = "https://andmed.stat.ee/api/v1/et/stat/RV032"
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
        "values": ["37", "39", "44", "49", "51", "57", "59", "65", "67", "70", "74", "78", "82", "84", "86"]
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

# --- ANDMETE LAADIMINE ---
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
    file_id = "1sY_lSxCXGpXUiPsGt62PfgbNbSIwVIL-"
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    response = requests.get(url)
    if response.status_code != 200:
        st.error(f"GeoJSON faili allalaadimine ebaõnnestus (status code: {response.status_code})")
        return gpd.GeoDataFrame()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".geojson") as tmp_file:
        tmp_file.write(response.content)
        tmp_path = tmp_file.name
    gdf = gpd.read_file(tmp_path)
    os.remove(tmp_path)
    return gdf

# --- STREAMLIT TÖÖLAUD ---
st.title("Loomulik iive maakonniti")

valitud_aasta = st.sidebar.selectbox("Vali aasta", list(range(2014, 2024)))

df = import_data()
gdf = import_geojson()

# Kontroll veergude olemasolu
if "Mehed Loomulik iive" not in df.columns or "Naised Loomulik iive" not in df.columns:
    st.error("Andmestikus puuduvad vajalikud veerud.")
    st.stop()

# Arvuta koguiive ja filtreeri
df["Loomulik iive"] = df["Mehed Loomulik iive"] + df["Naised Loomulik iive"]
df = df[df["Maakond"].isin(gdf["MNIMI"])]
gdf_merged = gdf.merge(df, left_on="MNIMI", right_on="Maakond")
gdf_aasta = gdf_merged[gdf_merged["Aasta"] == valitud_aasta]

# Kuvamine
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
