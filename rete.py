import pandas as pd
import streamlit as st

st.subheader("Gestione Reti e Hardware per Sede")

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

# Inizializzazione della memoria di sessione per le reti
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

# Inizializzazione della memoria di sessione per l'hardware dettagliato
if "inventario_hardware" not in st.session_state:
  st.session_state.inventario_hardware = []

sede_scelta = st.selectbox(
    "📍 Seleziona la Sede da Gestire",
    sedi_config,
    format_func=lambda x: (
        f"{x['nome']} ({x['gruppo']}) — Rete: {x['blocco']}/24"
    ),
)

idx_selezionato = sedi_config.index(sede_scelta)

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

  # 1. Estrae in automatico le macchine che hanno un IP occupato nella tabella sopra per questa sede
  df_rete_sede = st.session_state.dataframes_rete[idx_selezionato]
  macchine_occupate = df_rete_sede[
      df_rete_sede["Stato"] == "🔴 Occupato"
  ].to_dict("records")

  st.write("📋 **Dispositivi registrati in questa sede (da Tabella IP):**")

  if macchine_occupate:
    lista_esterna = []
    for m in macchine_occupate:
      lista_esterna.append({
          "Sede": sede_scelta["nome"],
          "Blocco": sede_scelta["gruppo"],
          "Indirizzo IP": m["Indirizzo IP"],
          "Nome Macchina": m["Nome Macchina"],
      })
    st.dataframe(
        pd.DataFrame(lista_esterna), use_container_width=True, hide_index=True
    )
  else:
    st.warning(
        "Nessun dispositivo registrato in questo blocco. Assegna un nome"
        " macchina nella tab 'Blocco IP & Occupazione'."
    )

  st.markdown("---")
  st.markdown(
      "🛠️ **Aggiungi dettagli tecnici avanzati per le macchine della sede:**"
  )

  # Form per aggiungere marca, modello, ram, ecc. collegati alla macchina
  with st.form(key=f"form_hw_{idx_selezionato}"):
    ip_disponibili = [
        m["Indirizzo IP"]
        for m in macchine_occupate
        if m["Nome Macchina"].strip()
    ]

    if ip_disponibili:
      ip_scelto = st.selectbox("Seleziona IP Macchina", ip_disponibili)
      col1, col2 = st.columns(2)
      with col1:
        hw_marca = st.text_input("Marca (es. Dell, HP)")
        hw_modello = st.text_input("Modello")
        hw_cpu = st.text_input("Processore")
      with col2:
        hw_ram = st.number_input("RAM (GB)", min_value=2, max_value=256, value=16)
        hw_tipo_hd = st.selectbox("Tipo HD", ["SSD", "HDD", "NVMe"])
        hw_cap_hd = st.text_input("Capienza HD")
        hw_garanzia = st.date_input("Scadenza Garanzia")

      btn_salva = st.form_submit_button("Salva Specifiche Tecniche")
      if btn_salva:
        st.success(
            f"Specifiche salvate con successo per l'IP {ip_scelto}!"
        )
    else:
      st.info(
          "Prima inserisci almeno un nome macchina nella tab 'Blocco IP &"
          " Occupazione' per associargli i componenti hardware."
      )
