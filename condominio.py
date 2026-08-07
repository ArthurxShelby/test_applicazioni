import io
import os
import pandas as pd
import streamlit as st
from supabase import create_client

# Configurazione pagina
st.set_page_config(page_title="Gestione Spese Condominiale", layout="wide")

# Connessione Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET_NAME = "fatture_pdf"

# Lista condomini (Esposito, Marangi, ecc.)
APP_NAMES = ["ESPOSITO", "MARANGI", "LINCESSO", "FUSO", "PUCA", "BAVILA", "TESTA"]

# --- FUNZIONI DI SUPPORTO ---
def carica_fatture_da_supabase():
    try:
        response = supabase.table("fatture").select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Errore nel recupero dati: {e}")
        return pd.DataFrame()

# --- INTERFACCIA PRINCIPALE ---
st.sidebar.title("Menu Principale")
menu = st.sidebar.selectbox("Seleziona Sezione", ["Dashboard & Riepilogo", "Inserisci Fattura"])

if menu == "Dashboard & Riepilogo":
    st.title("📊 Dashboard & Riepilogo Condominio")
    
    # Caricamento dati dal database
    df = carica_fatture_da_supabase()
    
    if df.empty:
        st.info("Nessuna fattura presente nel database.")
    else:
        st.subheader("Elenco Fatture Registrate")
        st.dataframe(df, use_container_width=True)
        
        # Selettore fattura specifica per anteprima o dettagli
        if "id" in df.columns:
            st.markdown("---")
            st.subheader("Seleziona Fattura Specifica")
            scelta_fattura = st.selectbox(
                "Scegli una singola fattura", 
                options=df.itertuples(), 
                format_func=lambda x: f"ID: {x.id} | {getattr(x, 'anno', '')} - {getattr(x, 'mese', '')} | {getattr(x, 'tipo', '')} | {getattr(x, 'fornitore', '')} | Tot: € {getattr(x, 'totale', 0)}"
            )
            
            if scelta_fattura:
                file_collegato = getattr(scelta_fattura, 'file', None)
                st.write(f"**File Fattura Collegato:** {file_collegato}")
                
                if file_collegato:
                    try:
                        # Generazione link pubblico o download dal bucket Supabase
                        res = supabase.storage.from_(BUCKET_NAME).get_public_url(file_collegato)
                        if res:
                            st.success(File collegato correttamente nel bucket: {file_collegato})
                    except Exception as e:
                        st.warning(f"Impossibile caricare l'anteprima dal bucket: {e}")

elif menu == "Inserisci Fattura":
    st.title("📝 Inserisci Nuova Fattura")
    
    with st.form("form_fattura_nuova"):
        col1, col2 = st.columns(2)
        with col1:
            anno = st.selectbox("Anno", options=[2025, 2026], index=1)
            mese = st.selectbox("Mese", ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"])
            tipo = st.selectbox("Tipologia Spesa", ["Energia Elettrica", "Gasolio"])
        with col2:
            fornitore = st.text_input("Fornitore")
            imponibile = st.number_input("Imponibile (€)", min_value=0.0, format="%.2f")
            iva = st.number_input("IVA (€)", min_value=0.0, format="%.2f")
        
        uploaded_file = st.file_uploader("Carica File PDF", type=["pdf"])
        submit_fat = st.form_submit_button("Salva Fattura su Supabase")

        # --- GESTIONE INVIO E UPLOAD (CON ERRORI VISIBILI) ---
        if submit_fat:
            operazione_ok = True
            nome_file_pulito = ""
            
            # 1. Tentativo Upload File su Storage
            if uploaded_file is not None:
                nome_file_pulito = uploaded_file.name.replace(" ", "_")
                try:
                    supabase.storage.from_(BUCKET_NAME).upload(
                        path=nome_file_pulito, 
                        file=uploaded_file.getvalue(), 
                        file_options={"upsert": "true"}
                    )
                    st.success(f"✅ File {nome_file_pulito} caricato con successo nello storage!")
                except Exception as e:
                    st.error(f"❌ ERRORE STORAGE: {e}")
                    operazione_ok = False
            
            # 2. Tentativo Inserimento Database (se l'upload è andato a buon fine)
            if operazione_ok:
                try:
                    nuova_fattura = {
                        "anno": int(anno), 
                        "mese": mese, 
                        "tipo": tipo, 
                        "fornitore": fornitore, 
                        "imponibile": float(imponibile), 
                        "iva": float(iva), 
                        "totale": float(imponibile + iva),
                        "file": nome_file_pulito if uploaded_file else ""
                    }
                    supabase.table("fatture").insert(nuova_fattura).execute()
                    st.success("✅ Fattura salvata correttamente nel Database!")
                except Exception as e:
                    st.error(f"❌ ERRORE DATABASE: {e}")
