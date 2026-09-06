import ipaddress
import pandas as pd
import streamlit as st

st.subheader("Gestione Interattiva Sedi e Reti IP")

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

if "dataframes_rete" not in st.session_state:
  st.session_state.dataframes_rete = {}
  for idx, item in enumerate(sedi_config):
    base_ip = item["blocco"].rsplit(".", 1)[0]
    righe_ip = []
    for i in range(256):
      righe_ip.append({
          "Indirizzo IP": f"{base_ip}.{i}",
          "Nome Macchina": "",
          "Stato": "🟢 Libero",
      })
    st.session_state.dataframes_rete[idx] = pd.DataFrame(righe_ip)

for idx, item in enumerate(sedi_config):
  label = f"📍 Sede: {item['nome']} ({item['gruppo']})  |  Rete: {item['blocco']}/24  |  Subnet Mask: {item['subnet']}"

  with st.expander(label):
    df_corrente = st.session_state.dataframes_rete[idx]

    df_modificato = st.data_editor(
        df_corrente,
        column_config={
            "Indirizzo IP": st.column_config.TextColumn(
                "Indirizzo IP", disabled=True
            ),
            "Nome Macchina": st.column_config.TextColumn(
                "Nome Macchina (Digita e premi Invio)"
            ),
            "Stato": st.column_config.SelectboxColumn(
                "Stato", options=["🟢 Libero", "🔴 Occupato"], required=True
            ),
        },
        key=f"editor_sede_{idx}",
        use_container_width=True,
        hide_index=True,
    )

    # Verifica se ci sono modifiche da applicare sullo stato
    modificato = False
    for i in range(len(df_modificato)):
      nome_mac = str(df_modificato.loc[i, "Nome Macchina"]).strip()
      stato_attuale = df_modificato.loc[i, "Stato"]

      if nome_mac and nome_mac != "nan" and stato_attuale != "🔴 Occupato":
        df_modificato.loc[i, "Stato"] = "🔴 Occupato"
        modificato = True
      elif (not nome_mac or nome_mac == "nan") and stato_attuale == "🔴 Occupato":
        df_modificato.loc[i, "Stato"] = "🟢 Libero"
        modificato = True

    st.session_state.dataframes_rete[idx] = df_modificato

    # Se lo stato è cambiato, forza il ricaricamento visivo immediato
    if modificato:
      st.rerun()
