import ipaddress
import streamlit as st

st.subheader("Panoramica Completa: Sedi e Blocchi IP (0 - 255)")

# Elenco delle sedi e dei blocchi associati (puoi sostituirlo con una query a Supabase: supabase.table('sedi').select('*').execute())
sedi_config = [
    {"nome": "Sede Centrale", "blocco": "192.168.1.0/24", "subnet": "hhhhhh",},
    {"nome": "Sede Centrale", "blocco": "192.168.2.0/24"},
    {"nome": "Sede 2", "blocco": "192.168.3.0/24"},
    {"nome": "Sede 3", "blocco": "192.168.4.0/24"},
    {"nome": "Sede 4", "blocco": "192.168.5.0/24"},
    {"nome": "Sede 5", "blocco": "192.168.6.0/24"},
    {"nome": "Sede 6", "blocco": "192.168.7.0/24"},
    {"nome": "Sede 7", "blocco": "192.168.8.0/24"},
]

for item in sedi_config:
  nome_sede = item["nome"]
  blocco = item["blocco"]

  # Crea un menu a tendina per ogni blocco di ogni sede
  with st.expander(f"📍 {nome_sede} — Blocco: {blocco}"):
    # Estrae la parte di rete comune (es. '192.168.1')
    base_ip = blocco.split("/")[0].rsplit(".", 1)[0]

    # Genera tutte le 256 righe da 0 a 255
    colonne_dati = []
    for i in range(256):
      indirizzo_corrente = f"{base_ip}.{i}"
      colonne_dati.append(
          {"Indirizzo IP": indirizzo_corrente, "Stato": "Disponibile / Libero"}
      )

    # Mostra la tabella completa da 0 a 255 per questo blocco
    st.dataframe(colonne_dati, use_container_width=True)
    
