import ipaddress
import pandas as pd
import streamlit as st

# Controllo autenticazione tramite st.secrets
if "autenticato" not in st.session_state:
  st.session_state.autenticato = False

if not st.session_state.autenticato:
  st.subheader("🔐 Accesso Protetto")
  password_inserita = st.text_input(
      "Inserisci la password per accedere", type="password"
  )
  if st.button("Accedi"):
    app_password = st.secrets.get("APP_PASSWORD", "")
    if password_inserita == app_password:
      st.session_state.autenticato = True
      st.rerun()
    else:
      st.error("Password errata.")
  st.stop()

st.subheader("Gestione Reti e Hardware per Sede")

sedi_config = [
    {
        "id": 1,
        "nome": "Trieste",
        "blocco": "38.0",
        "subnet": "254.0",
        "range_custom": range(1, 256),
    },
    {
        "id": 2,
        "nome": "Sede Centrale",
        "blocco": "39.0",
        "subnet": "254.0",
        "range_custom": range(1, 256),
    },
    {
        "id": 3,
        "nome": "Monfalcone",
        "blocco": "86.0",
        "subnet": "255.0",
        "range_custom": range(1, 256),
    },
    {
        "id": 4,
        "nome": "Grado",
        "blocco": "168.0",
        "subnet": "255.0",
        "range_custom": range(1, 256),
    },
    {
        "id": 5,
        "nome": "Nogaro",
        "blocco": "61.0",
        "subnet": "255.0",
        "range_custom": range(1, 256),
    },
    {
        "id": 6,
        "nome": "Lignao",
        "blocco": "26.0",
        "subnet": "255.0",
        "range_custom": range(1, 256),
    },
    {
        "id": 7,
        "nome": "Marano",
        "blocco": "29.0",
        "subnet": "255.0",
        "range_custom": range(1, 256),
    },
    {
        "id": 8,
        "nome": "MMnn",
        "blocco": "66.0",
        "subnet": "255.0",
        "range_custom": range(1, 256),
    },
    {
        "id": 9,
        "nome": "P.nuovo",
        "blocco": "77.0",
        "subnet": "255.192",
        "range_custom": range(65, 127),
    },
]

def pulisci_valore(val):
  if val is None or pd.isna(val):
    return ""
  s = str(val).strip()
  if s.lower() in ["none", "nan", "", "-"]:
    return ""
  return s

if "dataframes_rete" not in st.session_state:
  st.session_state.dataframes_rete = {}

for idx, item in enumerate(sedi_config):
  base_ip = item["blocco"].split(".")[0]
  range_ip = item["range_custom"]

  old_df = st.session_state.dataframes_rete.get(idx, pd.DataFrame())
  old_data_map = {}
  if not old_df.empty and "_ip_completo" in old_df.columns:
    for _, r in old_df.iterrows():
      old_data_map[r["_ip_completo"]] = {
          "Nome Macchina": pulisci_valore(r.get("Nome Macchina", "")),
          "Tipologia": pulisci_valore(r.get("Tipologia", "")),
          "Stato": r.get("Stato", "🟢 Libero"),
      }

  righe_ip = []
  for i in range_ip:
    ip_completo = f"{base_ip}.{i}"
    existing = old_data_map.get(
        ip_completo,
        {
            "Nome Macchina": "",
            "Tipologia": "",
            "Stato": "🟢 Libero",
        },
    )
    righe_ip.append({
        "Indirizzo IP": ip_completo,
        "_ip_completo": ip_completo,
        "Nome Macchina": existing["Nome Macchina"],
        "Tipologia": existing["Tipologia"],
        "Stato": existing["Stato"],
    })
  st.session_state.dataframes_rete[idx] = pd.DataFrame(righe_ip)

if "hardware_dettagli" not in st.session_state:
  st.session_state.hardware_dettagli = {}

idx_selezionato = st.selectbox(
    "📍 Seleziona la Sede da Gestire",
    options=range(len(sedi_config)),
    format_func=lambda i: (
        f"{sedi_config[i]['nome']} — Rete: {sedi_config[i]['blocco']}"
        f" / {sedi_config[i]['subnet']}"
    ),
)

sede_scelta = sedi_config[idx_selezionato]
blocco_completo_ip = sede_scelta["blocco"].split(".")[0]
subnet_ultimi_due = sede_scelta["subnet"]

tab_rete, tab_hardware = st.tabs(
    ["🌐 Blocco IP & Occupazione", "💻 Inventario Hardware Dettagliato"]
)

with tab_rete:
  st.markdown(f"### 🌐 Gestione IP: {sede_scelta['nome']}")
  st.info(
      f"Subnet Mask associata: {subnet_ultimi_due} | Digita il nome dispositivo"
      " per occupare l'IP e seleziona la tipologia."
  )

  df_corrente = st.session_state.dataframes_rete[idx_selezionato]

  df_corrente["Nome Macchina"] = df_corrente["Nome Macchina"].apply(pulisci_valore)
  df_corrente["Tipologia"] = df_corrente["Tipologia"].apply(pulisci_valore)

  totale_ip = len(df_corrente)
  df_occupati = df_corrente[
      df_corrente["Stato"].astype(str).str.contains("Occupato")
  ]
  occupati = len(df_occupati)
  liberi = totale_ip - occupati

  n_pc = len(df_corrente[df_corrente["Tipologia"] == "PC / Macchina"])
  n_stampanti = len(df_corrente[df_corrente["Tipologia"] == "Stampante"])
  n_switch = len(df_corrente[df_corrente["Tipologia"] == "Switch"])

  col_m1, col_m2, col_m3 = st.columns(3)
  col_m1.metric("Totale IP", totale_ip)
  col_m2.metric("🟢 Liberi", liberi)
  col_m3.metric("🔴 Occupati", occupati)

  st.markdown("##### 📊 Riepilogo Tipologie Dispositivi")
  col_t1, col_t2, col_t3 = st.columns(3)
  col_t1.metric("🖥️ PC / Macchine", n_pc)
  col_t2.metric("🖨️ Stampanti", n_stampanti)
  col_t3.metric("🔌 Switch", n_switch)

  st.markdown("---")

  df_per_editor = df_corrente.drop(columns=["_ip_completo"], errors="ignore").copy()
  
  # Pulizia preventiva dei valori per evitare qualsiasi "None" grafico
  opzioni_tipologia = ["PC / Macchina", "Stampante", "Switch", "Altro"]
  for i in range(len(df_per_editor)):
    if not df_per_editor.loc[i, "Nome Macchina"]:
      df_per_editor.loc[i, "Tipologia"] = ""
    else:
      val_t = str(df_per_editor.loc[i, "Tipologia"])
      if val_t not in opzioni_tipologia:
        df_per_editor.loc[i, "Tipologia"] = "PC / Macchina" if val_t == "" else val_t

  df_per_editor = df_per_editor.fillna("")

  df_modificato = st.data_editor(
      df_per_editor,
      column_config={
          "Indirizzo IP": st.column_config.TextColumn(
              "Indirizzo IP", disabled=True
          ),
          "Nome Macchina": st.column_config.TextColumn(
              "Nome / Identificativo Dispositivo"
          ),
          "Tipologia": st.column_config.SelectboxColumn(
              "Tipologia Dispositivo",
              options=opzioni_tipologia,
              required=False
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
    ip_corr = df_corrente.loc[i, "_ip_completo"]
    nome_mac = pulisci_valore(df_modificato.loc[i, "Nome Macchina"])
    tipo_scelto = pulisci_valore(df_modificato.loc[i, "Tipologia"])

    if not nome_mac:
      tipo_scelto = ""

    stato_attuale = df_modificato.loc[i, "Stato"]

    if nome_mac and stato_attuale != "🔴 Occupato":
      df_modificato.loc[i, "Stato"] = "🔴 Occupato"
      modificato = True
    elif not nome_mac and stato_attuale == "🔴 Occupato":
      df_modificato.loc[i, "Stato"] = "🟢 Libero"
      tipo_scelto = ""
      if ip_corr in st.session_state.hardware_dettagli:
        del st.session_state.hardware_dettagli[ip_corr]
      modificato = True

    if df_corrente.loc[i, "Tipologia"] != tipo_scelto or df_corrente.loc[i, "Nome Macchina"] != nome_mac:
      modificato = True

    df_corrente.loc[i, "Nome Macchina"] = nome_mac
    df_corrente.loc[i, "Tipologia"] = tipo_scelto
    df_corrente.loc[i, "Stato"] = df_modificato.loc[i, "Stato"]

  st.session_state.dataframes_rete[idx_selezionato] = df_corrente

  if modificato:
    st.rerun()

with tab_hardware:
  st.markdown(f"### 💻 Specifiche Hardware: {sede_scelta['nome']}")

  df_rete_sede = st.session_state.dataframes_rete[idx_selezionato]

  with st.expander(
      "🛠️ Aggiungi dettagli tecnici avanzati (Manuale)", expanded=True
  ):
    macchine_occupate = df_rete_sede.to_dict("records")
    with st.form(key=f"form_hw_{idx_selezionato}"):
      ip_disponibili_mostrati = [m["Indirizzo IP"] for m in macchine_occupate]

      if ip_disponibili_mostrati:
        scelta_mostrata = st.selectbox("Seleziona IP Dispositivo", ip_disponibili_mostrati)
        ip_scelto = [
            m["_ip_completo"]
            for m in macchine_occupate
            if m["Indirizzo IP"] == scelta_mostrata
        ][0]

        dettagli_esistenti = st.session_state.hardware_dettagli.get(
            ip_scelto, {}
        )

        col1, col2 = st.columns(2)
        with col1:
          hw_marca = st.text_input(
              "Marca (es. Dell, HP, Cisco)",
              value=pulisci_valore(dettagli_esistenti.get("Marca", "")),
          )
          hw_modello = st.text_input(
              "Modello", value=pulisci_valore(dettagli_esistenti.get("Modello", ""))
          )
          hw_cpu = st.text_input(
              "Processore / Dettaglio", value=pulisci_valore(dettagli_esistenti.get("Processore", ""))
          )
        with col2:
          ram_salvata = dettagli_esistenti.get("RAM", "16 GB")
          try:
            ram_val = int(str(ram_salvata).replace(" GB", "").strip())
          except:
            ram_val = 16
          hw_ram = st.number_input("RAM / Porte (GB o Num)", min_value=2, max_value=256, value=ram_val)
          
          tipo_hd_esistente = pulisci_valore(dettagli_esistenti.get("Tipo HD", "SSD"))
          if tipo_hd_esistente not in ["SSD", "HDD", "NVMe", "Altro"]:
            tipo_hd_esistente = "SSD"
            
          hw_tipo_hd = st.selectbox(
              "Tipo Memoria / Extra",
              ["SSD", "HDD", "NVMe", "Altro"],
              index=["SSD", "HDD", "NVMe", "Altro"].index(tipo_hd_esistente),
          )
          hw_cap_hd = st.text_input(
              "Capienza / Note", value=pulisci_valore(dettagli_esistenti.get("Capienza HD", ""))
          )
          hw_garanzia = st.text_input(
              "Scadenza Garanzia",
              value=pulisci_valore(dettagli_esistenti.get("Garanzia", "")),
          )

        btn_salva = st.form_submit_button("Salva Specifiche Tecniche")
        if btn_salva:
          st.session_state.hardware_dettagli[ip_scelto] = {
              "Marca": hw_marca,
              "Modello": hw_modello,
              "Processore": hw_cpu,
              "RAM": f"{hw_ram} GB",
              "Tipo HD": hw_tipo_hd,
              "Capienza HD": hw_cap_hd,
              "Garanzia": hw_garanzia,
          }
          idx_r = df_rete_sede[
              df_rete_sede["_ip_completo"] == ip_scelto
          ].index
          if not idx_r.empty and df_rete_sede.loc[idx_r[0], "Stato"] != "🔴 Occupato":
            df_rete_sede.loc[idx_r, "Stato"] = "🔴 Occupato"
            st.session_state.dataframes_rete[idx_selezionato] = df_rete_sede
          st.success(f"Specifiche salvate con successo per l'IP {scelta_mostrata}!")
          st.rerun()

  with st.expander("📁 Importa inventario da file (CSV o Excel)"):
    st.info(
        "Il file deve contenere almeno una colonna 'Indirizzo IP' e opzionalmente:"
        " 'Nome Macchina', 'Tipologia', 'Marca', 'Modello', ecc."
    )
    uploaded_file = st.file_uploader(
        "Carica file CSV o XLSX", type=["csv", "xlsx"]
    )

    if uploaded_file is not None:
      try:
        if uploaded_file.name.endswith(".csv"):
          df_import = pd.read_csv(uploaded_file)
        else:
          df_import = pd.read_excel(uploaded_file)

        if "Indirizzo IP" not in df_import.columns:
          st.error(
              "Il file caricato deve contenere una colonna denominata"
              " 'Indirizzo IP'."
          )
        else:
          if st.button("Conferma e Importa Dati"):
            count_importati = 0
            base_ip_sede = blocco_completo_ip
            prefix = f"{base_ip_sede}."
            for _, row in df_import.iterrows():
              ip_file = str(row.get("Indirizzo IP", "")).strip()

              if not ip_file.startswith(prefix):
                ip_file_completo = f"{prefix}{ip_file}"
              else:
                ip_file_completo = ip_file

              if ip_file_completo.startswith(base_ip_sede):
                nome_mac_file = pulisci_valore(row.get("Nome Macchina", ""))
                tipo_file = pulisci_valore(row.get("Tipologia", ""))

                if nome_mac_file:
                  idx_r = df_rete_sede[
                      df_rete_sede["_ip_completo"] == ip_file_completo
                  ].index
                  if not idx_r.empty:
                    df_rete_sede.loc[idx_r, "Nome Macchina"] = nome_mac_file
                    df_rete_sede.loc[idx_r, "Tipologia"] = tipo_file
                    df_rete_sede.loc[idx_r, "Stato"] = "🔴 Occupato"

                st.session_state.hardware_dettagli[ip_file_completo] = {
                    "Marca": pulisci_valore(row.get("Marca", "-")),
                    "Modello": pulisci_valore(row.get("Modello", "-")),
                    "Processore": pulisci_valore(row.get("Processore", "-")),
                    "RAM": pulisci_valore(row.get("RAM", "-")),
                    "Tipo HD": pulisci_valore(row.get("Tipo HD", "-")),
                    "Capienza HD": pulisci_valore(row.get("Capienza HD", "-")),
                    "Garanzia": pulisci_valore(row.get("Garanzia", "-")),
                }
                count_importati += 1

            st.session_state.dataframes_rete[idx_selezionato] = df_rete_sede
            st.success(
                f"Importati con successo {count_importati} dispositivi!"
            )
            st.rerun()
      except Exception as e:
        st.error(f"Errore nella lettura del file: {e}")

  st.markdown("---")
  st.write("📋 **Inventario Completo della Sede (Modificabile):**")

  lista_completa = []
  for m in df_rete_sede.to_dict("records"):
    ip_comp = m["_ip_completo"]
    dettagli = st.session_state.hardware_dettagli.get(ip_comp, {})

    nome_m = pulisci_valore(m["Nome Macchina"])
    tipo_m = pulisci_valore(m["Tipologia"])

    lista_completa.append({
        "Indirizzo IP": m["Indirizzo IP"],
        "_ip_completo": ip_comp,
        "Nome Macchina": nome_m,
        "Tipologia": tipo_m,
        "Marca": pulisci_valore(dettagli.get("Marca", "-")),
        "Modello": pulisci_valore(dettagli.get("Modello", "-")),
        "Processore": pulisci_valore(dettagli.get("Processore", "-")),
        "RAM": pulisci_valore(dettagli.get("RAM", "-")),
        "Tipo HD": pulisci_valore(dettagli.get("Tipo HD", "-")),
        "Capienza HD": pulisci_valore(dettagli.get("Capienza HD", "-")),
        "Garanzia": pulisci_valore(dettagli.get("Garanzia", "-")),
    })

  df_inventario_corrente = pd.DataFrame(lista_completa)
  df_inv_per_editor = df_inventario_corrente.drop(
      columns=["_ip_completo"], errors="ignore"
  ).copy()

  for i in range(len(df_inv_per_editor)):
    if not df_inv_per_editor.loc[i, "Nome Macchina"]:
      df_inv_per_editor.loc[i, "Tipologia"] = ""

  df_inv_per_editor = df_inv_per_editor.fillna("")

  df_inventario_modificato = st.data_editor(
      df_inv_per_editor,
      column_config={
          "Indirizzo IP": st.column_config.TextColumn(
              "Indirizzo IP", disabled=True
          ),
          "Nome Macchina": st.column_config.TextColumn("Nome Dispositivo"),
          "Tipologia": st.column_config.SelectboxColumn(
              "Tipologia",
              options=opzioni_tipologia,
              required=False
          ),
          "Marca": st.column_config.TextColumn("Marca"),
          "Modello": st.column_config.TextColumn("Modello"),
          "Processore": st.column_config.TextColumn("Processore"),
          "RAM": st.column_config.TextColumn("RAM"),
          "Tipo HD": st.column_config.TextColumn("Tipo HD"),
          "Capienza HD": st.column_config.TextColumn("Capienza HD"),
          "Garanzia": st.column_config.TextColumn("Garanzia"),
      },
      key=f"editor_inventario_{idx_selezionato}",
      use_container_width=True,
      hide_index=True,
  )

  inv_modificato = False
  for i in range(len(df_inventario_modificato)):
    ip_comp = df_inventario_corrente.loc[i, "_ip_completo"]
    nuovo_nome = pulisci_valore(df_inventario_modificato.loc[i, "Nome Macchina"])
    nuova_tipologia = pulisci_valore(df_inventario_modificato.loc[i, "Tipologia"])

    if not nuovo_nome:
      nuova_tipologia = ""

    st.session_state.hardware_dettagli[ip_comp] = {
        "Marca": pulisci_valore(df_inventario_modificato.loc[i, "Marca"]),
        "Modello": pulisci_valore(df_inventario_modificato.loc[i, "Modello"]),
        "Processore": pulisci_valore(df_inventario_modificato.loc[i, "Processore"]),
        "RAM": pulisci_valore(df_inventario_modificato.loc[i, "RAM"]),
        "Tipo HD": pulisci_valore(df_inventario_modificato.loc[i, "Tipo HD"]),
        "Capienza HD": pulisci_valore(df_inventario_modificato.loc[i, "Capienza HD"]),
        "Garanzia": pulisci_valore(df_inventario_modificato.loc[i, "Garanzia"]),
    }

    idx_r = df_rete_sede[df_rete_sede["_ip_completo"] == ip_comp].index
    if not idx_r.empty:
      vecchio_nome = str(df_rete_sede.loc[idx_r[0], "Nome Macchina"])
      vecchia_tipologia = str(df_rete_sede.loc[idx_r[0], "Tipologia"])
      if vecchio_nome != nuovo_nome or vecchia_tipologia != nuova_tipologia:
        df_rete_sede.loc[idx_r, "Nome Macchina"] = nuovo_nome
        df_rete_sede.loc[idx_r, "Tipologia"] = nuova_tipologia
        if nuovo_nome:
          df_rete_sede.loc[idx_r, "Stato"] = "🔴 Occupato"
        else:
          df_rete_sede.loc[idx_r, "Stato"] = "🟢 Libero"
        inv_modificato = True

  st.session_state.dataframes_rete[idx_selezionato] = df_rete_sede
  if inv_modificato:
    st.rerun()
