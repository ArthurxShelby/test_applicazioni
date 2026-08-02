import streamlit as st
import pandas as pd
import numpy as np
# Rimuoviamo matplotlib, non serve più per la mappa
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Tracker Uscite Bici Interattivo", page_icon="🚴‍♂️", layout="wide")

st.title("🚴‍♂️ Tracker Uscite in Bici (Mappa Interattiva)")
st.write("Inserisci i punti di passaggio. Il percorso verrà visualizzato sulla mappa interattiva.")

# Inizializzazione della sessione per i punti (Trieste - Basovizza - Prosecco)
if "points" not in st.session_state:
    st.session_state.points = [
        {"nome": "Trieste (Partenza)", "lat": 45.6495, "lon": 13.7768, "alt": 5},
        {"nome": "Basovizza", "lat": 45.6417, "lon": 13.8639, "alt": 370},
        {"nome": "Prosecco", "lat": 45.7142, "lon": 13.7433, "alt": 250}
    ]

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

# Sezione Principale: Layout a due colonne
col_map, col_data = st.columns([2, 1])

# --- Colonna Sinistra: Mappa ---
with col_map:
    st.subheader("🗺️ Mappa del Percorso")
    
    # Selettore stile mappa nella colonna della mappa
    map_style = st.radio(
        "Scegli stile mappa:",
        ("🗺️ Stradale (OpenStreetMap)", "衛星 Satellitare (con etichette)"),
        horizontal=True
    )
    
    if len(st.session_state.points) > 0:
        # Calcola il centro medio dei punti per centrare la mappa
        centro_lat = np.mean([p["lat"] for p in st.session_state.points])
        centro_lon = np.mean([p["lon"] for p in st.session_state.points])
        
        # Crea l'oggetto mappa Folium
        if map_style == "🗺️ Stradale (OpenStreetMap)":
            m = folium.Map(location=[centro_lat, centro_lon], zoom_start=12, tiles='OpenStreetMap')
        else:
            # Utilizziamo Esri World Imagery che è ottimo e spesso ha etichette integrate
            m = folium.Map(location=[centro_lat, centro_lon], zoom_start=12, tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community')

        # Prepara la lista di coordinate per la linea
        coordinate_linea = []

        for i, punto in enumerate(st.session_state.points):
            # Crea il popup con le info
            popup_html = f"<b>{punto['nome']}</b><br>Altitudine: {punto['alt']}m"
            
            # Colore diverso per partenza e arrivo
            if i == 0:
                colore_marker = 'green' # Partenza
                icona = 'play'
            elif i == len(st.session_state.points) - 1:
                colore_marker = 'red' # Arrivo
                icona = 'flag'
            else:
                colore_marker = 'blue' # Tappe intermedie
                icona = 'map-pin'

            # Aggiungi il Marker
            folium.Marker(
                [punto["lat"], punto["lon"]],
                popup=popup_html,
                tooltip=f"{punto['nome']} ({punto['alt']}m)",
                icon=folium.Icon(color=colore_marker, icon=icona, prefix='fa')
            ).add_to(m)
            
            coordinate_linea.append([punto["lat"], punto["lon"]])

        # Aggiungi la linea del percorso
        if len(coordinate_linea) > 1:
            folium.PolyLine(
                coordinate_linea,
                color='blue',
                weight=3,
                opacity=0.8,
                tooltip='Percorso'
            ).add_to(m)

        # Visualizza la mappa in Streamlit
        st_folium(m, width='100%', height=500)
    else:
        st.info("Aggiungi almeno un punto per visualizzare la mappa.")

# --- Colonna Destra: Dati e Tabella ---
with col_data:
    st.subheader("📊 Dati Tecnici")
    
    if len(st.session_state.points) > 0:
        df_points = pd.DataFrame(st.session_state.points)
        st.dataframe(df_points, use_container_width=True)
        
        # Calcoli di distanza e dislivello
        distanza_totale = 0.0
        dislivello_positivo = 0.0
        dislivello_negativo = 0.0
        
        for i in range(len(st.session_state.points) - 1):
            p1 = (st.session_state.points[i]["lat"], st.session_state.points[i]["lon"])
            p2 = (st.session_state.points[i+1]["lat"], st.session_state.points[i+1]["lon"])
            
            # Distanza in km
            distanza_totale += geodesic(p1, p2).kilometers
            
            # Calcolo dislivello
            alt1 = st.session_state.points[i]["alt"]
            alt2 = st.session_state.points[i+1]["alt"]
            diff_alt = alt2 - alt1
            
            if diff_alt > 0:
                dislivello_positivo += diff_alt
            else:
                dislivello_negativo += abs(diff_alt)

        # Metriche principali
        st.metric("📏 Distanza Totale", f"{distanza_totale:.2f} km")
        st.metric("📈 Dislivello Positivo", f"{dislivello_positivo:.0f} m")
        st.metric("📉 Dislivello Negativo", f"{dislivello_negativo:.0f} m")
    else:
        st.info("Aggiungi punti per vedere i dati.")

# RIMOSSO IL GRAFICO ALTImETRICO per far posto alla mappa completa.
# Se lo vuoi rimettere, puoi metterlo sotto i dati tecnici.
