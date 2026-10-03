import streamlit as st
from datetime import datetime
import google.generativeai as genai

# Configurazione pagina
st.set_page_config(page_title="Smart Cycling Coach - Piano Definitivo", page_icon="🚴‍♂️", layout="centered")

# Configurazione sicura API Gemini
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    elif "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception:
    pass

st.title("🚴‍♂️ Smart Cycling Coach (AI Advisor)")
st.markdown("Carica il report della tua ultima uscita da **Intervals.icu** per ricevere l'analisi e il consiglio sul prossimo allenamento (Mercoledì: Medio | Sabato: Dislivello | Domenica: Lungo).")

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

# --- CORPO PRINCIPALE ---
uploaded_file = st.file_uploader("Carica il file PDF o lo screenshot del report", type=["pdf", "png", "jpg", "jpeg"])

# Selezione del prossimo allenamento da pianificare
next_workout_day = st.selectbox(
    "Per quale giorno vuoi pianificare il prossimo allenamento?",
    ["Mercoledì (Medio)", "Sabato (Dislivello)", "Domenica (Lungo)"]
)

if uploaded_file is not None:
    if st.button("Analizza Attività e Consiglia Allenamento", type="primary"):
        with st.spinner("Il Coach AI sta analizzando i dati di Intervals.icu..."):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                file_bytes = uploaded_file.getvalue()
                mime_type = uploaded_file.type
                
                file_part = {
                    "mime_type": mime_type,
                    "data": file_bytes
                }
                
                prompt = f"""
                Agisci come un coach di ciclismo professionista ed esperto di preparazione atletica.
                L'atleta ha 56 anni, pedala su una bici da corsa (Giant TCR Advanced Pro 0) e ha una FTP di {current_ftp}W.
                
                Ha appena completato un'uscita di cui allego il report (PDF o immagine da Intervals.icu).
                
                Il prossimo allenamento pianificato che deve affrontare è per il giorno: **{next_workout_day}**.
                Ricorda la struttura fissa della sua settimana:
                - Mercoledì: Medio
                - Sabato: Dislivello
                - Domenica: Lungo
                
                Compito:
                1. Estrai e riassumi brevemente i dati chiave dell'uscita appena fatta (Durata, TSS, Potenza Media, IF, ecc.).
                2. Valuta lo stato di affaticamento dell'atleta in base ai carichi rilevati.
                3. Fornisci un consiglio dettagliato e strutturato per il prossimo allenamento ({next_workout_day}), indicando target di potenza precisi calcolati sulla sua FTP di {current_ftp}W, durata consigliata, gestione dello sforzo e percorsi idonei (es. zona Trieste/Slovenia se applicabile).
                
                Scrivi una risposta chiara, motivante e professionale in italiano.
                """
                
                response = model.generate_content([file_part, prompt])
                
                st.markdown("---")
                st.subheader("💡 Analisi & Consiglio del Coach AI")
                st.write(response.text)
                
            except Exception as e:
                st.error(f"Errore durante l'elaborazione con l'intelligenza artificiale: {e}")
else:
    st.info("Carica un file PDF o un'immagine nella sezione sopra per iniziare.")
