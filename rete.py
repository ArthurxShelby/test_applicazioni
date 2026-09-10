import ipaddress
import io
import re
import pandas as pd
from fpdf import FPDF
import streamlit as st

# 1. Configurazione della pagina a tutto schermo per PC e dispositivi larghi
st.set_page_config(
    page_title="Gestione Reti e Hardware per Sede",
    page_icon="💻",
    layout="wide"  # <--- Espande la pagina a tutto schermo
)

# 2. CSS personalizzato per eliminare i limiti di larghezza del contenitore e allargare le tabelle
st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 3rem;
        padding-right: 3rem;
        max-width: 100% !important;
    }
    div[data-testid="stDataEditor"] {
        width: 100% !important;
    }
    </style>
""", unsafe_allow_html=True)

# (Opzionale per rilevamento mobile avanzato)
try:
  from streamlit_javascript import st_javascript
  is_mobile_env = True
except ImportError:
  is_mobile_env = False

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

# Rilevamento automatico del tipo di dispositivo basato su larghezza schermo
tipo_dispositivo = "PC / Desktop"
if is_mobile_env:
  try:
    screen_width = st_javascript("window.innerWidth")
    if screen_width and isinstance(screen_width, (int, float)):
      if screen_width < 768:
        tipo_dispositivo = "Smartphone"
      elif 768 <= screen_width < 1024:
        tipo_dispositivo = "Tablet"
  except:
    pass

st.subheader("Gestione Reti e Hardware per Sede")
st.caption(f"💻 Dispositivo rilevato: **{tipo_dispositivo}**")

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

def estrai_anno(testo):
  if not testo:
    return 9999
  match = re.search(r'\b(19\d{2}|20\d{2})\b', str(testo))
  if match:
    return int(match.group(1))
  return 9999

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

if "stato_ordinamento_anno" not in st.session_state:
  st.session_state.stato_ordinamento_anno = {}

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
  occupati = len(df_corrente[df_corrente["Stato"].astype(str).str.contains("Occupato")])
  liberi = totale_ip - occupati

  if tipo_dispositivo == "Smartphone":
    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Totale IP", totale_ip)
    col_m2.metric("🟢 Liberi", liberi)
    st.metric("🔴 Occupati", occupati)
  else:
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Totale IP", totale_ip)
    col_m2.metric("🟢 Liberi", liberi)
    col_m3.metric("🔴 Occupati", occupati)

  st.markdown("---")

  df_per_editor = df_corrente.drop(columns=["_ip_completo"], errors="ignore").copy()
  opzioni_tipologia = ["PC / Macchina", "Stampante", "Switch", "Altro"]
  
  for i in range(len(df_per_editor)):
    if not df_per_editor.loc[i, "Nome Macchina"]:
      df_per_editor.loc[i, "Tipologia"] = ""
    else:
      val_t = str(df_per_editor.loc[i, "Tipologia"])
      if val_t not in opzioni_tipologia and val_t != "":
        df_per_editor.loc[i, "Tipologia"] = "PC / Macchina"

  df_per_editor = df_per_editor.fillna("")

  df_modificato = st.data_editor(
      df_per_editor,
      column_config={
          "Indirizzo IP": st.column_config.TextColumn("Indirizzo IP", disabled=True),
          "Nome Macchina": st.column_config.TextColumn("Nome Dispositivo"),
          "Tipologia": st.column_config.SelectboxColumn("Tipologia", options=opzioni_tipologia, required=False),
          "Stato": st.column_config.SelectboxColumn("Stato", options=["🟢 Libero", "🔴 Occupato"], required=True),
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

  with st.expander("🛠️ Aggiungi dettagli tecnici avanzati (Manuale)", expanded=(tipo_dispositivo == "PC / Desktop")):
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

        dettagli_esistenti = st.session_state.hardware_dettagli.get(ip_scelto, {})

        if tipo_dispositivo == "Smartphone":
          hw_marca = st.text_input("Marca", value=pulisci_valore(dettagli_esistenti.get("Marca", "")))
          hw_modello = st.text_input("Modello", value=pulisci_valore(dettagli_esistenti.get("Modello", "")))
          hw_cpu = st.text_input("Processore e Anno", value=pulisci_valore(dettagli_esistenti.get("Processore", "")))
          
          ram_salvata = dettagli_esistenti.get("RAM", "16 GB")
          try:
            ram_val = int(str(ram_salvata).replace(" GB", "").strip())
          except:
            ram_val = 16
          hw_ram = st.number_input("RAM / Porte (GB)", min_value=2, max_value=256, value=ram_val)
          
          tipo_hd_esistente = pulisci_valore(dettagli_esistenti.get("Tipo HD", "SSD"))
          if tipo_hd_esistente not in ["SSD", "HDD", "NVMe", "Altro"]:
            tipo_hd_esistente = "SSD"
          hw_tipo_hd = st.selectbox("Tipo Memoria", ["SSD", "HDD", "NVMe", "Altro"], index=["SSD", "HDD", "NVMe", "Altro"].index(tipo_hd_esistente))
          hw_cap_hd = st.text_input("Capienza / Note", value=pulisci_valore(dettagli_esistenti.get("Capienza HD", "")))
          hw_garanzia = st.text_input("Scadenza Garanzia", value=pulisci_valore(dettagli_esistenti.get("Garanzia", "")))
        else:
          col1, col2 = st.columns(2)
          with col1:
            hw_marca = st.text_input("Marca (es. Dell, HP, Cisco)", value=pulisci_valore(dettagli_esistenti.get("Marca", "")))
            hw_modello = st.text_input("Modello", value=pulisci_valore(dettagli_esistenti.get("Modello", "")))
            hw_cpu = st.text_input("Processore e Anno (es. Intel i5 2020)", value=pulisci_valore(dettagli_esistenti.get("Processore", "")))
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
            hw_tipo_hd = st.selectbox("Tipo Memoria / Extra", ["SSD", "HDD", "NVMe", "Altro"], index=["SSD", "HDD", "NVMe", "Altro"].index(tipo_hd_esistente))
            hw_cap_hd = st.text_input("Capienza / Note", value=pulisci_valore(dettagli_esistenti.get("Capienza HD", "")))
            hw_garanzia = st.text_input("Scadenza Garanzia", value=pulisci_valore(dettagli_esistenti.get("Garanzia", "")))

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
          idx_r = df_rete_sede[df_rete_sede["_ip_completo"] == ip_scelto].index
          if not idx_r.empty and df_rete_sede.loc[idx_r[0], "Stato"] != "🔴 Occupato":
            df_rete_sede.loc[idx_r, "Stato"] = "🔴 Occupato"
            st.session_state.dataframes_rete[idx_selezionato] = df_rete_sede
          st.success(f"Specifiche salvate con successo per l'IP {scelta_mostrata}!")
          st.rerun()

  with st.expander("📁 Importa inventario da file (CSV o Excel)"):
    uploaded_file = st.file_uploader("Carica file CSV o XLSX", type=["csv", "xlsx"])
    if uploaded_file is not None:
      try:
        if uploaded_file.name.endswith(".csv"):
          df_import = pd.read_csv(uploaded_file)
        else:
          df_import = pd.read_excel(uploaded_file)

        if "Indirizzo IP" not in df_import.columns:
          st.error("Il file caricato deve contenere una colonna 'Indirizzo IP'.")
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
                  idx_r = df_rete_sede[df_rete_sede["_ip_completo"] == ip_file_completo].index
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
            st.success(f"Importati con successo {count_importati} dispositivi!")
            st.rerun()
      except Exception as e:
        st.error(f"Errore nella lettura del file: {e}")

  st.markdown("---")
  
  if tipo_dispositivo == "Smartphone":
    st.markdown(f"📋 **Inventario Sede**")
    ordinato_attivo = st.session_state.stato_ordinamento_anno.get(idx_selezionato, False)
    label_btn = "🔄 Annulla Ordine Anno" if ordinato_attivo else "📅 Ordina per Anno"
    if st.button(label_btn, use_container_width=True):
      st.session_state.stato_ordinamento_anno[idx_selezionato] = not ordinato_attivo
      st.rerun()
  else:
    col_tit_inv, col_btn_ord = st.columns([3, 1])
    with col_tit_inv:
      st.markdown(f"📋 **Inventario Completo della Sede (Modificabile)**")
    with col_btn_ord:
      ordinato_attivo = st.session_state.stato_ordinamento_anno.get(idx_selezionato, False)
      label_btn = "🔄 Riordina per Anno (Attivo)" if ordinato_attivo else "📅 Ordina per Anno"
      if st.button(label_btn, use_container_width=True):
        st.session_state.stato_ordinamento_anno[idx_selezionato] = not ordinato_attivo
        st.rerun()

  lista_completa = []
  for m in df_rete_sede.to_dict("records"):
    ip_comp = m["_ip_completo"]
    dettagli = st.session_state.hardware_dettagli.get(ip_comp, {})

    nome_m = pulisci_valore(m["Nome Macchina"])
    tipo_m = pulisci_valore(m["Tipologia"])
    proc_val = pulisci_valore(dettagli.get("Processore", "-"))

    lista_completa.append({
        "Indirizzo IP": m["Indirizzo IP"],
        "_ip_completo": ip_comp,
        "Nome Macchina": nome_m,
        "Tipologia": tipo_m,
        "Stato": m["Stato"],
        "Marca": pulisci_valore(dettagli.get("Marca", "-")),
        "Modello": pulisci_valore(dettagli.get("Modello", "-")),
        "Processore": proc_val,
        "RAM": pulisci_valore(dettagli.get("RAM", "-")),
        "Tipo HD": pulisci_valore(dettagli.get("Tipo HD", "-")),
        "Capienza HD": pulisci_valore(dettagli.get("Capienza HD", "-")),
        "Garanzia": pulisci_valore(dettagli.get("Garanzia", "-")),
    })

  df_inventario_corrente = pd.DataFrame(lista_completa)

  if st.session_state.stato_ordinamento_anno.get(idx_selezionato, False):
    df_inventario_corrente["_anno_temp"] = df_inventario_corrente["Processore"].apply(estrai_anno)
    df_inventario_corrente = df_inventario_corrente.sort_values(by="_anno_temp", ascending=True).drop(columns=["_anno_temp"])

  df_inv_per_editor = df_inventario_corrente.drop(columns=["_ip_completo"], errors="ignore").copy()

  for i in range(len(df_inv_per_editor)):
    if not df_inv_per_editor.loc[i, "Nome Macchina"]:
      df_inv_per_editor.loc[i, "Tipologia"] = ""

  df_inv_per_editor = df_inv_per_editor.fillna("")

  df_inventario_modificato = st.data_editor(
      df_inv_per_editor,
      column_config={
          "Indirizzo IP": st.column_config.TextColumn("Indirizzo IP", disabled=True),
          "Nome Macchina": st.column_config.TextColumn("Nome Dispositivo"),
          "Tipologia": st.column_config.SelectboxColumn("Tipologia", options=opzioni_tipologia, required=False),
          "Stato": st.column_config.SelectboxColumn("Stato", options=["🟢 Libero", "🔴 Occupato"], required=True),
          "Marca": st.column_config.TextColumn("Marca"),
          "Modello": st.column_config.TextColumn("Modello"),
          "Processore": st.column_config.TextColumn("Processore e Anno"),
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
    ip_corr_riga = df_inventario_modificato.loc[i, "Indirizzo IP"]
    riga_orig = df_inventario_corrente[df_inventario_corrente["Indirizzo IP"] == ip_corr_riga]
    if not riga_orig.empty:
      ip_comp = riga_orig.iloc[0]["_ip_completo"]
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

  # --- PULSANTI DI ESPORTAZIONE ---
  st.markdown("---")
  st.markdown(f"##### 📥 Esporta Inventario (Solo Dispositivi Occupati) - {sede_scelta['nome']}")

  lista_export_finale = []
  for m in df_rete_sede.to_dict("records"):
    ip_comp = m["_ip_completo"]
    nome_mac = pulisci_valore(m["Nome Macchina"])
    if nome_mac:
      dettagli = st.session_state.hardware_dettagli.get(ip_comp, {})
      lista_export_finale.append({
          "Indirizzo IP": m["Indirizzo IP"],
          "Nome Macchina": nome_mac,
          "Tipologia": pulisci_valore(m["Tipologia"]),
          "Marca": pulisci_valore(dettagli.get("Marca", "")),
          "Modello": pulisci_valore(dettagli.get("Modello", "")),
          "Processore": pulisci_valore(dettagli.get("Processore", "")),
          "RAM": pulisci_valore(dettagli.get("RAM", "")),
          "Tipo HD": pulisci_valore(dettagli.get("Tipo HD", "")),
          "Capienza HD": pulisci_valore(dettagli.get("Capienza HD", "")),
          "Garanzia": pulisci_valore(dettagli.get("Garanzia", "")),
      })
      
  df_export_finale = pd.DataFrame(lista_export_finale)

  if tipo_dispositivo == "Smartphone":
    output_excel_tab = io.BytesIO()
    with pd.ExcelWriter(output_excel_tab, engine="openpyxl") as writer:
      df_export_finale.to_excel(writer, index=False, sheet_name="Inventario Occupati")
    
    st.download_button(
        label="📊 Scarica Excel (.xlsx)",
        data=output_excel_tab.getvalue(),
        file_name=f"Inventario_Occupati_{sede_scelta['nome'].replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
  else:
    # Ripristinati entrambi i pulsanti (Excel e PDF affiancati su PC)
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
      output_excel_tab = io.BytesIO()
      with pd.ExcelWriter(output_excel_tab, engine="openpyxl") as writer:
        df_export_finale.to_excel(writer, index=False, sheet_name="Inventario Occupati")
      st.download_button(
          label="📊 Scarica Occupati in Excel (.xlsx)",
          data=output_excel_tab.getvalue(),
          file_name=f"Inventario_Occupati_{sede_scelta['nome'].replace(' ', '_')}.xlsx",
          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          use_container_width=True,
      )
    with col_btn2:
      class PDFReportTab(FPDF):
        def header(self):
          self.set_font("helvetica", "B", 10)
          self.cell(0, 10, f"Inventario Hardware Occupati - Sede: {sede_scelta['nome']}", 0, 1, "C")
          self.ln(3)

        def footer(self):
          self.set_y(-15)
          self.set_font("helvetica", "I", 8)
          self.cell(0, 10, f"Pagina {self.page_no()}", 0, 0, "C")

      def genera_pdf_tab(df_data):
        pdf = PDFReportTab(orientation="L", unit="mm", format="A4")
        pdf.add_page()
        pdf.set_font("helvetica", "", 8)
        
        headers = ["IP", "Nome", "Tipologia", "Marca", "Modello", "CPU & Anno", "RAM", "HD", "Capienza", "Garanzia"]
        col_widths = [25, 35, 30, 25, 25, 25, 18, 20, 25, 27]
        
        pdf.set_font("helvetica", "B", 8)
        for i, h in enumerate(headers):
          pdf.cell(col_widths[i], 7, h, 1, 0, "C")
        pdf.ln()
        
        pdf.set_font("helvetica", "", 7)
        for _, row in df_data.iterrows():
          pdf.cell(col_widths[0], 6, str(row["Indirizzo IP"]), 1, 0, "C")
          pdf.cell(col_widths[1], 6, str(row["Nome Macchina"])[:20], 1, 0, "L")
          pdf.cell(col_widths[2], 6, str(row["Tipologia"])[:18], 1, 0, "L")
          pdf.cell(col_widths[3], 6, str(row["Marca"])[:15], 1, 0, "L")
          pdf.cell(col_widths[4], 6, str(row["Modello"])[:15], 1, 0, "L")
          pdf.cell(col_widths[5], 6, str(row["Processore"])[:15], 1, 0, "L")
          pdf.cell(col_widths[6], 6, str(row["RAM"])[:10], 1, 0, "C")
          pdf.cell(col_widths[7], 6, str(row["Tipo HD"])[:10], 1, 0, "C")
          pdf.cell(col_widths[8], 6, str(row["Capienza HD"])[:12], 1, 0, "C")
          pdf.cell(col_widths[9], 6, str(row["Garanzia"])[:15], 1, 1, "C")
          
        raw_pdf = pdf.output()
        if isinstance(raw_pdf, (bytearray, bytes)):
          return bytes(raw_pdf)
        return str(raw_pdf).encode("latin1")

      try:
        if not df_export_finale.empty:
          pdf_bytes_tab = genera_pdf_tab(df_export_finale)
          st.download_button(
              label="📄 Scarica Occupati in PDF (.pdf)",
              data=pdf_bytes_tab,
              file_name=f"Inventario_Occupati_{sede_scelta['nome'].replace(' ', '_')}.pdf",
              mime="application/pdf",
              use_container_width=True,
          )
      except Exception as e:
        st.error(f"Errore nella generazione del PDF: {e}")
