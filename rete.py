import ipaddress
import io
import re
import pandas as pd
from fpdf import FPDF
import streamlit as st

# Configurazione della pagina
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

# Integrazione Supabase
try:
  from supabase import create_client
  SUPABASE_DISPONIBILE = True
except ImportError:
  SUPABASE_DISPONIBILE = False

# Connessione a Supabase tramite st.secrets
def get_supabase_client():
  if not SUPABASE_DISPONIBILE:
    return None
  try:
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if url and key:
      return create_client(url, key)
  except Exception:
    pass
  return None

supabase = get_supabase_client()

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

NOME_TABELLA_SUPABASE = "inventario_hardware"

def carica_dati_da_supabase():
  """Carica tutti i record dalla tabella Supabase."""
  if not supabase:
    return []
  try:
    response = supabase.table(NOME_TABELLA_SUPABASE).select("*").execute()
    if response.data:
      return response.data
  except Exception as e:
    st.warning(f"Impossibile connettersi a Supabase per il caricamento: {e}")
  return []

def salva_o_aggiorna_su_supabase(ip_completo, sede_nome, dati_hw, dati_rete):
  """Salva o aggiorna un record su Supabase includendo la gestione errori visibile."""
  if not supabase:
    st.error("⚠️ Client Supabase non disponibile! Controlla i secrets.")
    return
  try:
    payload = {
        "ip_completo": ip_completo,
        "sede": sede_nome,
        "nome_macchina": dati_rete.get("Nome Macchina", ""),
        "tipologia": dati_rete.get("Tipologia", ""),
        "stato": dati_rete.get("Stato", "🟢 Libero"),
        "marca": dati_hw.get("Marca", ""),
        "modello": dati_hw.get("Modello", ""),
        "s_o": dati_hw.get("S.O.", ""),
        "processore": dati_hw.get("Processore", ""),
        "ram": dati_hw.get("RAM", ""),
        "tipo_hd": dati_hw.get("Tipo HD", "SSD"),
        "capienza_hd": dati_hw.get("Capienza HD", ""),
        "garanzia": dati_hw.get("Garanzia", "")
    }
    
    supabase.table(NOME_TABELLA_SUPABASE).upsert(payload, on_conflict="ip_completo").execute()
  except Exception as e:
    st.error(f"❌ Errore critico salvataggio Supabase: {e}")

def elimina_da_supabase(ip_completo):
  """Elimina o ripulisce il record su Supabase quando l'IP viene liberato."""
  if not supabase:
    return
  try:
    supabase.table(NOME_TABELLA_SUPABASE).delete().eq("ip_completo", ip_completo).execute()
  except Exception as e:
    print("Errore nella cancellazione da Supabase:", e)

dati_supabase = carica_dati_da_supabase()

def pulisci_valore(val):
  if val is None or pd.isna(val):
    return ""
  s = str(val).strip()
  if s.lower() in ["none", "nan", "", "-"]:
    return ""
  return s

def estrai_marca_e_modello(testo_modello):
  testo = pulisci_valore(testo_modello)
  if not testo:
    return "", ""
  parti = testo.split(" ", 1)
  marca = parti[0]
  modello = parti[1] if len(parti) > 1 else ""
  return marca, modello

def estrai_anno(testo):
  if not testo:
    return 9999
  match = re.search(r'\b(19\d{2}|20\d{2})\b', str(testo))
  if match:
    return int(match.group(1))
  return 9999

def processa_stringa_hd(testo_capienza, tipo_hd_attuale):
  """Estrae accuratamente SSD, HDD o NVMe dalla capienza e pulisce il testo in GB."""
  cap_str = pulisci_valore(testo_capienza)
  tipo_str = pulisci_valore(tipo_hd_attuale)
  
  match_tipo = re.search(r'\b(SSD|HDD|NVMe)\b', cap_str, re.IGNORECASE)
  if match_tipo:
    trovato = match_tipo.group(1).upper()
    if not tipo_str or tipo_str == "-":
      tipo_str = trovato
    cap_str = re.sub(r'\b(SSD|HDD|NVMe)\b', '', cap_str, flags=re.IGNORECASE)
    cap_str = re.sub(r'[,;\s]+', ' ', cap_str).strip()
    cap_str = cap_str.strip(',').strip('-').strip()

  if (not tipo_str or tipo_str == "-") and cap_str:
    tipo_str = "SSD"
  elif not tipo_str or tipo_str == "-":
    tipo_str = "SSD"

  return tipo_str, cap_str

if "dataframes_rete" not in st.session_state:
  st.session_state.dataframes_rete = {}
  st.session_state.hardware_dettagli = {}

  for idx, item in enumerate(sedi_config):
    base_ip = item["blocco"].split(".")[0]
    range_ip = item["range_custom"]
    
    righe_ip = []
    for i in range_ip:
      ip_completo = f"{base_ip}.{i}"
      match_db = next((row for row in dati_supabase if row.get("ip_completo") == ip_completo), None)
      
      if match_db:
        righe_ip.append({
            "Indirizzo IP": ip_completo,
            "_ip_completo": ip_completo,
            "Nome Macchina": pulisci_valore(match_db.get("nome_macchina", "")),
            "Tipologia": pulisci_valore(match_db.get("tipologia", "")),
            "Stato": pulisci_valore(match_db.get("stato", "🔴 Occupato")),
        })
        
        db_capienza = pulisci_valore(match_db.get("capienza_hd", ""))
        db_tipo_hd = pulisci_valore(match_db.get("tipo_hd", ""))
        tipo_hd_corretto, cap_hd_corretta = processa_stringa_hd(db_capienza, db_tipo_hd)

        st.session_state.hardware_dettagli[ip_completo] = {
            "Marca": pulisci_valore(match_db.get("marca", "")),
            "Modello": pulisci_valore(match_db.get("modello", "")),
            "S.O.": pulisci_valore(match_db.get("s_o", "")),
            "Processore": pulisci_valore(match_db.get("processore", "")),
            "RAM": pulisci_valore(match_db.get("ram", "")),
            "Tipo HD": tipo_hd_corretto,
            "Capienza HD": cap_hd_corretta,
            "Garanzia": pulisci_valore(match_db.get("garanzia", "")),
        }
      else:
        righe_ip.append({
            "Indirizzo IP": ip_completo,
            "_ip_completo": ip_completo,
            "Nome Macchina": "",
            "Tipologia": "",
            "Stato": "🟢 Libero",
        })
        
    st.session_state.dataframes_rete[idx] = pd.DataFrame(righe_ip)

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

  for i in range(len(df_modificato)):
    ip_corr = df_corrente.loc[i, "_ip_completo"]
    nome_mac = pulisci_valore(df_modificato.loc[i, "Nome Macchina"])
    tipo_scelto = pulisci_valore(df_modificato.loc[i, "Tipologia"])

    if not nome_mac:
      tipo_scelto = ""

    stato_attuale = df_modificato.loc[i, "Stato"]

    if nome_mac and stato_attuale != "🔴 Occupato":
      df_modificato.loc[i, "Stato"] = "🔴 Occupato"
    elif not nome_mac and stato_attuale == "🔴 Occupato":
      df_modificato.loc[i, "Stato"] = "🟢 Libero"
      tipo_scelto = ""
      if ip_corr in st.session_state.hardware_dettagli:
        del st.session_state.hardware_dettagli[ip_corr]
      elimina_da_supabase(ip_corr)

    df_corrente.loc[i, "Nome Macchina"] = nome_mac
    df_corrente.loc[i, "Tipologia"] = tipo_scelto
    df_corrente.loc[i, "Stato"] = df_modificato.loc[i, "Stato"]

    if nome_mac:
      dettagli_esistenti = st.session_state.hardware_dettagli.get(ip_corr, {})
      salva_o_aggiorna_su_supabase(ip_corr, sede_scelta["nome"], dettagli_esistenti, df_corrente.loc[i].to_dict())

  st.session_state.dataframes_rete[idx_selezionato] = df_corrente

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
          hw_nome_macchina = st.text_input("Nome Dispositivo", value=pulisci_valore(riga_corrente_ip.get("Nome Macchina", "")))
        with col_f2:
          tipologia_esistente = pulisci_valore(riga_corrente_ip.get("Tipologia", "PC / Macchina"))
          if tipologia_esistente not in ["PC / Macchina", "Stampante", "Switch"]:
            tipologia_esistente = "PC / Macchina"
          hw_tipologia = st.selectbox("Tipologia", ["PC / Macchina", "Stampante", "Switch"], index=["PC / Macchina", "Stampante", "Switch"].index(tipologia_esistente))

        st.markdown("---")

        if tipo_dispositivo == "Smartphone":
          hw_marca = st.text_input("Marca", value=pulisci_valore(dettagli_esistenti.get("Marca", "")))
          hw_modello = st.text_input("Modello", value=pulisci_valore(dettagli_esistenti.get("Modello", "")))
          hw_so = st.text_input("S.O. (Sistema Operativo)", value=pulisci_valore(dettagli_esistenti.get("S.O.", "")))
          hw_cpu = st.text_input("Processore e anno", value=pulisci_valore(dettagli_esistenti.get("Processore", "")))
          
          ram_salvata = dettagli_esistenti.get("RAM", "16 GB")
          try:
            ram_val = int(str(ram_salvata).replace(" GB", "").strip())
          except:
            ram_val = 16
          hw_ram = st.number_input("RAM / Porte (GB)", min_value=2, max_value=256, value=ram_val)
          
          tipo_hd_esistente = pulisci_valore(dettagli_esistenti.get("Tipo HD", "SSD"))
          if tipo_hd_esistente not in ["SSD", "HDD", "NVMe"]:
            tipo_hd_esistente = "SSD"
          hw_tipo_hd = st.selectbox("Tipo Memoria", ["SSD", "HDD", "NVMe"], index=["SSD", "HDD", "NVMe"].index(tipo_hd_esistente))
          hw_cap_hd = st.text_input("Capienza / Note", value=pulisci_valore(dettagli_esistenti.get("Capienza HD", "")))
          hw_garanzia = st.text_input("Scadenza Garanzia", value=pulisci_valore(dettagli_esistenti.get("Garanzia", "")))
        else:
          col1, col2 = st.columns(2)
          with col1:
            hw_marca = st.text_input("Marca (es. Dell, HP)", value=pulisci_valore(dettagli_esistenti.get("Marca", "")))
            hw_modello = st.text_input("Modello", value=pulisci_valore(dettagli_esistenti.get("Modello", "")))
            hw_so = st.text_input("S.O. (Sistema Operativo)", value=pulisci_valore(dettagli_esistenti.get("S.O.", "")))
            hw_cpu = st.text_input("Processore e anno (es. i5 2020)", value=pulisci_valore(dettagli_esistenti.get("Processore", "")))
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
          tipo_hd_fin, cap_hd_fin = processa_stringa_hd(hw_cap_hd, hw_tipo_hd)

          dettagli_nuovi = {
              "Marca": hw_marca,
              "Modello": hw_modello,
              "S.O.": hw_so,
              "Processore": hw_cpu,
              "RAM": f"{hw_ram} GB",
              "Tipo HD": tipo_hd_fin,
              "Capienza HD": cap_hd_fin,
              "Garanzia": hw_garanzia,
          }
          st.session_state.hardware_dettagli[ip_scelto] = dettagli_nuovi

          idx_r = df_rete_sede[df_rete_sede["_ip_completo"] == ip_scelto].index
          if not idx_r.empty:
            df_rete_sede.loc[idx_r, "Nome Macchina"] = pulisci_valore(hw_nome_macchina)
            df_rete_sede.loc[idx_r, "Tipologia"] = hw_tipologia if pulisci_valore(hw_nome_macchina) else ""
            if pulisci_valore(hw_nome_macchina):
              df_rete_sede.loc[idx_r, "Stato"] = "🔴 Occupato"
            else:
              df_rete_sede.loc[idx_r, "Stato"] = "🟢 Libero"
            st.session_state.dataframes_rete[idx_selezionato] = df_rete_sede

          riga_aggiornata = df_rete_sede[df_rete_sede["_ip_completo"] == ip_scelto].iloc[0].to_dict()
          salva_o_aggiorna_su_supabase(ip_scelto, sede_scelta["nome"], dettagli_nuovi, riga_aggiornata)

          st.success(f"Dati di {scelta_mostrata} salvati su Supabase con successo!")
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
              if len(parti_ip) >= 2:
                ip_file_completo = f"{parti_ip[-2]}.{parti_ip[-1]}"
              else:
                ip_file_completo = f"{base_ip_sede}.{ip_raw}"

              if ip_file_completo.startswith(f"{base_ip_sede}."):
                nome_mac_file = pulisci_valore(row.get("Nome Dispositivo", ""))
                
                idx_r = df_rete_sede[df_rete_sede["_ip_completo"] == ip_file_completo].index
                if not idx_r.empty:
                  if nome_mac_file:
                    df_rete_sede.loc[idx_r, "Nome Macchina"] = nome_mac_file
                    df_rete_sede.loc[idx_r, "Stato"] = "🔴 Occupato"

                modello_grezzo = row.get("Modello", "")
                marca_estratta, modello_pulito = estrai_marca_e_modello(modello_grezzo)

                capienza_grezza = row.get("Capienza HD", "")
                tipo_hd_grezzo = row.get("Tipo HD", "-")
                tipo_hd_finale, capienza_finale = processa_stringa_hd(capienza_grezza, tipo_hd_grezzo)

                dettagli_imp = {
                    "Marca": marca_estratta,
                    "Modello": modello_pulito,
                    "S.O.": pulisci_valore(row.get("S.O.", "-")),
                    "Processore": pulisci_valore(row.get("Processore e anno", "-")),
                    "RAM": pulisci_valore(row.get("RAM", "-")),
                    "Tipo HD": tipo_hd_finale,
                    "Capienza HD": capienza_finale,
                    "Garanzia": pulisci_valore(row.get("Garanzia", "-")),
                }
                st.session_state.hardware_dettagli[ip_file_completo] = dettagli_imp
                
                riga_inf = df_rete_sede.loc[idx_r[0]].to_dict() if not idx_r.empty else {"Nome Macchina": nome_mac_file, "Tipologia": "PC / Macchina", "Stato": "🔴 Occupato"}
                salva_o_aggiorna_su_supabase(ip_file_completo, sede_scelta["nome"], dettagli_imp, riga_inf)
                count_importati += 1

            st.session_state.dataframes_rete[idx_selezionato] = df_rete_sede
            st.success(f"Importati e sincronizzati con Supabase {count_importati} dispositivi!")
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

    marca_val = pulisci_valore(dettagli.get("Marca", ""))
    modello_val = pulisci_valore(dettagli.get("Modello", "-"))
    if not marca_val and modello_val and modello_val != "-":
      marca_val, modello_val = estrai_marca_e_modello(modello_val)

    so_val = pulisci_valore(dettagli.get("S.O.", "-"))
    
    cap_hd_grezza = pulisci_valore(dettagli.get("Capienza HD", "-"))
    tipo_hd_grezzo = pulisci_valore(dettagli.get("Tipo HD", "-"))
    tipo_hd_val, cap_hd_val = processa_stringa_hd(cap_hd_grezza, tipo_hd_grezzo)
    
    dettagli["Tipo HD"] = tipo_hd_val
    dettagli["Capienza HD"] = cap_hd_val
    st.session_state.hardware_dettagli[ip_comp] = dettagli

    lista_completa.append({
        "Indirizzo IP": m["Indirizzo IP"],
        "_ip_completo": ip_comp,
        "Nome Macchina": nome_m,
        "Tipologia": tipo_m,
        "Stato": m["Stato"],
        "Marca": marca_val,
        "Modello": modello_val,
        "S.O.": so_val,
        "Processore e anno": proc_val,
        "RAM": pulisci_valore(dettagli.get("RAM", "-")),
        "Tipo HD": tipo_hd_val,
        "Capienza HD": cap_hd_val,
        "Garanzia": pulisci_valore(dettagli.get("Garanzia", "-")),
    })

  df_inventario_corrente = pd.DataFrame(lista_completa)

  if st.session_state.stato_ordinamento_anno.get(idx_selezionato, False):
    df_inventario_corrente["_anno_temp"] = df_inventario_corrente["Processore e anno"].apply(estrai_anno)
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
          "S.O.": st.column_config.TextColumn("S.O."),
          "Processore e anno": st.column_config.TextColumn("Processore e anno"),
          "RAM": st.column_config.TextColumn("RAM"),
          "Tipo HD": st.column_config.TextColumn("Tipo HD"),
          "Capienza HD": st.column_config.TextColumn("Capienza HD"),
          "Garanzia": st.column_config.TextColumn("Garanzia"),
      },
      key=f"editor_inventario_{idx_selezionato}",
      use_container_width=True,
      hide_index=True,
  )

  for i in range(len(df_inventario_modificato)):
    ip_corr_riga = df_inventario_modificato.loc[i, "Indirizzo IP"]
    riga_orig = df_inventario_corrente[df_inventario_corrente["Indirizzo IP"] == ip_corr_riga]
    if not riga_orig.empty:
      ip_comp = riga_orig.iloc[0]["_ip_completo"]
      nuovo_nome = pulisci_valore(df_inventario_modificato.loc[i, "Nome Macchina"])
      nuova_tipologia = pulisci_valore(df_inventario_modificato.loc[i, "Tipologia"])

      if not nuovo_nome:
        nuova_tipologia = ""

      cap_edit = pulisci_valore(df_inventario_modificato.loc[i, "Capienza HD"])
      tipo_edit = pulisci_valore(df_inventario_modificato.loc[i, "Tipo HD"])
      tipo_finale_ed, cap_finale_ed = processa_stringa_hd(cap_edit, tipo_edit)

      dettagli_agg = {
          "Marca": pulisci_valore(df_inventario_modificato.loc[i, "Marca"]),
          "Modello": pulisci_valore(df_inventario_modificato.loc[i, "Modello"]),
          "S.O.": pulisci_valore(df_inventario_modificato.loc[i, "S.O."]),
          "Processore": pulisci_valore(df_inventario_modificato.loc[i, "Processore e anno"]),
          "RAM": pulisci_valore(df_inventario_modificato.loc[i, "RAM"]),
          "Tipo HD": tipo_finale_ed,
          "Capienza HD": cap_finale_ed,
          "Garanzia": pulisci_valore(df_inventario_modificato.loc[i, "Garanzia"]),
      }
      st.session_state.hardware_dettagli[ip_comp] = dettagli_agg

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

        riga_inf_att = df_rete_sede.loc[idx_r[0]].to_dict()
        salva_o_aggiorna_su_supabase(ip_comp, sede_scelta["nome"], dettagli_agg, riga_inf_att)

  st.session_state.dataframes_rete[idx_selezionato] = df_rete_sede

  st.markdown("---")
  st.markdown(f"##### 📥 Esporta Inventario (Solo Dispositivi Occupati) - {sede_scelta['nome']}")

  lista_export_finale = []
  for m in df_rete_sede.to_dict("records"):
    ip_comp = m["_ip_completo"]
    nome_mac = pulisci_valore(m["Nome Macchina"])
    if nome_mac:
      dettagli = st.session_state.hardware_dettagli.get(ip_comp, {})
      
      tipo_hd_val = pulisci_valore(dettagli.get("Tipo HD", ""))
      cap_hd_val = pulisci_valore(dettagli.get("Capienza HD", ""))

      lista_export_finale.append({
          "Indirizzo IP": m["Indirizzo IP"],
          "Nome Dispositivo": nome_mac,
          "Tipologia": pulisci_valore(m["Tipologia"]),
          "Marca": pulisci_valore(dettagli.get("Marca", "")),
          "Modello": pulisci_valore(dettagli.get("Modello", "")),
          "S.O.": pulisci_valore(dettagli.get("S.O.", "")),
          "Processore e anno": pulisci_valore(dettagli.get("Processore", "")),
          "RAM": pulisci_valore(dettagli.get("RAM", "")),
          "Tipo HD": tipo_hd_val,
          "Capienza HD": cap_hd_val,
          "Garanzia": pulisci_valore(dettagli.get("Garanzia", "")),
      })
      
  df_export_finale = pd.DataFrame(lista_export_finale)

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
    
    headers = ["IP", "Nome Dispositivo", "Tipologia", "Marca", "Modello", "S.O.", "CPU & Anno", "RAM", "HD", "Capienza", "Garanzia"]
    col_widths = [22, 32, 26, 22, 22, 22, 22, 16, 18, 22, 23]
    
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
        pdf.cell(col_widths[1], 6, str(row["Nome Dispositivo"])[:18], 1, 0, "L")
        pdf.cell(col_widths[2], 6, str(row["Tipologia"])[:15], 1, 0, "L")
        pdf.cell(col_widths[3], 6, str(row["Marca"])[:12], 1, 0, "L")
        pdf.cell(col_widths[4], 6, str(row["Modello"])[:12], 1, 0, "L")
        pdf.cell(col_widths[5], 6, str(row["S.O."])[:12], 1, 0, "L")
        pdf.cell(col_widths[6], 6, str(row["Processore e anno"])[:12], 1, 0, "L")
        pdf.cell(col_widths[7], 6, str(row["RAM"])[:8], 1, 0, "C")
        pdf.cell(col_widths[8], 6, str(row["Tipo HD"])[:8], 1, 0, "C")
        pdf.cell(col_widths[9], 6, str(row["Capienza HD"])[:10], 1, 0, "C")
        pdf.cell(col_widths[10], 6, str(row["Garanzia"])[:12], 1, 1, "C")
      
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

  if tipo_dispositivo == "Smartphone":
    st.download_button(
        label="📊 Scarica Excel (.xlsx)",
        data=output_excel_tab.getvalue(),
        file_name=f"Inventario_Occupati_{sede_scelta['nome'].replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    st.download_button(
        label="📄 Scarica PDF (.pdf)",
        data=pdf_bytes_tab,
        file_name=f"Inventario_Occupati_{sede_scelta['nome'].replace(' ', '_')}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
  else:
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
