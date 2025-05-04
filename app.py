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

# Kontrolli veergude olemasolu
required_cols = ["Maakond", "Mehed Loomulik iive", "Naised Loomulik iive"]
if not all(col in df.columns for col in required_cols):
    st.error("Andmestikus puuduvad vajalikud veerud. Kontrolli andmevormingut.")
    st.write("Veerud:", df.columns.tolist())
    st.stop()

# Arvuta loomulik iive
df["Loomulik iive"] = df["Mehed Loomulik iive"] + df["Naised Loomulik iive"]

# Kontrolli maakondade ühtlust
st.sidebar.markdown("**Kontrolli maakonnanimede sobivust:**")
if st.sidebar.checkbox("Näita maakondade nimed"):
    st.sidebar.write("Andmestikus:", sorted(df["Maakond"].unique()))
    st.sidebar.write("GeoJSONis:", sorted(gdf["MNIMI"].unique()))

# Ühenda geoandmetega
gdf_merged = gdf.merge(df, left_on="MNIMI", right_on="Maakond")

# Kui merge ebaõnnestus
if gdf_merged.empty:
    st.error("Geoandmete ja statistikaandmete ühendamine ebaõnnestus – maakondade nimed ei klapi.")
    st.stop()

# Filtreeri valitud aasta
gdf_aasta = gdf_merged[gdf_merged["Aasta"] == valitud_aasta]

# Kontroll, kas midagi on joonistada
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
