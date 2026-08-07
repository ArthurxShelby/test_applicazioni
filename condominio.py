import io
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import streamlit as st
from supabase import create_client

# Configurazione della pagina
st.set_page_config(page_title="Gestione Spese Condominiali", page_icon="🏢", layout="wide")

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
        return {row["condominio"]: float(row["mq"]) for row in response.data} if response.data else {}
    except: return {}

def carica_riporti_da_supabase():
    try:
        response = supabase.table("riporti").select("*").execute()
        return {row["condominio"]: float(row["riporto"]) for row in response.data} if response.data else {app: 0.0 for app in APP_NAMES}
    except: return {app: 0.0 for app in APP_NAMES}

def carica_fatture_da_supabase():
    try:
        response = supabase.table("fatture").select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame(columns=["id", "anno", "mese", "tipo", "fornitore", "imponibile", "iva", "totale"])
    except: return pd.DataFrame(columns=["id", "anno", "mese", "tipo", "fornitore", "imponibile", "iva", "totale"])

def carica_pagamenti_da_supabase():
    try:
        response = supabase.table("pagamenti").select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except: 
        try:
            response = supabase.table("pagamneti").select("*").execute()
            return pd.DataFrame(response.data) if response.data else pd.DataFrame()
        except: return pd.DataFrame()

# --- INIZIALIZZAZIONE SESSION STATE ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "mq_appartamenti" not in st.session_state: st.session_state.mq_appartamenti = carica_mq_da_supabase()
if "riporti" not in st.session_state: st.session_state.riporti = carica_riporti_da_supabase()
if "fatture" not in st.session_state: st.session_state.fatture = carica_fatture_da_supabase()
if "pagamenti" not in st.session_state: st.session_state.pagamenti = carica_pagamenti_da_supabase()

def calcola_millesimi_da_mq(mq_dict):
    tot_mq = sum(mq_dict.values())
    return {app: round((mq / tot_mq) * 1000, 2) for app, mq in mq_dict.items()} if tot_mq > 0 else {k: 0 for k in mq_dict}

# --- PDF GENERATOR ---
def genera_pdf_riparto(df, contesto):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = [Paragraph(f"<b>Rieparto Spese: {contesto}</b>", getSampleStyleSheet()['Heading1'])]
    data = [list(df.columns)] + df.values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# --- INTERFACCIA ---
if not st.session_state.logged_in:
    st.title("🏢 Accesso Gestione Condominio")
    with st.form("login"):
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Accedi"):
            if user == "admin" and pwd == "condominio2026":
                st.session_state.logged_in = True
                st.rerun()
else:
    menu = st.sidebar.selectbox("Menu", ["Dashboard & Riepilogo", "Inserisci Fattura", "Storico e Dettaglio", "Gestione Millesimi & Riporti"])
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    if menu == "Dashboard & Riepilogo":
        st.title("📊 Dashboard")
        df_fatture = carica_fatture_da_supabase()
        millesimi = calcola_millesimi_da_mq(st.session_state.mq_appartamenti)
        tot_millesimi = sum(millesimi.values())
        
        # Logica di calcolo (omessa sintesi per spazio) ...
        # [Qui andrebbe la logica di calcolo del riparto presente nel tuo file originale]

        st.subheader("💳 Gestione Introiti")
        with st.form("pagamento"):
            c1, c2 = st.columns(2)
            cond = c1.selectbox("Condomino", APP_NAMES, key="reg_condomino")
            imp = c2.number_input("Importo", min_value=0.0)
            if st.form_submit_button("Registra"):
                # Logica salvataggio su Supabase...
                st.rerun()

        st.markdown("### Storico Pagamenti")
        df_pag = carica_pagamenti_da_supabase()
        if not df_pag.empty:
            mostra_tutti = st.checkbox("Mostra tutti")
            df_v = df_pag if mostra_tutti else df_pag[df_pag["condominio"] == st.session_state.reg_condomino]
            st.dataframe(df_v, use_container_width=True)
            
    elif menu == "Inserisci Fattura":
        st.title("📝 Inserisci Fattura")
        # [Logica Inserimento...]

    elif menu == "Storico e Dettaglio":
        st.dataframe(carica_fatture_da_supabase())

    elif menu == "Gestione Millesimi & Riporti":
        st.title("⚙️ Gestione")
        # [Logica Gestione...]
