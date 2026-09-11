import ipaddress
import io
import re
import pandas as pd
from fpdf import FPDF
import streamlit as st
from supabase import create_client, Client

st.set_page_config(
    page_title="Gestione Reti e Hardware per Sede",
    page_icon="💻",
    layout="wide"
)

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

# Inizializzazione Client Supabase
@st.cache_resource
def init_supabase():
  url = st.secrets.get("SUPABASE_URL", "")
  key = st.secrets.get("SUPABASE_KEY", "")
  if url and key:
    return create_client(url, key)
  return None

supabase: Client = init_supabase()

# Funzione centralizzata e pulita per la sincronizzazione su Supabase
def salva_su_supabase(ip_comp, dati_dict):
  if supabase is None:
    return False
  try:
    payload = {
        "Indirizzo IP": ip_comp,
        "Nome Dispositivo": dati_dict.get("Nome Dispositivo") or None,
        "Tipologia": dati_dict.get("Tipologia") or None,
        "Stato": dati_dict.get("Stato") or "🟢 Libero",
        "Marca": dati_dict.get("Marca") or None,
        "Modello": dati_dict.get("Modello") or None,
        "Processore e anno": dati_dict.get("Processore") or dati_dict.get("Processore e anno") or None,
        "S.O.": dati_dict.get("S.O.") or None,
        "RAM": dati_dict.get("RAM") or None,
        "Tipo HD": dati_dict.get("Tipo HD") or None,
        "Capienza HD": dati_dict.get("Capienza HD") or None,
        "Garanzia": dati_dict.get("Garanzia") or None,
    }
    supabase.table("inventario").upsert(payload, on_conflict="Indirizzo IP").execute()
    return True
  except Exception as e:
    st.error(f"Errore sincronizzazione Supabase su IP {ip_comp}: {e}")
    return False

# Funzione per ordinare correttamente gli IP in modo numerico (compatibile con tipo inet)
def ordina_per_ip(df, colonna_ip="_ip_completo"):
  if df.empty or colonna_ip not in df.columns:
    return df
  try:
    df = df.copy()
    df["_sort_key"] = df[colonna_ip].apply(
        lambda x: ipaddress.ip_address(str(x).strip())
        if str(x).strip()
        else ipaddress.ip_address("0.0.0.0")
    )
    df = df.sort_values(by="_sort_key").drop(columns=["_sort_key"])
    return df
  except Exception:
    return df

try:
  from streamlit_javascript import st_javascript
  is_mobile_env = True
except ImportError:
  is_mobile_env = False

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
    {"id": 1, "nome": "Trieste", "blocco": "38.0", "subnet": "254.0", "range_custom": range(1, 256)},
    {"id": 2, "nome": "Sede Centrale", "blocco": "39.0", "subnet": "254.0", "range_custom": range(1, 256)},
    {"id": 3, "nome": "Monfalcone", "blocco": "86.0", "subnet": "255.0", "range_custom": range(1, 256)},
    {"id": 4, "nome": "Grado", "blocco": "168.0", "subnet": "255.0", "range_custom": range(1, 256)},
    {"id": 5, "nome": "Nogaro", "blocco": "61.0", "subnet": "255.0", "range_custom": range(1, 256)},
    {"id": 6, "nome": "Lignao", "blocco": "26.0", "subnet": "255.0", "range_custom": range(1, 256)},
    {"id": 7, "nome": "Marano", "blocco": "29.0", "subnet": "255.0", "range_custom": range(1, 256)},
    {"id": 8, "nome": "MMnn", "blocco": "66.0", "subnet": "255.0", "range_custom": range(1, 256)},
    {"id": 9, "nome": "P.nuovo", "blocco": "77.0", "subnet": "255.192", "range_custom": range(65, 127)},
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

# Inizializzazione Stati
if "dataframes_rete" not in st.session_state:
  st.session_state.dataframes_rete = {}

if "hardware_dettagli" not in st.session_state:
  st.session_state.hardware_dettagli = {}

# Caricamento dati da Supabase all'avvio
if "dati_caricati_da_supabase" not in st.session_state:
  if supabase is not None:
    try:
      response = supabase.table("inventario").select("*").execute()
      if response.data:
        for row in response.data:
          ip_db = row.get("Indirizzo IP")
          if ip_db:
            nome_db = pulisci_valore(row.get("Nome Dispositivo"))
            stato_db = "🔴 Occupato" if nome_db else (pulisci_valore(row.get("Stato")) or "🟢 Libero")
            
            st.session_state.hardware_dettagli[ip_db] = {
                "Nome Dispositivo": nome_db,
                "Tipologia": pulisci_valore(row.get("Tipologia")),
                "Stato": stato_db,
                "Marca": pulisci_valore(row.get("Marca")),
                "Modello": pulisci_valore(row.get("Modello")),
                "Processore": pulisci_valore(row.get("Processore e anno")),
                "S.O.": pulisci_valore(row.get("S.O.")),
                "RAM": pulisci_valore(row.get("RAM")),
                "Tipo HD": pulisci_valore(row.get("Tipo HD")),
                "Capienza HD": pulisci_valore(row.get("Capienza HD")),
                "Garanzia": pulisci_valore(row.get("Garanzia")),
            }
    except Exception as e:
      st.error(f"Errore di caricamento da Supabase: {e}")
  st.session_state.dati_caricati_da_supabase = True

for idx, item in enumerate(sedi_config):
  base_ip = item["blocco"].split(".")[0]
  range_ip = item["range_custom"]

  righe_ip = []
  for i in range_ip:
    # Generazione IP nel formato completo a 4 ottetti compatibile con inet
    ip_completo = f"{base_ip}.0.0.{i}"
    
    hw = st.session_state.hardware_dettagli.get(ip_completo, {})
    nome_macchina = pulisci_valore(hw.get("Nome Dispositivo", ""))
    tipologia = pulisci_valore(hw.get("Tipologia", ""))
    
    stato = "🔴 Occupato" if nome_macchina else pulisci_valore(hw.get("Stato", "🟢 Libero"))
    if not stato:
      stato = "🟢 Libero"

    righe_ip.append({
        "Indirizzo IP": ip_completo,
        "_ip_completo": ip_completo,
        "Nome Dispositivo": nome_macchina,
        "Tipologia": tipologia,
        "Stato": stato,
    })
  
  df_temp = pd.DataFrame(righe_ip)
  st.session_state.dataframes_rete[idx] = ordina_per_ip(df_temp, "_ip_completo")

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
  df_corrente["Nome Dispositivo"] = df_corrente["Nome Dispositivo"].apply(pulisci_valore)
  df_corrente["Tipologia"] = df_corrente["Tipologia"].apply(pulisci_valore)

  totale_ip = len(df_corrente)
  occupati = len(df_corrente[df_corrente["Stato"].astype(str).str.contains("Occupato")])
  liberi = totale_ip - occupati

  pc_count = len(df_corrente[df_corrente["Tipologia"] == "PC / Macchina"])
  stampanti_count = len(df_corrente[df_corrente["Tipologia"] == "Stampante"])
  switch_count = len(df_corrente[df_corrente["Tipologia"] == "Switch"])

  col_m1, col_m2, col_m3 = st.columns(3)
  col_m1.metric("Totale IP", totale_ip)
  col_m2.metric("🟢 Liberi", liberi)
  col_m3.metric("🔴 Occupati", occupati)

  st.markdown("<br>", unsafe_allow_html=True)

  col_t1, col_t2, col_t3 = st.columns(3)
  col_t1.metric("💻 PC / Macchina", pc_count)
  col_t2.metric("🖨️ Stampanti", stampanti_count)
  col_t3.metric("🖲️ Switch", switch_count)

  st.markdown("---")

  df_per_editor = df_corrente.drop(columns=["_ip_completo"], errors="ignore").copy()
  opzioni_tipologia = ["PC / Macchina", "Stampante", "Switch"]
  
  for i in range(len(df_per_editor)):
    if not df_per_editor.loc[i, "Nome Dispositivo"]:
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
          "Nome Dispositivo": st.column_config.TextColumn("Nome Dispositivo"),
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
    nome_mac = pulisci_valore(df_modificato.loc[i, "Nome Dispositivo"])
    tipo_scelto = pulisci_valore(df_modificato.loc[i, "Tipologia"])

    if not nome_mac:
      tipo_scelto = ""

    stato_attuale = "🔴 Occupato" if nome_mac else "🟢 Libero"

    if df_corrente.loc[i, "Tipologia"] != tipo_scelto or df_corrente.loc[i, "Nome Dispositivo"] != nome_mac or df_corrente.loc[i, "Stato"] != stato_attuale:
      modificato = True

    df_corrente.loc[i, "Nome Dispositivo"] = nome_mac
    df_corrente.loc[i, "Tipologia"] = tipo_scelto
    df_corrente.loc[i, "Stato"] = stato_attuale

    if ip_corr not in st.session_state.hardware_dettagli:
      st.session_state.hardware_dettagli[ip_corr] = {}
    
    st.session_state.hardware_dettagli[ip_corr]["Nome Dispositivo"] = nome_mac
    st.session_state.hardware_dettagli[ip_corr]["Tipologia"] = tipo_scelto
    st.session_state.hardware_dettagli[ip_corr]["Stato"] = stato_attuale

    if modificato:
      salva_su_supabase(ip_corr, st.session_state.hardware_dettagli[ip_corr])

  st.session_state.dataframes_rete[idx_selezionato] = df_corrente

  if modificato:
    st.rerun()

with tab_hardware:
  st.markdown(f"### 💻 Specifiche Hardware: {sede_scelta['nome']}")
  df_rete_sede = st.session_state.dataframes_rete[idx_selezionato]

  with st.expander("🛠️ Aggiungi dettagli tecnici avanzati (Manuale)", expanded=True):
    lista_tutti_ip = df_rete_sede.to_dict("records")
    ip_disponibili_mostrati = [m["Indirizzo IP"] for m in lista_tutti_ip]
    
    if ip_disponibili_mostrati:
      scelta_mostrata = st.selectbox(
          "1. Seleziona IP Dispositivo", 
          ip_disponibili_mostrati, 
          key=f"selettore_ip_{idx_selezionato}"
      )
      
      ip_scelto = [m["_ip_completo"] for m in lista_tutti_ip if m["Indirizzo IP"] == scelta_mostrata][0]
      riga_corrente_ip = [m for m in lista_tutti_ip if m["_ip_completo"] == ip_scelto][0]
      dettagli_esistenti = st.session_state.hardware_dettagli.get(ip_scelto, {})

      st.markdown("2. Inserisci e salva le specifiche")
      with st.form(key=f"form_hw_{idx_selezionato}"):
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
          hw_nome_macchina = st.text_input("Nome Dispositivo", value=pulisci_valore(riga_corrente_ip.get("Nome Dispositivo", "")))
        with col_f2:
          tipologia_esistente = pulisci_valore(riga_corrente_ip.get("Tipologia", "PC / Macchina"))
          if tipologia_esistente not in ["PC / Macchina", "Stampante", "Switch"]:
            tipologia_esistente = "PC / Macchina"
          hw_tipologia = st.selectbox("Tipologia", ["PC / Macchina", "Stampante", "Switch"], index=["PC / Macchina", "Stampante", "Switch"].index(tipologia_esistente))

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
          hw_marca = st.text_input("Marca (es. Dell, HP)", value=pulisci_valore(dettagli_esistenti.get("Marca", "")))
          hw_modello = st.text_input("Modello", value=pulisci_valore(dettagli_esistenti.get("Modello", "")))
          hw_cpu = st.text_input("Processore e anno (es. i5 2020)", value=pulisci_valore(dettagli_esistenti.get("Processore", "")))
          hw_so = st.text_input("S.O.", value=pulisci_valore(dettagli_esistenti.get("S.O.", "")))
        with col2:
          ram_salvata = dettagli_esistenti.get("RAM", "16 GB")
          try:
            ram_val = int(str(ram_salvata).replace(" GB", "").strip())
          except:
            ram_val = 16
          hw_ram = st.number_input("RAM / Porte (GB o Num)", min_value=2, max_value=256, value=ram_val)
          
          tipo_hd_esistente = pulisci_valore(dettagli_esistenti.get("Tipo HD", "SSD"))
          if tipo_hd_esistente not in ["SSD", "HDD", "NVMe"]:
            tipo_hd_esistente = "SSD"
          hw_tipo_hd = st.selectbox("Tipo Memoria / Extra", ["SSD", "HDD", "NVMe"], index=["SSD", "HDD", "NVMe"].index(tipo_hd_esistente))
          hw_cap_hd = st.text_input("Capienza / Note", value=pulisci_valore(dettagli_esistenti.get("Capienza HD", "")))
          hw_garanzia = st.text_input("Scadenza Garanzia", value=pulisci_valore(dettagli_esistenti.get("Garanzia", "")))

        btn_salva = st.form_submit_button("Salva Specifiche Tecniche e Dispositivo")
        
        if btn_salva:
          nome_salvato = pulisci_valore(hw_nome_macchina)
          stato_finale = "🔴 Occupato" if nome_salvato else "🟢 Libero"
          
          dati_salvataggio = {
              "Nome Dispositivo": nome_salvato,
              "Tipologia": hw_tipologia if nome_salvato else "",
              "Stato": stato_finale,
              "Marca": hw_marca,
              "Modello": hw_modello,
              "Processore": hw_cpu,
              "S.O.": hw_so,
              "RAM": f"{hw_ram} GB",
              "Tipo HD": hw_tipo_hd,
              "Capienza HD": hw_cap_hd,
              "Garanzia": hw_garanzia,
          }

          st.session_state.hardware_dettagli[ip_scelto] = dati_salvataggio

          idx_r = df_rete_sede[df_rete_sede["_ip_completo"] == ip_scelto].index
          if not idx_r.empty:
            df_rete_sede.loc[idx_r, "Nome Dispositivo"] = nome_salvato
            df_rete_sede.loc[idx_r, "Tipologia"] = hw_tipologia if nome_salvato else ""
            df_rete_sede.loc[idx_r, "Stato"] = stato_finale
            st.session_state.dataframes_rete[idx_selezionato] = df_rete_sede

          salva_su_supabase(ip_scelto, dati_salvataggio)

          st.success(f"Dati di {scelta_mostrata} salvati con successo!")
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
            
            for _, row in df_import.iterrows():
              ip_raw = str(row.get("Indirizzo IP", "")).strip()
              if not ip_raw:
                continue

              parti_ip = ip_raw.split(".")
              if len(parti_ip) == 4:
                ip_file_completo = ip_raw
              elif len(parti_ip) >= 2:
                ip_file_completo = f"{parti_ip[-2]}.0.0.{parti_ip[-1]}"
              else:
                ip_file_completo = f"{base_ip_sede}.0.0.{ip_raw}"

              if ip_file_completo.startswith(f"{base_ip_sede}."):
                nome_mac_file = pulisci_valore(row.get("Nome Dispositivo", ""))
                tipologia_file = pulisci_valore(row.get("Tipologia", "PC / Macchina"))
                stato_file = "🔴 Occupato" if nome_mac_file else "🟢 Libero"
                
                idx_r = df_rete_sede[df_rete_sede["_ip_completo"] == ip_file_completo].index
                if not idx_r.empty:
                  df_rete_sede.loc[idx_r, "Nome Dispositivo"] = nome_mac_file
                  df_rete_sede.loc[idx_r, "Tipologia"] = tipologia_file if nome_mac_file else ""
                  df_rete_sede.loc[idx_r, "Stato"] = stato_file

                dati_file = {
                    "Nome Dispositivo": nome_mac_file,
                    "Tipologia": tipologia_file if nome_mac_file else "",
                    "Stato": stato_file,
                    "Marca": pulisci_valore(row.get("Marca", "")),
                    "Modello": pulisci_valore(row.get("Modello", "")),
                    "Processore": pulisci_valore(row.get("Processore e anno", "")),
                    "S.O.": pulisci_valore(row.get("S.O.", "")),
                    "RAM": pulisci_valore(row.get("RAM", "")),
                    "Tipo HD": pulisci_valore(row.get("Tipo HD", "")),
                    "Capienza HD": pulisci_valore(row.get("Capienza HD", "")),
                    "Garanzia": pulisci_valore(row.get("Garanzia", "")),
                }

                st.session_state.hardware_dettagli[ip_file_completo] = dati_file
                salva_su_supabase(ip_file_completo, dati_file)

                count_importati += 1

            st.session_state.dataframes_rete[idx_selezionato] = df_rete_sede
            st.success(f"Importati con successo {count_importati} dispositivi per questa sede!")
            st.rerun()
      except Exception as e:
        st.error(f"Errore nella lettura del file: {e}")

  st.markdown("---")
  
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

    nome_m = pulisci_valore(m["Nome Dispositivo"])
    tipo_m = pulisci_valore(m["Tipologia"])
    stato_m = "🔴 Occupato" if nome_m else "🟢 Libero"
    proc_val = pulisci_valore(dettagli.get("Processore", ""))
    so_val = pulisci_valore(dettagli.get("S.O.", ""))

    lista_completa.append({
        "Indirizzo IP": m["Indirizzo IP"],
        "_ip_completo": ip_comp,
        "Nome Dispositivo": nome_m,
        "Tipologia": tipo_m,
        "Stato": stato_m,
        "Marca": pulisci_valore(dettagli.get("Marca", "")),
        "Modello": pulisci_valore(dettagli.get("Modello", "")),
        "Processore e anno": proc_val,
        "S.O.": so_val,
        "RAM": pulisci_valore(dettagli.get("RAM", "")),
        "Tipo HD": pulisci_valore(dettagli.get("Tipo HD", "")),
        "Capienza HD": pulisci_valore(dettagli.get("Capienza HD", "")),
        "Garanzia": pulisci_valore(dettagli.get("Garanzia", "")),
    })

  df_inventario_corrente = pd.DataFrame(lista_completa)
  df_inventario_corrente = ordina_per_ip(df_inventario_corrente, "_ip_completo")

  if st.session_state.stato_ordinamento_anno.get(idx_selezionato, False):
    df_inventario_corrente["_anno_temp"] = df_inventario_corrente["Processore e anno"].apply(estrai_anno)
    df_inventario_corrente = df_inventario_corrente.sort_values(by="_anno_temp", ascending=True).drop(columns=["_anno_temp"])

  df_inv_per_editor = df_inventario_corrente.drop(columns=["_ip_completo"], errors="ignore").copy()

  for i in range(len(df_inv_per_editor)):
    if not df_inv_per_editor.loc[i, "Nome Dispositivo"]:
      df_inv_per_editor.loc[i, "Tipologia"] = ""

  df_inv_per_editor = df_inv_per_editor.fillna("")

  df_inventario_modificato = st.data_editor(
      df_inv_per_editor,
      column_config={
          "Indirizzo IP": st.column_config.TextColumn("Indirizzo IP", disabled=True),
          "Nome Dispositivo": st.column_config.TextColumn("Nome Dispositivo"),
          "Tipologia": st.column_config.SelectboxColumn("Tipologia", options=opzioni_tipologia, required=False),
          "Stato": st.column_config.SelectboxColumn("Stato", options=["🟢 Libero", "🔴 Occupato"], required=True),
          "Marca": st.column_config.TextColumn("Marca"),
          "Modello": st.column_config.TextColumn("Modello"),
          "Processore e anno": st.column_config.TextColumn("Processore e anno"),
          "S.O.": st.column_config.TextColumn("S.O."),
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
      nuovo_nome = pulisci_valore(df_inventario_modificato.loc[i, "Nome Dispositivo"])
      nuova_tipologia = pulisci_valore(df_inventario_modificato.loc[i, "Tipologia"])
      
      nuovo_stato = "🔴 Occupato" if nuovo_nome else "🟢 Libero"
      if not nuovo_nome:
        nuova_tipologia = ""

      marca_v = pulisci_valore(df_inventario_modificato.loc[i, "Marca"])
      modello_v = pulisci_valore(df_inventario_modificato.loc[i, "Modello"])
      proc_v = pulisci_valore(df_inventario_modificato.loc[i, "Processore e anno"])
      so_v = pulisci_valore(df_inventario_modificato.loc[i, "S.O."])
      ram_v = pulisci_valore(df_inventario_modificato.loc[i, "RAM"])
      tipo_hd_v = pulisci_valore(df_inventario_modificato.loc[i, "Tipo HD"])
      cap_hd_v = pulisci_valore(df_inventario_modificato.loc[i, "Capienza HD"])
      gar_v = pulisci_valore(df_inventario_modificato.loc[i, "Garanzia"])

      dati_aggiornati = {
          "Nome Dispositivo": nuovo_nome,
          "Tipologia": nuova_tipologia,
          "Stato": nuovo_stato,
          "Marca": marca_v,
          "Modello": modello_v,
          "Processore": proc_v,
          "S.O.": so_v,
          "RAM": ram_v,
          "Tipo HD": tipo_hd_v,
          "Capienza HD": cap_hd_v,
          "Garanzia": gar_v,
      }

      st.session_state.hardware_dettagli[ip_comp] = dati_aggiornati

      idx_r = df_rete_sede[df_rete_sede["_ip_completo"] == ip_comp].index
      if not idx_r.empty:
        vecchio_nome = str(df_rete_sede.loc[idx_r[0], "Nome Dispositivo"])
        vecchia_tipologia = str(df_rete_sede.loc[idx_r[0], "Tipologia"])
        vecchio_stato = str(df_rete_sede.loc[idx_r[0], "Stato"])
        if vecchio_nome != nuovo_nome or vecchia_tipologia != nuova_tipologia or vecchio_stato != nuovo_stato:
          df_rete_sede.loc[idx_r, "Nome Dispositivo"] = nuovo_nome
          df_rete_sede.loc[idx_r, "Tipologia"] = nuova_tipologia
          df_rete_sede.loc[idx_r, "Stato"] = nuovo_stato
          inv_modificato = True

      salva_su_supabase(ip_comp, dati_aggiornati)

  st.session_state.dataframes_rete[idx_selezionato] = df_rete_sede
  if inv_modificato:
    st.rerun()

  st.markdown("---")
  with st.expander("⚠️ Area Pericolosa - Gestione Svuotamento Sede"):
    conferma_svuota = st.checkbox(
        "Conferma di voler eliminare tutti i dati e l'inventario di questa sede", 
        key=f"chk_svuota_{idx_selezionato}"
    )
    if st.button("🗑️ Svuota Inventario Sede", type="primary", key=f"btn_svuota_{idx_selezionato}"):
      if conferma_svuota:
        df_rete_sede["Nome Dispositivo"] = ""
        df_rete_sede["Tipologia"] = ""
        df_rete_sede["Stato"] = "🟢 Libero"
        st.session_state.dataframes_rete[idx_selezionato] = df_rete_sede

        ips_da_rimuovere = [m["_ip_completo"] for m in df_rete_sede.to_dict("records")]
        for ip_c in ips_da_rimuovere:
          if ip_c in st.session_state.hardware_dettagli:
            del st.session_state.hardware_dettagli[ip_c]
          
          salva_su_supabase(ip_c, {
              "Nome Dispositivo": "",
              "Tipologia": "",
              "Stato": "🟢 Libero",
              "Marca": "",
              "Modello": "",
              "Processore": "",
              "S.O.": "",
              "RAM": "",
              "Tipo HD": "",
              "Capienza HD": "",
              "Garanzia": ""
          })

        st.success(f"Inventario della sede '{sede_scelta['nome']}' svuotato con successo!")
        st.rerun()
      else:
        st.warning("Per favore, spunta la casella di conferma prima di procedere con la cancellazione.")

  st.markdown("---")
  st.markdown(f"##### 📥 Esporta Inventario (Solo Dispositivi Occupati) - {sede_scelta['nome']}")

  lista_export_finale = []
  for m in df_rete_sede.to_dict("records"):
    ip_comp = m["_ip_completo"]
    nome_mac = pulisci_valore(m["Nome Dispositivo"])
    if nome_mac:
      dettagli = st.session_state.hardware_dettagli.get(ip_comp, {})
      lista_export_finale.append({
          "Indirizzo IP": m["Indirizzo IP"],
          "Nome Dispositivo": nome_mac,
          "Tipologia": pulisci_valore(m["Tipologia"]),
          "Marca": pulisci_valore(dettagli.get("Marca", "")),
          "Modello": pulisci_valore(dettagli.get("Modello", "")),
          "Processore e anno": pulisci_valore(dettagli.get("Processore", "")),
          "S.O.": pulisci_valore(dettagli.get("S.O.", "")),
          "RAM": pulisci_valore(dettagli.get("RAM", "")),
          "Tipo HD": pulisci_valore(dettagli.get("Tipo HD", "")),
          "Capienza HD": pulisci_valore(dettagli.get("Capienza HD", "")),
          "Garanzia": pulisci_valore(dettagli.get("Garanzia", "")),
      })
      
  df_export_finale = pd.DataFrame(lista_export_finale)
  df_export_finale = ordina_per_ip(df_export_finale, "Indirizzo IP")

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
    
    headers = ["IP", "Nome Dispositivo", "Tipologia", "Marca", "Modello", "CPU & Anno", "S.O.", "RAM", "HD", "Capienza", "Garanzia"]
    col_widths = [28, 32, 25, 22, 22, 22, 20, 15, 18, 22, 25]
    
    pdf.set_font("helvetica", "B", 8)
    for i, h in enumerate(headers):
      pdf.cell(col_widths[i], 7, h, 1, 0, "C")
    pdf.ln()
    
    pdf.set_font("helvetica", "", 7)
    if df_data.empty:
      pdf.cell(sum(col_widths), 10, "Nessun dispositivo occupato presente in questa sede.", 1, 1, "C")
    else:
      for _, row in df_data.iterrows():
        pdf.cell(col_widths[0], 6, str(row["Indirizzo IP"]), 1, 0, "C")
        pdf.cell(col_widths[1], 6, str(row["Nome Dispositivo"])[:20], 1, 0, "L")
        pdf.cell(col_widths[2], 6, str(row["Tipologia"])[:18], 1, 0, "L")
        pdf.cell(col_widths[3], 6, str(row["Marca"])[:15], 1, 0, "L")
        pdf.cell(col_widths[4], 6, str(row["Modello"])[:15], 1, 0, "L")
        pdf.cell(col_widths[5], 6, str(row["Processore e anno"])[:15], 1, 0, "L")
        pdf.cell(col_widths[6], 6, str(row["S.O."])[:15], 1, 0, "L")
        pdf.cell(col_widths[7], 6, str(row["RAM"])[:10], 1, 0, "C")
        pdf.cell(col_widths[8], 6, str(row["Tipo HD"])[:10], 1, 0, "C")
        pdf.cell(col_widths[9], 6, str(row["Capienza HD"])[:12], 1, 0, "C")
        pdf.cell(col_widths[10], 6, str(row["Garanzia"])[:15], 1, 1, "C")
      
    raw_pdf = pdf.output()
    if isinstance(raw_pdf, (bytearray, bytes)):
      return bytes(raw_pdf)
    return str(raw_pdf).encode("latin1")

  output_excel_tab = io.BytesIO()
  with pd.ExcelWriter(output_excel_tab, engine="openpyxl") as writer:
    df_export_finale.to_excel(writer, index=False, sheet_name="Inventario Occupati")

  try:
    pdf_bytes_tab = genera_pdf_tab(df_export_finale)
  except Exception as e:
    pdf_bytes_tab = b""

  col_btn1, col_btn2 = st.columns(2)
  with col_btn1:
    st.download_button(
        label="📊 Scarica Occupati in Excel (.xlsx)",
        data=output_excel_tab.getvalue(),
        file_name=f"Inventario_Occupati_{sede_scelta['nome'].replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
  with col_btn2:
    st.download_button(
        label="📄 Scarica Occupati in PDF (.pdf)",
        data=pdf_bytes_tab,
        file_name=f"Inventario_Occupati_{sede_scelta['nome'].replace(' ', '_')}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
