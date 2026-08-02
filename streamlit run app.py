import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from geopy.distance import geodesic

st.set_page_config(page_title="Tracker Uscite Bici", page_icon="🚴‍♂️", layout="wide")

st.title("🚴‍♂️ Tracker Uscite in Bici (Distanza & Dislivello)")
st.write("Inserisci i punti di passaggio (Waypoint) del tuo giro in bici. Il programma calcolerà la distanza totale e stimerà il dislivello.")

# Inizializzazione della sessione per i punti
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
        lat = st.number_input("Latitudine", value=45.6700, format="%.4f")
        lon = st.number_input("Longitudine", value=13.7800, format="%.4f")
        alt = st.number_input("Altitudine (metri s.l.m.)", value=300)
        
        submitted = st.form_submit_button("Aggiungi alla lista")
        if submitted:
            st.session_state.points.append({"nome": nome_tappa, "lat": lat, "lon": lon, "alt": alt})
            st.rerun()

    if st.button("🔄 Resetta Tappe"):
        st.session_state.points = []
        st.rerun()

# Mostra la tabella delle tappe attuali
st.subheader("📍 Elenco Tappe Inserite")
if len(st.session_state.points) > 0:
    df_points = pd.DataFrame(st.session_state.points)
    st.dataframe(df_points, use_container_width=True)
    
    # Calcoli di distanza e dislivello
    distanza_totale = 0.0
    dislivello_positivo = 0.0
    dislivello_negativo = 0.0
    
    distanze_parziali = [0.0]
    altitudini = [st.session_state.points[0]["alt"]]
    nomi_tappe = [st.session_state.points[0]["nome"]]

    for i in range(len(st.session_state.points) - 1):
        p1 = (st.session_state.points[i]["lat"], st.session_state.points[i]["lon"])
        p2 = (st.session_state.points[i+1]["lat"], st.session_state.points[i+1]["lon"])
        
        # Distanza in km tra due punti consecutivi
        dist_tratta = geodesic(p1, p2).kilometers
        distanza_totale += dist_tratta
        distanze_parziali.append(distanza_totale)
        
        # Calcolo dislivello
        alt1 = st.session_state.points[i]["alt"]
        alt2 = st.session_state.points[i+1]["alt"]
        diff_alt = alt2 - alt1
        
        if diff_alt > 0:
            dislivello_positivo += diff_alt
        else:
            dislivello_negativo += abs(diff_alt)
            
        altitudini.append(alt2)
        nomi_tappe.append(st.session_state.points[i+1]["nome"])

    # Metriche principali in evidenza
    col1, col2, col3 = st.columns(3)
    col1.metric("📏 Distanza Totale", f"{distanza_totale:.2f} km")
    col2.metric("📈 Dislivello Positivo (Salita)", f"{dislivello_positivo:.0f} m")
    col3.metric("📉 Dislivello Negativo (Discesa)", f"{dislivello_negativo:.0f} m")

    # Grafico altimetrico
    st.subheader("⛰️ Profilo Altimetrico del Percorso")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(distanze_parziali, altitudini, marker='o', color='tab:green', linewidth=2, markersize=6)
    ax.fill_between(distanze_parziali, altitudini, color='tab:green', alpha=0.2)
    
    ax.set_xlabel("Distanza Progressiva (km)")
    ax.set_ylabel("Altitudine (metri)")
    ax.grid(True, linestyle='--', alpha=0.6)
    
    # Etichette dei punti sul grafico
    for i, txt in enumerate(nomi_tappe):
        ax.annotate(txt, (distanze_parziali[i], altitudini[i]), textcoords="offset points", xytext=(0,10), ha='center', fontsize=9)

    st.pyplot(fig)

else:
    st.info("Aggiungi almeno due punti dalla barra laterale per iniziare il calcolo.")
