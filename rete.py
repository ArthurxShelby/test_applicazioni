import ipaddress
import streamlit as st

st.subheader("Panoramica Sedi e Reti")

sedi_config = [
    {
        "nome": "Sede Centrale",
        "blocco": "192.168.1.0",
        "subnet": "255.255.255.0",
        "gruppo": "Blocco 1",
    },
    {
        "nome": "Sede Centrale",
        "blocco": "192.168.2.0",
        "subnet": "255.255.255.0",
        "gruppo": "Blocco 2",
    },
    {
        "nome": "Sede 2",
        "blocco": "192.168.3.0",
        "subnet": "255.255.255.0",
        "gruppo": "Blocco Unico",
    },
    {
        "nome": "Sede 3",
        "blocco": "192.168.4.0",
        "subnet": "255.255.255.0",
        "gruppo": "Blocco Unico",
    },
    {
        "nome": "Sede 4",
        "blocco": "192.168.5.0",
        "subnet": "255.255.255.0",
        "gruppo": "Blocco Unico",
    },
    {
        "nome": "Sede 5",
        "blocco": "192.168.6.0",
        "subnet": "255.255.255.0",
        "gruppo": "Blocco Unico",
    },
    {
        "nome": "Sede 6",
        "blocco": "192.168.7.0",
        "subnet": "255.255.255.0",
        "gruppo": "Blocco Unico",
    },
    {
        "nome": "Sede 7",
        "blocco": "192.168.8.0",
        "subnet": "255.255.255.0",
        "gruppo": "Blocco Unico",
    },
]

for item in sedi_config:
  label = f"📍 Sede: {item['nome']} ({item['gruppo']})  |  Rete: {item['blocco']}/24  |  Subnet Mask: {item['subnet']}"

  with st.expander(label):
    base_ip = item["blocco"].rsplit(".", 1)[0]
    colonne_dati = []
    
    # Genera esattamente 256 righe (da .0 a .255) per ciascun blocco con la propria colonna di stato
    for i in range(256):
      colonne_dati.append({
          "Indirizzo IP": f"{base_ip}.{i}",
          "Stato": "Disponibile / Libero",
      })

    st.dataframe(colonne_dati, use_container_width=True)
      
