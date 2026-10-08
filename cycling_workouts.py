import streamlit as st
from datetime import datetime, date
import requests
import google.generativeai as genai

# Configurazione pagina
st.set_page_config(page_title="Smart Cycling Coach", page_icon="🚴‍♂️", layout="centered")

# Configurazione sicura API Gemini
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    elif "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception:
    pass

st.title("🚴‍♂️ Smart Cycling Coach & Intervals.icu")
st.markdown("Pianificazione intelligente degli allenamenti basata sui tuoi dati reali.")

# Recupero credenziali Intervals dallo stesso formato di uscite.py
try:
    API_KEY = st.secrets["intervals"]["api_key"]
    ATHLETE_ID = str(st.secrets["intervals"]["athlete_id"])
except Exception as e:
    st.error("Errore: Configura le credenziali di Intervals nei secrets sotto la sezione [intervals].")
    st.stop()

# Inizializzazione dello stato di sessione per mantenere i dati dell'attività
if "latest_activity" not in st.session_state:
    st.session_state.latest_activity = None

# --- SIDEBAR: PARAMETRI ATLETA ---
with st.sidebar:
    st.header("⚙ Parametri Atleta")
    age = st.number_input("Età", min_value=18, max_value=80, value=56)
    current_ftp = st.number_input("FTP attuale (W)", value=268)
    bike = st.text_input("Bici", value="Giant TCR Advanced Pro 0")
    
    st.markdown("---")
    st.markdown("### Obiettivi Settimanali")
    st.markdown("- **Mercoledì**: Medio / Soglia")
    st.markdown("- **Sabato**: Dislivello / Colli")
    st.markdown("- **Domenica**: Lungo di Resistenza")

# Selezione del giorno e modalità di input
next_workout_day = st.selectbox(
    "Per quale giorno vuoi pianificare il prossimo allenamento?",
    ["Mercoledì (Medio)", "Sabato (Dislivello)", "Domenica (Lungo)"]
)

input_mode = st.radio("Modalità recupero dati ultima uscita:", ["Sincronizza da Intervals.icu", "Inserisci dati manualmente"])

if input_mode == "Sincronizza da Intervals.icu":
    if st.button("Sincronizza Ultima Uscita", type="primary"):
        with st.spinner("Connessione a Intervals.icu in corso..."):
            try:
                url = f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}/activities"
                params = {
                    "oldest": "2025-11-15",
                    "newest": date.today().strftime("%Y-%m-%d"),
                    "iw": True
                }
                auth_data = ("API_KEY", API_KEY.strip())
                
                response = requests.get(url, auth=auth_data, params=params)
                
                if response.status_code == 200:
                    activities = response.json()
                    if activities:
                        latest = activities[0]
                        st.session_state.latest_activity = {
                            "date": latest.get("start_date_local"),
                            "name": latest.get("name"),
                            "moving_time_min": round(latest.get("moving_time", 0) / 60),
                            "distance_km": round(latest.get("distance", 0) / 1000, 1),
                            "elevation_gain": latest.get("total_elevation_gain", 0),
                            "tss": latest.get("icu_training_load", 0),
                            "avg_power": latest.get("icu_average_watts", 0),
                            "intensity_factor": latest.get("icu_intensity", 0)
                        }
                        st.success("Attività sincronizzata con successo!")
                    else:
                        st.warning("Nessuna attività trovata sul profilo Intervals.icu.")
                else:
                    st.warning(f"Errore di comunicazione (Codice HTTP {response.status_code}). Verifica le credenziali o i parametri.")
            except Exception as e:
                st.warning(f"Errore di connessione: {e}")
else:
    st.markdown("### Inserisci i dati dell'ultima uscita")
    col1, col2 = st.columns(2)
    with col1:
        dist = st.number_input("Distanza (km)", value=85.0, key="input_dist")
        durata = st.number_input("Durata (min)", value=180, key="input_durata")
        potenza = st.number_input("Potenza Media (W)", value=210, key="input_potenza")
    with col2:
        dislivello = st.number_input("Dislivello (m D+)", value=1200, key="input_dislivello")
        tss = st.number_input("TSS", value=140, key="input_tss")
    
    if st.button("Conferma Dati Uscita", type="primary"):
        st.session_state.latest_activity = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "name": "Uscita inserita manualmente",
            "moving_time_min": durata,
            "distance_km": dist,
            "elevation_gain": dislivello,
            "tss": tss,
            "avg_power": potenza,
            "intensity_factor": 0.82
        }
        st.success("Dati registrati correttamente in memoria!")

# Se abbiamo i dati dell'attività in sessione, mostriamo il riepilogo e il pulsante per l'AI
if st.session_state.latest_activity is not None:
    st.markdown("---")
    with st.expander("📊 Riepilogo dell'ultima uscita considerata", expanded=True):
        st.json(st.session_state.latest_activity)
        
    if st.button("Genera Consiglio Personalizzato con AI", type="secondary"):
        prompt = f"""
        Agisci come un coach di ciclismo professionista ed esperto di preparazione atletica.
        L'atleta ha 56 anni, pedala su una bici da corsa ({bike}) e ha una FTP di {current_ftp}W.
        
        Ecco i dati dell'ultima uscita:
        {st.session_state.latest_activity}
        
        Il prossimo allenamento pianificato che deve affrontare è per il giorno: **{next_workout_day}**.
        Struttura tipica della sua settimana:
        - Mer
