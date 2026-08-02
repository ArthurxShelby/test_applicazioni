import streamlit as st
import pandas as pd
import numpy as np
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium
import requests

st.set_page_config(page_title="Tracker Bici da Corsa - Click Mappa", page_icon="🚴‍♂️", layout="wide")

st.title("🚴‍♂️ Tracker Uscite in Bici da Corsa")
st.write("Cerca per indirizzo oppure seleziona l'inserimento manuale per **cliccare direttamente sulla mappa** e aggiungere i waypoint.")

# Inizializzazione della sessione
if "points" not in st.session_state:
    st.session_state.points = [
        {"nome": "Trieste Centrale", "lat": 45.6562, "lon": 13.7740, "alt": 5},
        {"nome": "Basovizza", "lat": 45.6417, "lon": 13.8639, "alt": 370},
        {"nome": "Prosecco", "lat": 45.7142, "lon": 13.7433, "alt": 250}
    ]

# Funzione per cercare coordinate e altitudine da un indirizzo/luogo
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

# Funzione per ottenere l'altitudine tramite API pubblica
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

# Funzione per calcolare il percorso stradale reale (OSRM)
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
            ricerca_input = st.text_input("Nome Luogo / Indirizzo", "Opicina")
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
                        st.error("Luogo non trovato. Prova a essere più specifico.")
                else:
                    st.warning("Inserisci il nome di un luogo.")
    else:
        st.subheader("🗺️ Click su Mappa Attivo")
        st.info("Clicca in un punto qualsiasi della mappa a destra per aggiungere automaticamente una nuova tappa.")
        
        # Opzionale: nome da dare al punto cliccato
        nome_click = st.text_input("Nome per il prossimo punto cliccato", f"Tappa {len(st.session_state.points) + 1}")

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
        st.rerun()

# Layout principale
col_map, col_data = st.columns([2, 1])

with col_map:
    st.subheader("🗺️ Mappa del Percorso Stradale")
    
    map_style = st.radio(
        "Scegli stile mappa:",
        ("🗺️ Stradale (OpenStreetMap)", "🛰️ Satellitare (con etichette)"),
        horizontal=True
    )
    
    if len(st.session_state.points) > 0:
        centro_lat = np.mean([p["lat"] for p in st.session_state.points])
        centro_lon = np.mean([p["lon"] for p in st.session_state.points])
        
        if map_style == "🗺️ Stradale (OpenStreetMap)":
            m = folium.Map(location=[centro_lat, centro_lon], zoom_start=12, tiles='OpenStreetMap')
        else:
            m = folium.Map(
                location=[centro_lat, centro_lon], 
                zoom_start=12, 
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 
                attr='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
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

        # Mostra la mappa e cattura il click se siamo in modalità manuale
        map_output = st_folium(m, width='100%', height=500)
        
        # Gestione del click sulla mappa
        if modalita == "🗺️ Inserimento Manuale (Click su Mappa)":
            if map_output and map_output.get("last_clicked"):
                click_lat = map_output["last_clicked"]["lat"]
                click_lon = map_output["last_clicked"]["lng"]
                
                # Evita di aggiungere lo stesso punto più volte di seguito a causa del refresh
                ultimo_punto = st.session_state.points[-1] if st.session_state.points else None
                if not ultimo_punto or (ultimo_punto["lat"] != click_lat or ultimo_punto["lon"] != click_lon):
                    alt_cliccata = ottieni_altitudine(click_lat, click_lon)
                    st.session_state.points.append({
                        "nome": nome_click,
                        "lat": click_lat,
                        "lon": click_lon,
                        "alt": alt_cliccata
                    })
                    st.rerun()
    else:
        st.info("Aggiungi almeno un punto per visualizzare la mappa.")

with col_data:
    st.subheader("📊 Dati Tecnici")
    
    if len(st.session_state.points) > 0:
        df_points = pd.DataFrame(st.session_state.points)
        st.dataframe(df_points, use_container_width=True)
        
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

        st.metric("📏 Distanza su Strada", f"{distanza_stradale:.2f} km")
        st.metric("📈 Dislivello Positivo", f"{dislivello_positivo:.0f} m")
        st.metric("📉 Dislivello Negativo", f"{dislivello_negativo:.0f} m")
    else:
        st.info("Aggiungi punti per vedere i dati.")
