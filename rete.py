import ipaddress
import pandas as pd
import streamlit as st

st.subheader("Gestione Reti e Hardware per Sede")

# Definizione delle sedi e dei relativi blocchi di rete
sedi_config = [
    {
        "id": 1,
        "nome": "Sede Centrale",
        "blocco": "192.168.1.0",
        "subnet": "255.255.255.0",
        "gruppo": "Blocco 1",
    },
    {
        "id": 2,
        "nome": "Sede Centrale",
        "blocco": "192.168.2.0",
        "subnet": "255.255.255.0",
        "gruppo": "Blocco 2",
    },
    {
        "id": 3,
        "nome": "Sede 2",
        "blocco": "192.168.3.0",
        "subnet": "255.255.255.0",
        "gruppo": "Blocco Unico",
    },
    {
        "id": 4,
        "nome": "Sede 3",
        "blocco": "192.168.4.0",
        "subnet": "255.255.255.0",
        "gruppo": "Blocco Unico",
    },
    {
        "id": 5,
        "nome": "Sede 4",
        "blocco": "192.168.5.0",
        "subnet": "255.255.255.0",
        "gruppo": "Blocco Unico",
    },
    {
        "id": 6,
        "nome": "Sede 5",
        "blocco": "192.168.6.0",
        "subnet": "255.255.255.0",
        "gruppo": "Blocco Unico",
    },
    {
        "id": 7,
        "nome": "Sede 6",
        "blocco": "192.168.7.0",
        "subnet": "255.255.255.0",
        "gruppo": "Blocco Unico",
    },
    {
        "id": 8,
        "nome": "Sede 7",
        "blocco": "192.168.8.0",
        "subnet": "255.255.255.0",
        "gruppo": "Blocco Unico",
    },
]

# Inizializzazione della memoria di sessione per i dataframe delle reti
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

# Selezione della sede dal menu a tendina principale
sede_scelta = st.selectbox(
    "📍 Seleziona la Sede da Gestire",
    sedi_config,
    format_func=lambda x: (
        f"{x['nome']} ({x['gruppo']}) — Rete: {x['blocco']}/24"
    ),
)

# Trova l'indice corrispondente alla sede selezionata
idx_selezionato = sedi_config.index(sede_scelta)

# Layout a tab per dividere la visualizzazione della rete e dell'hardware dettagliato
tab_rete, tab_hardware = st.tabs(
    ["🌐 Blocco IP & Occupazione", "💻 Inventario Hardware Dettagliato"]
)

with tab_rete:
  st.markdown(
      f"### 🌐 Gestione IP: {sede_scelta['nome']} - {sede_scelta['gruppo']}"
  )
  st.info(
      f"Subnet Mask associata: {sede_scelta['subnet']} | Digita il nome"
      " macchina per occupare l'IP."
  )

  df_corrente = st.session_state.dataframes_rete[idx_selezionato]

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
      key=f"editor_sede_{idx_selezionato}",
      use_container_width=True,
      hide_index=True,
  )

  # Logica di aggiornamento automatico stato (Verde / Rosso)
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

  st.session_state.dataframes_rete[idx_selezionato] = df_modificato

  if modificato:
    st.rerun()

with tab_hardware:
  st.markdown(
      f"### 💻 Specifiche Hardware: {sede_scelta['nome']} -"
      f" {sede_scelta['gruppo']}"
  )

  # Form per registrare i dettagli hardware legati a questa sede
  with st.form(key=f"form_hw_{idx_selezionato}"):
    col1, col2 = st.columns(2)
    with col1:
      hw_nome = st.text_input("Nome Macchina")
      hw_ip = st.text_input("Indirizzo IP Assegnato")
      hw_marca = st.text_input("Marca")
      hw_modello = st.text_input("Modello")
      hw_cpu = st.text_input("Processore")
    with col2:
      hw_ram = st.number_input("RAM (GB)", min_value=2, max_value=256, value=16)
      hw_tipo_hd = st.selectbox("Tipo HD", ["SSD", "HDD", "NVMe"])
      hw_cap_hd = st.text_input("Capienza HD")
      hw_garanzia = st.date_input("Scadenza Garanzia")

    btn_salva = st.form_submit_button("Salva Componente Hardware")
    if btn_salva:
      st.success(
          f"Scheda hardware per '{hw_nome}' salvata correttamente per la"
          f" {sede_scelta['nome']}!"
      )

  # Qui in seguito collegherai la query a Supabase filtrando per sede_id == sede_scelta['id']
  st.markdown("---")
  st.write("📋 **Elenco macchine registrate con specifiche complete:**")
  # Esempio di tabella vuota o popolata dai dati del DB
  df_hw_vuoto = pd.DataFrame(columns=[
      "IP",
      "Nome",
      "Marca",
      "Modello",
      "CPU",
      "RAM",
      "HD",
      "Garanzia",
  ])
  st.dataframe(df_hw_vuoto, use_container_width=True, hide_index=True)
