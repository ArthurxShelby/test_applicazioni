import ipaddress
import pandas as pd
import streamlit as st

st.subheader("Panoramica Sedi e Reti con Stati Dinamici")

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


def colora_stato(valore):
  if valore == "Occupata":
    return "color: #ff4b4b; font-weight: bold;"  # Rosso
  else:
    return "color: #28a745; font-weight: bold;"  # Verde


for item in sedi_config:
  label = f"📍 Sede: {item['nome']} ({item['gruppo']})  |  Rete: {item['blocco']}/24  |  Subnet Mask: {item['subnet']}"

  with st.expander(label):
    base_ip = item["blocco"].rsplit(".", 1)[0]
    righe_ip = []

    for i in range(256):
      indirizzo = f"{base_ip}.{i}"
      # Simulazione: l'IP .10 viene marchiato come occupato per testare il rosso
      stato = "Occupata" if i == 10 else "Disponibile / Libero"
      righe_ip.append({"Indirizzo IP": indirizzo, "Stato": stato})

    df = pd.DataFrame(righe_ip)

    # Applicazione dello stile condizionale tramite pandas Styler
    df_stilizzato = df.style.map(
        colora_stato, subset=["Stato"]
    )  # Usa .applymap se usi versioni di pandas precedenti alla 2.1.0

    st.dataframe(df_stilizzato, use_container_width=True)
