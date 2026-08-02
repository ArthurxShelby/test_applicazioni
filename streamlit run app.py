import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import requests

st.set_page_config(page_title="Tracker Bici da Corsa - Mappa Fluida", page_icon="🚴‍♂️", layout="wide")

st.title("🚴‍♂️ Tracker Uscite in Bici da Corsa")
st.write("Mappa interattiva con zoom a due dita attivo, senza pulsanti +/- e gestione waypoint fluida.")

if "points" not in st.session_state:
    st.session_state.points = [
        {"nome": "Stazione centrale trieste", "lat": 45.6587, "lon": 13.7710, "alt": 5},
        {"nome": "Sistiana", "lat": 45.7716, "lon": 13.6370, "alt": 70},
        {"nome": "Tappa 3", "lat": 45.7954, "lon": 13.5870, "alt": 30},
        {"nome": "Tappa 4", "lat": 45.8179, "lon": 13.5770, "alt": 15}
    ]

if "map_center" not in st.session_state:
    st.session_state.map_center = [45.72, 13.68]
if "map_zoom" not in st.session_state:
    st.session_state.map_zoom = 11

def cerca_luogo(query):
    url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1"
    headers = {'User-Agent': 'TrackerBiciApp/1.0'}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                alt = ottieni_altitudine(lat, lon)
                return lat, lon, int(alt)
    except Exception as e:
        st.error(f"Errore nella ricerca del luogo: {e}")
    return None, None, None

def ottieni_altitudine(lat, lon):
    alt = 50
    try:
        elev_url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}"
        elev_res = requests.get(elev_url, timeout=3)
        if elev_res.status_code == 200:
            elev_data = elev_res.json()
            if "results" in elev_data and len(elev_data["results"]) > 0:
                alt = elev_data["results"][0]["elevation"]
    except:
        pass
    return int(alt)

def ottieni_percorso_stradale(punti):
    if len(punti) < 2:
        return [], 0.0
    
    coords_str = ";".join([f"{p['lon']},{p['lat']}" for p in punti])
    url = f"http://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "routes" in data and len(data["routes"]) > 0:
                route = data["routes"][0]
                geometry = [[coord[1], coord[0]] for coord in route["geometry"]["coordinates"]]
                distanza_km = route["distance"] / 1000.0
                return geometry, distanza_km
    except:
        pass
    
    fallback_coords = [[p["lat"], p["lon"]] for p in punti]
    return fallback_coords, 0.0

with st.sidebar:
    st.header("⚙️ Gestione Tappe")
    
    modalita = st.radio(
        "Modalità inserimento:",
        ("🔍 Ricerca per Nome/Indirizzo", "🗺️ Inserimento Manuale (Click su Mappa)"),
        horizontal=False
    )
    
    st.markdown("---")
    
    if modalita == "🔍 Ricerca per Nome/Indirizzo":
        with st.form("add_point_form_search"):
            st.subheader("➕ Aggiungi per Nome")
            ricerca_input = st.text_input("Nome Luogo / Indirizzo", "Monfalcone")
            submitted_search = st.form_submit_button("Cerca e Aggiungi")
            
            if submitted_search:
                if len(ricerca_input) > 0:
                    with st.spinner("Ricerca in corso..."):
                        lat_trovata, lon_trovata, alt_trovata = cerca_luogo(ricerca_input)
                    
                    if lat_trovata is not None:
                        st.session_state.points.append({
                            "nome": ricerca_input.capitalize(), 
                            "lat": lat_trovata, 
                            "lon": lon_trovata, 
                            "alt": alt_trovata
                        })
                        st.success("Tappa aggiunta con successo!")
                        st.rerun()
                    else:
                        st.error("Luogo non trovato.")
                else:
                    st.warning("Inserisci il nome di un luogo.")
    else:
        st.subheader("🗺️ Click su Mappa Attivo")
        st.info("Clicca sulla mappa in basso per aggiungere un punto.")
        nome_click = st.text_input("Nome per il punto cliccato", f"Tappa {len(st.session_state.points) + 1}")

    st.markdown("---")
    st.subheader("🗑️ Azioni Rapide")
    
    if st.button("↩️ Elimina Ultimo Waypoint"):
        if len(st.session_state.points) > 0:
            eliminato = st.session_state.points.pop()
            st.success(f"Rimosso: {eliminato['nome']}")
            st.rerun()
        else:
            st.warning("Non ci sono tappe da eliminare.")

    if st.button("🔄 Resetta Tutte le Tappe"):
        st.session_state.points = []
        st.session_state.map_center = [45.72, 13.68]
        st.session_state.map_zoom = 11
        st.rerun()

@st.fragment
def render_mappa_e_dati():
    st.subheader("🗺️ Mappa del Percorso Stradale")

    map_style = st.radio(
        "Scegli stile mappa:",
        ("🗺️ Stradale (OpenStreetMap)", "🛰️ Satellitare (con etichette)"),
        horizontal=True,
        key="selettore_stile_mappa"
    )

    distanza_stradale = 0.0

    if len(st.session_state.points) > 0:
        if map_style == "🗺️ Stradale (OpenStreetMap)":
            tiles_url = 'OpenStreetMap'
            attr = None
        else:
            tiles_url = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
            attr = 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'

        # zoom_control=False rimuove i pulsanti + e -, mentre scrollWheelZoom=True lascia attivo lo zoom con due dita
        m = folium.Map(
            location=st.session_state.map_center, 
            zoom_start=st.session_state.map_zoom, 
            tiles=tiles_url, 
            attr=attr,
            zoom_control=False,
            scrollWheelZoom=True,
            dragging=True
        )

        coordinate_strada, distanza_stradale = ottieni_percorso_stradale(st.session_state.points)

        if len(coordinate_strada) > 1:
            folium.PolyLine(
                coordinate_strada,
                color='red',
                weight=4,
                opacity=0.8,
                tooltip='Percorso Stradale'
            ).add_to(m)

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

        map_output = st_folium(
            m, 
            width='100%', 
            height=750, 
            returned_objects=["last_clicked"]
        )
        
        if map_output and modalita == "🗺️ Inserimento Manuale (Click su Mappa)":
            if map_output.get("last_clicked"):
                click_lat = map_output["last_clicked"]["lat"]
                click_lon = map_output["last_clicked"]["lng"]
                
                ultimo_punto = st.session_state.points[-1] if st.session_state.points else None
                if not ultimo_punto or (ultimo_punto["lat"] != click_lat or ultimo_punto["lon"] != click_lon):
                    alt_cliccata = ottieni_altitudine(click_lat, click_lon)
                    st.session_state.points.append({
                        "nome": nome_click,
                        "lat": click_lat,
                        "lon": click_lon,
                        "alt": alt_cliccata
                    })
    else:
        st.info("Aggiungi almeno un punto per visualizzare la mappa.")

    st.markdown("---")

    st.subheader("📊 Dati Tecnici e Tabella Tappe")

    if len(st.session_state.points) > 0:
        col1, col2, col3 = st.columns(3)
        
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

        col1.metric("📏 Distanza su Strada", f"{distanza_stradale:.2f} km")
        col2.metric("📈 Dislivello Positivo", f"{dislivello_positivo:.0f} m")
        col3.metric("📉 Dislivello Negativo", f"{dislivello_negativo:.0f} m")
        
        st.write("")
        df_points = pd.DataFrame(st.session_state.points)
        st.dataframe(df_points, use_container_width=True)
    else:
        st.info("Aggiungi punti per vedere i dati.")

render_mappa_e_dati()
