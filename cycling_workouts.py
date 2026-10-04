import streamlit as st
from datetime import datetime
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
    # Recupero sicuro dei secret se presenti, altrimenti fallback vuoto
    try:
        default_api_key = st.secrets.get("INTERVALS_API_KEY", "")
    except Exception:
        default_api_key = ""
        
    try:
        default_athlete_id = str(st.secrets.get("INTERVALS_ATHLETE_ID", "i519800"))
    except Exception:
        default_athlete_id = "i519800"

    if not default_api_key:
        st.warning("⚠️ Chiave API di Intervals.icu non rilevata nei secrets. Inseriscila qui sotto:")
        api_key_input = st.text_input("API Key Intervals.icu", type="password")
        athlete_id_input = st.text_input("Athlete ID", value=default_athlete_id)
    else:
        api_key_input = default_api_key
        athlete_id_input = default_athlete_id

    if st.button("Sincronizza Ultima Uscita", type="primary"):
        if not api_key_input:
            st.error("Inserisci una chiave API valida per continuare.")
        else:
            with st.spinner("Connessione a Intervals.icu in corso..."):
                try:
                    url = f"https://intervals.icu/api/v1/athlete/{athlete_id_input}/activities.json"
                    response = requests.get(url, auth=("API_KEY", api_key_input))
                    
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
                        st.warning(f"Errore di comunicazione (Codice HTTP {response.status_code}). Verifica ID e chiave API.")
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
        with st.spinner("Il Coach AI sta analizzando i tuoi carichi..."):
            prompt = f"""
            Agisci come un coach di ciclismo professionista ed esperto di preparazione atletica.
            L'atleta ha 56 anni, pedala su una bici da corsa ({bike}) e ha una FTP di {current_ftp}W.
            
            Ecco i dati dell'ultima uscita:
            {st.session_state.latest_activity}
            
            Il prossimo allenamento pianificato che deve affrontare è per il giorno: **{next_workout_day}**.
            Struttura tipica della sua settimana:
            - Mercoledì: Medio / Soglia (es. lavori su salite come San Servolo o simili in zona Trieste/Slovenia)
            - Sabato: Dislivello / Colli
            - Domenica: Lungo di Resistenza
            
            Compito:
            1. Analizza lo stato di recupero e carico dell'atleta in base all'uscita effettuata.
            2. Fornisci un piano di allenamento dettagliato per **{next_workout_day}**, specificando target di potenza precisi basati sulla FTP di {current_ftp}W, durata, ripetute o gestione dello sforzo, e suggerimenti sul percorso ideale (es. zona Trieste / Slovenia).
            
            Scrivi una risposta chiara, professionale e motivante in italiano.
            """
            
            ai_response = None
            last_error = None
            
            try:
                supported_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                
                for m_name in supported_models:
                    try:
                        clean_name = m_name.replace("models/", "")
                        model = genai.GenerativeModel(clean_name)
                        ai_response = model.generate_content(prompt)
                        if ai_response and ai_response.text:
                            break
                    except Exception as ex:
                        last_error = ex
                        continue
            except Exception as e:
                last_error = e
            
            if ai_response and ai_response.text:
                st.markdown("---")
                st.subheader("💡 Analisi & Consiglio del Coach AI")
                st.write(ai_response.text)
            else:
                st.error(f"Impossibile trovare un modello compatibile o generare la risposta. Dettaglio errore: {last_error}")
