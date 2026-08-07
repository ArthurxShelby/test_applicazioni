import io
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import streamlit as st
from supabase import create_client

# Configurazione della pagina
st.set_page_config(
    page_title="Gestione Spese Condominiali", page_icon="🏢", layout="wide"
)

# --- CONFIGURAZIONE SUPABASE ---
try:
  SUPABASE_URL = st.secrets["SUPABASE_URL"]
  SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
  st.error("Configurazione Supabase mancante nei Secrets!")
  st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

APP_NAMES = ["ESPOSITO", "MARANGI", "LINCESSO", "FUSO", "PUCA", "BAVILA", "TESTA"]

# --- FUNZIONI SUPABASE ---
def carica_mq_da_supabase():
  try:
    response = supabase.table("condominio").select("*").execute()
    data = response.data
    return {row["condominio"]: float(row["mq"]) for row in data} if data else {}
  except: return {}

def carica_riporti_da_supabase():
  try:
    response = supabase.table("riporti").select("*").execute()
    data = response.data
    return {row["condominio"]: float(row["riporto"]) for row in data} if data else {app: 0.0 for app in APP_NAMES}
  except: return {app: 0.0 for app in APP_NAMES}

def carica_fatture_da_supabase():
  try:
    response = supabase.table("fatture").select("*").execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame(columns=["id", "anno", "mese", "tipo", "fornitore", "imponibile", "iva", "totale"])
  except: return pd.DataFrame()

def carica_pagamenti_da_supabase():
  try:
    response = supabase.table("pagamenti").select("*").execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()
  except: return pd.DataFrame()

# --- INIT SESSION STATE ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "mq_appartamenti" not in st.session_state: st.session_state.mq_appartamenti = carica_mq_da_supabase()
if "riporti" not in st.session_state: st.session_state.riporti = carica_riporti_da_supabase()
if "fatture" not in st.session_state: st.session_state.fatture = carica_fatture_da_supabase()
if "pagamenti" not in st.session_state: st.session_state.pagamenti = carica_pagamenti_da_supabase()

def calcola_millesimi_da_mq(mq_dict):
  tot_mq = sum(mq_dict.values())
  return {app: round((mq / tot_mq) * 1000, 2) for app, mq in mq_dict.items()} if tot_mq > 0 else {k: 0 for k in mq_dict}

# --- LOGICA APP ---
if not st.session_state.logged_in:
  st.title("🏢 Accesso Gestione Condominio")
  if st.button("Accedi"): st.session_state.logged_in = True
else:
  menu = st.sidebar.selectbox("Menu", ["Dashboard & Riepilogo", "Inserisci Fattura", "Storico"])
  
  if menu == "Dashboard & Riepilogo":
    st.title("📊 Dashboard e Riparto")
    df_fatture = st.session_state.fatture
    millesimi = calcola_millesimi_da_mq(st.session_state.mq_appartamenti)
    tot_millesimi = sum(millesimi.values())

    # --- SEZIONE GESTIONE INTROITI ---
    st.subheader("💳 Gestione Introiti e Pagamenti Utenti")
    with st.form("form_registra_pagamento"):
      col_p1, col_p2 = st.columns(2)
      with col_p1:
        condomino_selezionato = st.selectbox("Seleziona Condomino", APP_NAMES, key="reg_condomino")
        # Selezione fattura...
      with col_p2:
        importo_versato = st.number_input("Importo Pagato (€)", min_value=0.0, key="reg_importo")
        data_versamento = st.text_input("Data", value="Agosto 2026")
      
      if st.form_submit_button("Registra Pagamento"):
        # Logica inserimento (omessa per brevità, resta quella precedente)
        st.session_state.pagamenti = carica_pagamenti_da_supabase()
        st.rerun()

    # --- STORICO PAGAMENTI SINCRONIZZATO ---
    st.markdown("### Storico Pagamenti Ricevuti")
    df_pag = carica_pagamenti_da_supabase()
    
    if not df_pag.empty:
      # Checkbox per modalità filtro
      mostra_tutti = st.checkbox("Mostra storico completo", value=False)
      cond_attivo = st.session_state.reg_condomino
      
      if not mostra_tutti:
        st.write(f"Filtrato per: **{cond_attivo}**")
        df_visual = df_pag[df_pag["condominio"] == cond_attivo]
      else:
        df_visual = df_pag
        
      st.dataframe(df_visual, use_container_width=True)
    else:
      st.info("Nessun pagamento registrato.")

  elif menu == "Inserisci Fattura":
    st.title("📝 Inserisci Fattura")
    # ... form inserimento ...
