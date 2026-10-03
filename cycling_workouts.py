import streamlit as st
from datetime import datetime
import requests
import google.generativeai as genai

# Configurazione pagina
st.set_page_config(page_title="Smart Cycling Coach - Live API", page_icon="🚴‍♂️", layout="centered")

# Configurazione sicura API Gemini
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    elif "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception:
    pass

st.title("🚴‍♂️ Smart Cycling Coach (Live Intervals.icu)")
st.markdown("Integrazione diretta con i flussi dati di **Intervals.icu** per il consiglio d'allenamento mirato.")

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

# Selezione del prossimo allenamento da pianificare
next_workout_day = st.selectbox(
    "Per quale giorno vuoi pianificare il prossimo allenamento?",
    ["Mercoledì (Medio)", "Sabato (Dislivello)", "Domenica (Lungo)"]
)

# Funzione per prelevare l'ultima attività tramite API di Intervals.icu
def fetch_latest_activity_from_intervals():
    try:
        athlete_id = str(st.secrets.get("INTERVALS_ATHLETE_ID", "i519800"))
        api_key = st.secrets["INTERVALS_API_KEY"]
        
        # Gestione corretta dell'endpoint: Intervals.icu accetta l'ID atleta (es. i519800) o "self"
        url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/activities.json"
        
        # Autenticazione Basic con username fisso "API_KEY" e password la chiave API personale
        response = requests.get(url, auth=("API_KEY", api_key))
        
        # Se fallisce con l'ID specifico, proviamo in automatico con l'endpoint "self"
        if response.status_code == 404 and athlete_id != "self":
            url_fallback = "https://intervals.icu/api/v1/athlete/self/activities.json"
            response = requests.get(url_fallback, auth=("API_KEY", api_key))
        
        if response.status_code == 200:
            activities = response.json()
            if activities:
                latest = activities[0]
                return {
                    "date": latest.get("start_date_local"),
                    "name": latest.get("name"),
                    "moving_time_min": round(latest.get("moving_time", 0) / 60),
                    "distance_km": round(latest.get("distance", 0) / 1000, 1),
                    "elevation_gain": latest.get("total_elevation_gain", 0),
                    "tss": latest.get("icu_training_load", 0),
                    "avg_power": latest.get("icu_average_watts", 0),
                    "intensity_factor": latest.get("icu_intensity", 0)
                }
        else:
            st.error(f"Errore HTTP {response.status_code}: {response.text}")
        return None
    except Exception as e:
        st.error(f"Errore di connessione alle API di Intervals.icu: {e}")
        return None

if st.button("Sincronizza Ultima Uscita e Chiedi al Coach", type="primary"):
    with st.spinner("Connessione a Intervals.icu in corso..."):
        latest_activity = fetch_latest_activity_from_intervals()
        
        if latest_activity:
            st.success("Ultima attività sincronizzata con successo da Intervals.icu!")
            with st.expander("📊 Dettagli dell'ultima uscita rilevata"):
                st.json(latest_activity)
            
            with st.spinner("Il Coach AI sta elaborando il consiglio personalizzato..."):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    prompt = f"""
                    Agisci come un coach di ciclismo professionista ed esperto di preparazione atletica.
                    L'atleta ha 56 anni, pedala su una bici da corsa ({bike}) e ha una FTP di {current_ftp}W.
                    
                    Ecco i dati reali dell'ultima uscita scaricati direttamente da Intervals.icu:
                    {latest_activity}
                    
                    Il prossimo allenamento pianificato che deve affrontare è per il giorno: **{next_workout_day}**.
                    Ricorda la struttura fissa della sua settimana:
                    - Mercoledì: Medio
                    - Sabato: Dislivello
                    - Domenica: Lungo
                    
                    Compito:
                    1. Analizza lo stato di affaticamento dell'atleta in base ai carichi dell'ultima uscita (TSS, dislivello, durata).
                    2. Fornisci un consiglio dettagliato e strutturato per il prossimo allenamento ({next_workout_day}), indicando target di potenza precisi calcolati sulla sua FTP di {current_ftp}W, durata consigliata, gestione dello sforzo e percorsi idonei (es. zona Trieste/Slovenia).
                    
                    Scrivi una risposta chiara, motivante e professionale in italiano.
                    """
                    
                    response = model.generate_content(prompt)
                    
                    st.markdown("---")
                    st.subheader("💡 Analisi & Consiglio del Coach AI")
                    st.write(response.text)
                    
                except Exception as e:
                    st.error(f"Errore durante l'elaborazione con l'intelligenza artificiale: {e}")
        else:
            st.warning("Non è stato possibile recuperare le attività. Verifica che la chiave API nei secrets sia corretta.")
