import io
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Gestione Spese Condominiali", page_icon="🏢", layout="wide")

# --- CONFIGURAZIONE SUPABASE DA SECRETS ---
try:
  SUPABASE_URL = (st.secrets.get("SUPABASE_URL") or st.secrets["supabase"]["SUPABASE_URL"]).strip()
  SUPABASE_KEY = (st.secrets.get("SUPABASE_KEY") or st.secrets["supabase"]["SUPABASE_KEY"]).strip()
except Exception:
  st.error("Configurazione Supabase mancante nei Secrets di Streamlit!")
  st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

APP_NAMES = ["ESPOSITO", "MARANGI", "LINCESSO", "FUSO", "PUCA", "BAVILA", "TESTA"]

# --- FUNZIONI DI SUPPORTO CON FALLBACK ---
def carica_fatture_da_supabase():
  try:
    response = supabase.table("fatture").select("*").execute()
    if response.data is not None:
      return pd.DataFrame(response.data)
  except Exception as e:
    st.error(f"Errore tabella 'fatture': {e}")
  return pd.DataFrame(columns=["id", "anno", "mese", "tipo", "fornitore", "imponibile", "iva", "totale"])

def carica_pagamenti_da_supabase():
  for nome_tabella in ["pagamenti", "pagamneti"]:
    try:
      response = supabase.table(nome_tabella).select("*").execute()
      if response.data is not None:
        return pd.DataFrame(response.data)
    except Exception:
      continue
  return pd.DataFrame(columns=["id", "condominio", "fattura_id", "data_pagamento", "importo_da_pagare", "importo_pagato", "accredito", "riporto"])

def carica_mq_da_supabase():
  try:
    response = supabase.table("condominio").select("*").execute()
    if response.data:
      return {row["condominio"]: float(row["mq"]) for row in response.data}
  except Exception:
    pass
  return {app: 75.0 for app in APP_NAMES}

def carica_riporti_da_supabase():
  try:
    response = supabase.table("riporti").select("*").execute()
    if response.data:
      return {row["condominio"]: float(row["riporto"]) for row in response.data}
  except Exception:
    pass
  return {app: 0.0 for app in APP_NAMES}

# --- STATO SESSIONE ---
if "logged_in" not in st.session_state:
  st.session_state.logged_in = False

def login_screen():
  st.title("🏢 Accesso Gestione Condominio")
  with st.form("login_form"):
    username = st.text_input("Nome Utente")
    password = st.text_input("Password", type="password")
    if st.form_submit_button("Accedi"):
      if username == "admin" and password == "condominio2026":
        st.session_state.logged_in = True
        st.rerun()
      else:
        st.error("Credenziali non valide.")

if not st.session_state.logged_in:
  login_screen()
else:
  st.sidebar.title("Menu Principale")
  menu = st.sidebar.selectbox("Seleziona Sezione", ["Dashboard & Riepilogo", "Inserisci Fattura", "Storico e Dettaglio", "Gestione Millesimi & Riporti"])
  if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

  df_fatture = carica_fatture_da_supabase()
  df_pagamenti = carica_pagamenti_da_supabase()
  mq_appartamenti = carica_mq_da_supabase()
  riporti = carica_riporti_da_supabase()

  tot_mq = sum(mq_appartamenti.values())
  millesimi = {app: round((mq / tot_mq) * 1000, 2) for app, mq in mq_appartamenti.items()} if tot_mq > 0 else {k: 0 for k in mq_appartamenti}
  tot_millesimi = sum(millesimi.values())

  if menu == "Dashboard & Riepilogo":
    st.title("📊 Dashboard e Riparto Spese")
    st.info(f"ℹ️ URL Collegato: {SUPABASE_URL}")
    
    if df_fatture.empty:
      st.warning("Nessun dato trovato nella tabella 'fatture' o errore di percorso URL.")
    else:
      st.dataframe(df_fatture, use_container_width=True)

  elif menu == "Inserisci Fattura":
    st.title("📝 Inserisci Fattura")
    with st.form("form_fattura"):
      anno = st.selectbox("Anno", [2024, 2025, 2026])
      mese = st.selectbox("Mese", ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"])
      tipo = st.selectbox("Tipologia", ["Energia Elettrica", "Gasolio"])
      fornitore = st.text_input("Fornitore")
      imponibile = st.number_input("Imponibile (€)", min_value=0.0)
      iva = st.number_input("IVA (€)", min_value=0.0)
      if st.form_submit_button("Salva"):
        supabase.table("fatture").insert({"anno": int(anno), "mese": mese, "tipo": tipo, "fornitore": fornitore, "imponibile": float(imponibile), "iva": float(iva), "totale": float(imponibile + iva)}).execute()
        st.success("Salvato!")
        st.rerun()

  elif menu == "Storico e Dettaglio":
    st.title("📂 Storico")
    st.dataframe(df_fatture, use_container_width=True)

  elif menu == "Gestione Millesimi & Riporti":
    st.title("⚙️ Gestione")
    st.write("Sezione configurazione.")
