import datetime
import json
import os
import pandas as pd
from supabase import create_client
import streamlit as st

st.set_page_config(
    page_title="Pianificazione Allenamento", page_icon="🏋️", layout="wide"
)

# --- 0. GESTIONE AUTENTICAZIONE E RUOLI (BLINDATURA) ---
st.sidebar.markdown("### 🔐 Accesso e Sicurezza")
ruolo_utente = st.sidebar.radio("Modalità Utente", ["Ospite (Sola Lettura)", "Proprietario / Autorizzato"])

is_proprietario = False
if ruolo_utente == "Proprietario / Autorizzato":
    password_inserita = st.sidebar.text_input("Inserisci Password di Controllo", type="password")
    password_corretta = st.secrets.get("auth", {}).get("proprietario_password", "admin123")
    if password_inserita == password_corretta:
        is_proprietario = True
        st.sidebar.success("Accesso Proprietario Autorizzato (Controllo Completo)")
    else:
        st.sidebar.error("Password errata. Modalità limitata a Ospite.")

# --- 0. GESTIONE PERSISTENZA CLOUD (SUPABASE) ---

@st.cache_resource
def init_supabase():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

def carica_database(db_iniziale):
    """Carica il database allenamenti dal cloud di Supabase, convertendo le liste in DataFrame."""
    try:
        response = supabase.table("app_data").select("payload").eq("id", 1).execute()
        if response.data and len(response.data) > 0:
            payload = response.data[0]["payload"]
            # Ricostruisce i DataFrame dai dizionari salvati
            db_ricostruito = {}
            for anno, mesi in payload.items():
                db_ricostruito[anno] = {}
                for mese, val in mesi.items():
                    if isinstance(val, list):
                        db_ricostruito[anno][mese] = pd.DataFrame(val)
                    else:
                        db_ricostruito[anno][mese] = val
            return db_ricostruito
    except Exception as e:
        st.warning(f"Impossibile connettersi al cloud per il caricamento: {e}")
    return db_iniziale

def salva_database(dati=None):
    """Salva lo stato attuale degli allenamenti nel cloud di Supabase convertendo i DataFrame in liste."""
    if not is_proprietario:
        return
    try:
        if dati is None:
            dati = st.session_state.database_allenamenti
            
        dati_serializzabili = {}
        for anno, mesi in dati.items():
            dati_serializzabili[anno] = {}
            for mese, df_val in mesi.items():
                if isinstance(df_val, pd.DataFrame):
                    dati_serializzabili[anno][mese] = df_val.to_dict(orient="records")
                else:
                    dati_serializzabili[anno][mese] = df_val
                    
        supabase.table("app_data").upsert({"id": 1, "payload": dati_serializzabili}).execute()
    except Exception as e:
        st.error(f"Errore durante il salvataggio dei dati sul cloud: {e}")

# --- 1. RIFERIMENTI FTP & SIDEBAR ---
ftp_atleta = 279

st.sidebar.markdown(f"## Riferimenti FTP ({ftp_atleta}W)")
st.sidebar.markdown(
    f"**Sweet Spot (SS):** {int(ftp_atleta * 0.88)}-{int(ftp_atleta * 0.93)}W"
)
st.sidebar.markdown(
    f"**Soglia Z4:** {int(ftp_atleta * 0.91)}-{int(ftp_atleta * 1.05)}W"
)
st.sidebar.markdown("**Cadenza Soglia:** ~90 RPM")
st.sidebar.markdown("**Cadenza SS:** ~85 RPM")

# --- 2. DATABASE INIZIALE STRUTTURATO ---
database_iniziale = {
    "2026": {
        "Gennaio": {
            "Settimana 1 (Base Invernale)": {
                "Martedì": {
                    "Esercizio": "Fondo Medio Z3: 3 x 15 min",
                    "Watt": 230,
                    "RPM": 90,
                    "Ripetizioni": 3,
                    "Lavoro_m": 15,
                    "Recupero_m": 5,
                },
                "Giovedì": {
                    "Esercizio": "Sweet Spot: 2 x 15 min",
                    "Watt": 245,
                    "RPM": 85,
                    "Ripetizioni": 2,
                    "Lavoro_m": 15,
                    "Recupero_m": 5,
                },
            }
        },
    }
}

elenco_mesi_completo = [
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
]

# Inizializzazione della memoria persistente via Supabase
if "database_allenamenti" not in st.session_state:
    st.session_state.database_allenamenti = carica_database(database_iniziale)
    if is_proprietario:
        salva_database()

st.title("🏋️ Pianificazione Allenamento per Anno Solare")

# --- 3. SELEZIONE ANNO E MESE ---
col_anno, col_mese = st.columns(2)

with col_anno:
    anno_selezionato_num = st.number_input(
        "Anno Solare Corrente:", min_value=2020, max_value=2100, value=2026, step=1
    )
    anno_selezionato = str(anno_selezionato_num)

with col_mese:
    mese_selezionato = st.selectbox("Mese Corrente:", elenco_mesi_completo)

st.markdown("---")

if anno_selezionato not in st.session_state.database_allenamenti:
    st.session_state.database_allenamenti[anno_selezionato] = {}

if mese_selezionato not in st.session_state.database_allenamenti[anno_selezionato]:
    st.session_state.database_allenamenti[anno_selezionato][mese_selezionato] = pd.DataFrame(
        columns=[
            "Settimana", "Giorno", "Esercizio / Nome", "Watt", "RPM",
            "Ripetizioni", "Lavoro (min)", "Recupero (min)",
        ]
    )

dati_correnti = st.session_state.database_allenamenti[anno_selezionato][mese_selezionato]

dati_correnti = st.session_state.database_allenamenti[anno_selezionato][mese_selezionato]

# Assicura che sia sempre un DataFrame pronto all'uso
if not isinstance(dati_correnti, pd.DataFrame):
    if isinstance(dati_correnti, list):
        df_base_mese = pd.DataFrame(dati_correnti)
    else:
        df_base_mese = pd.DataFrame(
            columns=[
                "Settimana", "Giorno", "Esercizio / Nome", "Watt",
                "RPM", "Ripetizioni", "Lavoro (min)", "Recupero (min)",
            ]
        )
    st.session_state.database_allenamenti[anno_selezionato][mese_selezionato] = df_base_mese
else:
    df_base_mese = dati_correnti

# --- 4. SEZIONE IMPORTAZIONE CSV (Riservata) ---
if is_proprietario:
    with st.expander("📂 Integra o carica piano di lavoro tramite file CSV", expanded=False):
        st.write(f"Stai caricando i dati per: **{mese_selezionato} {anno_selezionato}**.")
        file_caricato = st.file_uploader(
            "Seleziona il file CSV",
            type=["csv"],
            key=f"uploader_{anno_selezionato}_{mese_selezionato}",
        )

        if file_caricato is not None:
            try:
                df_caricato = pd.read_csv(file_caricato, sep=None, engine="python")
                df_caricato.columns = df_caricato.columns.str.strip()

                colonne_attese = [
                    "Settimana", "Giorno", "Esercizio / Nome", "Watt",
                    "RPM", "Ripetizioni", "Lavoro (min)", "Recupero (min)",
                ]

                if all(col in df_caricato.columns for col in colonne_attese):
                    st.session_state.database_allenamenti[anno_selezionato][mese_selezionato] = df_caricato[colonne_attese]
                    salva_database()
                    st.success(f"File CSV caricato e salvato permanentemente su Supabase per {mese_selezionato} {anno_selezionato}!")
                    st.rerun()
                else:
                    st.error(f"Il file CSV non contiene le colonne corrette: {colonne_attese}")
            except Exception as e:
                st.error(f"Errore nella lettura del file CSV: {e}")
else:
    st.info("ℹ️ Sezione di importazione CSV riservata al proprietario (Modalità Ospite: Sola Lettura).")

# --- 5. TABELLA INTERATTIVA DI MODIFICA ---
st.subheader(f"✍️ Gestione e Modifica Allenamenti: **{mese_selezionato} {anno_selezionato}**")

if is_proprietario:
    df_modificato = st.data_editor(
        df_base_mese,
        num_rows="dynamic",
        use_container_width=True,
        key=f"editor_{anno_selezionato}_{mese_selezionato}",
        column_config={
            "Watt": st.column_config.NumberColumn(min_value=50, max_value=500, step=1),
            "RPM": st.column_config.NumberColumn(min_value=60, max_value=120, step=1),
            "Ripetizioni": st.column_config.NumberColumn(min_value=1, max_value=20, step=1),
            "Lavoro (min)": st.column_config.NumberColumn(min_value=1, max_value=180, step=1),
            "Recupero (min)": st.column_config.NumberColumn(min_value=0, max_value=60, step=1),
        },
    )

    if not df_modificato.equals(df_base_mese):
        st.session_state.database_allenamenti[anno_selezionato][mese_selezionato] = df_modificato
        salva_database()
else:
    st.dataframe(df_base_mese, use_container_width=True)
    st.warning("⚠️ Accesso Ospite: la tabella è in sola lettura.")

st.markdown("<br>", unsafe_allow_html=True)

# --- 6. PANNELLO DI CANCELLAZIONE AVANZATO (Riservato) ---
if is_proprietario:
    with st.expander("🗑️ Pannello di Pulizia / Cancellazione Periodo (Avanzato)"):
        st.write("Seleziona un intervallo esatto basato su date specifiche per svuotare i dati.")

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            data_inizio_del = st.date_input("Data Inizio Periodo", value=datetime.date(2026, 1, 1), key="data_ini_del")
        with col_d2:
            data_fine_del = st.date_input("Data Fine Periodo", value=datetime.date(2026, 12, 31), key="data_fin_del")

        if st.button("🚨 Svuota dati per il periodo selezionato"):
            if data_inizio_del > data_fine_del:
                st.error("La data di inizio non può essere successiva alla data di fine.")
            else:
                try:
                    anno_inizio_del = data_inizio_del.year
                    anno_fine_del = data_fine_del.year
                    idx_m_ini = data_inizio_del.month - 1
                    idx_m_fin = data_fine_del.month - 1

                    for anno_target_num in range(anno_inizio_del, anno_fine_del + 1):
                        anno_target = str(anno_target_num)
                        if anno_target not in st.session_state.database_allenamenti:
                            continue

                        start_idx = idx_m_ini if anno_target_num == anno_inizio_del else 0
                        end_idx = idx_m_fin if anno_target_num == anno_fine_del else 11

                        mesi_da_pulire = elenco_mesi_completo[start_idx : end_idx + 1]

                        for m in mesi_da_pulire:
                            if m in st.session_state.database_allenamenti[anno_target]:
                                st.session_state.database_allenamenti[anno_target][m] = pd.DataFrame(
                                    columns=[
                                        "Settimana", "Giorno", "Esercizio / Nome", "Watt",
                                        "RPM", "Ripetizioni", "Lavoro (min)", "Recupero (min)",
                                    ]
                                )

                    salva_database()
                    st.success("Dati svuotati e sincronizzati con successo su Supabase!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore durante la pulizia: {e}")
else:
    with st.expander("🗑️ Pannello di Pulizia / Cancellazione Periodo (Avanzato)"):
        st.warning("⚠️ Funzione riservata esclusivamente al proprietario.")

