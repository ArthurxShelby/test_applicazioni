import io
import os
import base64
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import streamlit as st
from supabase import create_client

# Configurazione pagina
st.set_page_config(page_title="Gestione Spese", layout="wide")

# Connessione Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET_NAME = "fatture_pdf"
APP_NAMES = ["ESPOSITO", "MARANGI", "LINCESSO", "FUSO", "PUCA", "BAVILA", "TESTA"]

# --- FUNZIONI DI SUPPORTO ---
def carica_fatture_da_supabase():
    try:
        response = supabase.table("fatture").select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- INTERFACCIA ---
st.sidebar.title("Menu Principale")
menu = st.sidebar.selectbox("Seleziona Sezione", ["Dashboard & Riepilogo", "Inserisci Fattura"])

if menu == "Dashboard & Riepilogo":
    st.title("📊 Dashboard")
    df = carica_fatture_da_supabase()
    if df.empty:
        st.info("Nessuna fattura presente.")
    else:
        st.dataframe(df)

elif menu == "Inserisci Fattura":
    st.title("📝 Inserisci Nuova Fattura")
    
    with st.form("form_fattura_nuova"):
        col1, col2 = st.columns(2)
        with col1:
            anno = st.selectbox("Anno", options=[2025, 2026], index=1)
            mese = st.selectbox("Mese", ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"])
            tipo = st.selectbox("Tipologia", ["Energia Elettrica", "Gasolio"])
        with col2:
            fornitore = st.text_input("Fornitore")
            imponibile = st.number_input("Imponibile (€)", format="%.2f")
            iva = st.number_input("IVA (€)", format="%.2f")
        
        uploaded_file = st.file_uploader("Carica PDF", type=["pdf"])
        submit_fat = st.form_submit_button("Salva Fattura")

        # --- GESTIONE INVIO (NON SCOMPARE) ---
        if submit_fat:
            operazione_ok = True
            
            # 1. Upload File
            if uploaded_file is not None:
                try:
                    supabase.storage.from_(BUCKET_NAME).upload(
                        path=uploaded_file.name, 
                        file=uploaded_file.getvalue(), 
                        file_options={"upsert": "true"}
                    )
                    st.success(f"✅ File {uploaded_file.name} caricato nello storage!")
                except Exception as e:
                    st.error(f"❌ ERRORE STORAGE: {e}")
                    operazione_ok = False
            
            # 2. Inserimento Database
            if operazione_ok:
                try:
                    nuova_fattura = {
                        "anno": int(anno), "mese": mese, "tipo": tipo, "fornitore": fornitore, 
                        "imponibile": float(imponibile), "iva": float(iva), 
                        "totale": float(imponibile + iva), 
                        "file": uploaded_file.name if uploaded_file else ""
                    }
                    supabase.table("fatture").insert(nuova_fattura).execute()
                    st.success("✅ Fattura salvata con successo nel Database!")
                except Exception as e:
                    st.error(f"❌ ERRORE DATABASE: {e}")
