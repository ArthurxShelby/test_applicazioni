import streamlit as st
import pandas as pd
import numpy as np
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium
import requests

st.set_page_config(page_title="Tracker Bici da Corsa - Strade Reali", page_icon="🚴‍♂️", layout="wide")

st.title("🚴‍♂️ Tracker Uscite in Bici da Corsa (Percorsi su Strada)")
st.write("Inserisci le tappe: il sistema calcolerà la traccia seguendo le reali strade asfaltate.")

# Inizializzazione della sessione
if "points" not in st.session_state:
    st.session_state.points = [
        {"nome": "Trieste (Partenza)", "lat": 45.6495, "lon": 13.7768, "alt": 5},
        {"nome": "Basovizza", "lat": 45.6417, "lon": 13.8639, "alt": 370},
        {"nome": "Prosecco", "lat": 45.7142, "lon": 13.7433, "alt": 250}
    ]

# Funzione per ottenere il percorso stradale reale tramite OSRM (Open Source Routing Machine)
def ottieni_percorso_stradale(punti):
    if len(punti) < 2:
        return [], 0.0
    
    # Costruisce la stringa delle coordinate per l'API OSRM (lon,lat;lon,lat...)
    coords_str = ";".join([f"{p['lon']},{p['lat']}" for p in punti])
    url = f"http://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "routes" in data and len(data["routes"]) > 0:
                route = data["routes"][0]
                # Le coordinate in GeoJSON sono [lon, lat], Folium vuole [lat, lon]
                geometry = [[coord[1], coord[0]] for coord in route["geometry"]["coordinates"]]
                distanza_km = route["distance"] / 1000.0  # convertito in km
                return geometry, distanza_km
    except Exception as e:
        st.error(f"Errore di connessione al servizio di routing stradale: {e}")
    
    # Fallimento di riserva (linea retta se l'API non risponde)
    fallback_coords = [[p["lat"], p["lon"]] for p in punti]
    return fallback_coords, 0.0

with st.sidebar:
    st.header("➕ Aggiungi Tappa")
    with st.form("add_point_form"):
        nome_tappa = st.text_input("Nome Luogo / Punto", "Opicina")
        lat = st.number_input("Latitudine", value=45.6700, format="%.5f")
        lon = st.number_input("Longitudine", value=13.7800, format="%.5f")
        alt = st.number_input("Altitudine (metri s.l.m.)", value=300)
        
        submitted = st.form_submit_button("Aggiungi alla lista")
        if submitted:
            if len(nome_tappa) > 0:
                st.session_state.points.append({"nome": nome_tappa, "lat": lat, "lon": lon, "alt": alt})
                st.rerun()
            else:
                st.warning("Inserisci un nome per la tappa.")

    if st.button("🔄 Resetta Tappe"):
        st.session_state.points = []
        st.rerun()

# Layout principale
col_map, col_data = st.columns([2, 1])

with col_map:
    st.subheader("🗺️ Mappa del Percorso Stradale")
    
    # Selettore dello stile della mappa
    map_style = st.radio(
        "Scegli stile mappa:",
        ("🗺️ Stradale (OpenStreetMap)", "🛰️ Satellitare (con etichette)"),
        horizontal=True
    )
    
    if len(st.session_state.points) > 0:
        centro_lat = np.mean([p["lat"] for p in st.session_state.points])
        centro_lon = np.mean([p["lon"] for p in st.session_state.points])
        
        # Inizializzazione mappa
        if map_style == "🗺️ Stradale (OpenStreetMap)":
            m = folium.Map(location=[centro_lat, centro_lon], zoom_start=12, tiles='OpenStreetMap')
        else:
            m = folium.Map(
                location=[centro_lat, centro_lon], 
                zoom_start=12, 
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 
                attr='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
            )

        # Calcola tracciato stradale reale
        coordinate_strada, distanza_stradale = ottieni_percorso_stradale(st.session_state.points)

        # Disegna la linea che segue le strade
        if len(coordinate_strada) > 1:
            folium.PolyLine(
                coordinate_strada,
                color='red',
                weight=4,
                opacity=0.8,
                tooltip='Percorso Stradale'
            ).add_to(m)

        # Aggiungi i marker dei punti
        for i, punto in enumerate(st.session_state.points):
            popup_html = f"<b>{punto['nome']}</b><br>Altitudine: {punto['alt']}m"
            if i == 0:
                colore_marker = 'green'
                icona = 'play'
            elif i == len(st.session_state.points) - 1:
                colore_marker = 'darkred'
                icona = 'flag'
            else:
                colore_marker = 'blue'
                icona = 'map-pin'

            folium.Marker(
                [punto["lat"], punto["lon"]],
                popup=popup_html,
                tooltip=f"{punto['nome']} ({punto['alt']}m)",
                icon=folium.Icon(color=colore_marker, icon=icona, prefix='fa')
            ).add_to(m)

        st_folium(m, width='100%', height=500)
    else:
        st.info("Aggiungi almeno un punto per visualizzare la mappa.")

with col_data:
    st.subheader("📊 Dati Tecnici")
    
    if len(st.session_state.points) > 0:
        df_points = pd.DataFrame(st.session_state.points)
        st.dataframe(df_points, use_container_width=True)
        
        # Calcolo dislivello basato sui punti inseriti
        dislivello_positivo = 0.0
        dislivello_negativo = 0.0
        
        for i in range(len(st.session_state.points) - 1):
            alt1 = st.session_state.points[i]["alt"]
            alt2 = st.session_state.points[i+1]["alt"]
            diff_alt = alt2 - alt1
            if diff_alt > 0:
                dislivello_positivo += diff_alt
            else:
                dislivello_negativo += abs(diff_alt)

        # Mostra i dati con la distanza stradale effettiva calcolata dall'API
        st.metric("📏 Distanza su Strada", f"{distanza_stradale:.2f} km")
        st.metric("📈 Dislivello Positivo", f"{dislivello_positivo:.0f} m")
        st.metric("📉 Dislivello Negativo", f"{dislivello_negativo:.0f} m")
    else:
        st.info("Aggiungi punti per vedere i dati.")
