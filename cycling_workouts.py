import streamlit as st
from supabase import create_client
from datetime import datetime, timedelta
import io
import json
import google.generativeai as genai

# Configurazione pagina
st.set_page_config(page_title="Smart Adaptive Cycling Coach", page_icon="🚴‍♂️", layout="wide")

# Configurazione sicura API Gemini
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    elif "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception:
    pass

# Connessione Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

st.title("🚴‍♂️ Smart Adaptive Cycling Coach (Piano B)")
st.markdown("Pianificazione intelligente e adattiva basata sui tuoi dati reali da Intervals.icu.")

# --- SIDEBAR: PARAMETRI E CREAZIONE PIANO ---
with st.sidebar:
    st.header("⚙ Parametri Atleta")
    age = st.number_input("Età", min_value=18, max_value=80, value=56)
    current_ftp = st.number_input("FTP attuale (W)", value=268)
    
    st.markdown("---")
    st.header("📅 Genera Piano Base")
    start_date = st.date_input("Data inizio (Lunedì di riferimento)", value=datetime.today())
    num_weeks = st.slider("Numero di settimane", min_value=1, max_value=6, value=4)
    
    if st.button("Crea / Resetta Piano Base", type="primary"):
        try:
            # Svuota tabella esistente
            supabase.table("cycling_training_plans").delete().neq("id", 0).execute()
            
            generated_data = []
            current_monday = start_date - timedelta(days=start_date.weekday())
            
            for week in range(1, num_weeks + 1):
                week_start = current_monday + timedelta(weeks=week - 1)
                
                # Definizione dei 3 giorni fissi richiesti:
                # Mercoledì (indice 2) -> Medio
                # Sabato (indice 5) -> Uscita con Dislivello
                # Domenica (indice 6) -> Lungo
                workouts_template = [
                    {
                        "day_index": 2, 
                        "day_name": "Mercoledì", 
                        "type": "Medio", 
                        "desc": f"Lavoro al medio (Z3 / Sweet Spot, target ~{round(current_ftp*0.85)}W), ritmo costante per costruire resistenza.", 
                        "dur": 120, 
                        "zone": "Z3 / Medio"
                    },
                    {
                        "day_index": 5, 
                        "day_name": "Sabato", 
                        "type": "Dislivello", 
                        "desc": "Uscita collinare o montana con focus su variazioni di pendenza e ripetute brevi in salita.", 
                        "dur": 180, 
                        "zone": "Z3 / Z4"
                    },
                    {
                        "day_index": 6, 
                        "day_name": "Domenica", 
                        "type": "Lungo", 
                        "desc": "Giro lungo di resistenza aerobica a prevalenza Z2 con tratti regolari.", 
                        "dur": 240, 
                        "zone": "Z2"
                    }
                ]
                
                for w in workouts_template:
                    w_date = week_start + timedelta(days=w["day_index"])
                    generated_data.append({
                        "week_number": week,
                        "workout_date": str(w_date),
                        "day_of_week": w["day_name"],
                        "workout_type": w["type"],
                        "target_description": w["desc"],
                        "duration_min": w["dur"],
                        "target_zone": w["zone"],
                        "completed": False,
                        "actual_tss": 0
                    })
            
            supabase.table("cycling_training_plans").insert(generated_data).execute()
            st.success("Piano base generato con successo!")
            st.rerun()
            
        except Exception as e:
            st.error(f"Errore nella generazione: {e}")

# --- LETTURA DATI DA SUPABASE ---
try:
    response = supabase.table("cycling_training_plans").select("*").order("workout_date", desc=False).execute()
    plans = response.data
except Exception as e:
    plans = []
    st.error(f"Errore di connessione a Supabase: {e}")

# --- CORPO PRINCIPALE ---
if plans:
    st.subheader("📤 Aggiorna e Adatta con l'Ultimo Allenamento")
    
    uploaded_file = st.file_uploader("Carica il file PDF o lo screenshot del report (es. Intervals.icu)", type=["pdf", "png", "jpg", "jpeg"])
    
    completed_plans = [p for p in plans if not p.get('completed', False)]
    
    if uploaded_file is not None and completed_plans:
        selected_workout_id = st.selectbox(
            "A quale sessione pianificata corrisponde questa uscita?",
            options=[p['id'] for p in completed_plans],
            format_func=lambda x: next(f"Sett. {p['week_number']} - {p['workout_date']} ({p['workout_type']})" for p in completed_plans if p['id'] == x)
        )
        
        if st.button("Elabora e Ricalcola Piano in Modo Adattivo", type="primary"):
            with st.spinner("Analisi dell'attività e ricalcolo adattivo in corso..."):
                try:
                    # 1. Estrazione dati con Gemini Vision
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    file_bytes = uploaded_file.getvalue()
                    mime_type = uploaded_file.type
                    
                    extraction_prompt = """
                    Estrai da questo documento/screenshot i dati dell'allenamento. Restituisci SOLO un JSON con queste chiavi:
                    {"duration_minutes": 0, "tss": 0, "avg_power": 0}
                    """
                    resp_ext = model.generate_content([{"mime_type": mime_type, "data": file_bytes}, extraction_prompt])
                    text_ext = resp_ext.text.strip()
                    if "```json" in text_ext:
                        text_ext = text_ext.split("```json")[1].split("```")[0].strip()
                    elif "```" in text_ext:
                        text_ext = text_ext.split("```")[1].split("```")[0].strip()
                    workout_metrics = json.loads(text_ext)
                    
                    # 2. Segna l'allenamento come completato su Supabase
                    supabase.table("cycling_training_plans").update({
                        "completed": True,
                        "duration_min": workout_metrics.get("duration_minutes", 120),
                        "actual_tss": workout_metrics.get("tss", 0)
                    }).eq("id", selected_workout_id).execute()
                    
                    # 3. Prendi i prossimi allenamenti da adattare
                    future_plans = [p for p in completed_plans if p['id'] != selected_workout_id][:3]
                    
                    if future_plans:
                        replan_prompt = f"""
                        Sei un coach di ciclismo professionista per un atleta di 56 anni (FTP: {current_ftp}W).
                        L'atleta ha appena completato un'uscita con questi dati reali: {workout_metrics}
                        
                        Ecco i prossimi allenamenti pianificati: {future_plans}
                        
                        Compito: Valuta la fatica accumulata e adatta la descrizione (`target_description`), la durata (`duration_min`) e la zona (`target_zone`) dei prossimi allenamenti.
                        Restituisci SOLO una lista JSON valida formattata così, senza testo extra:
                        [
                            {{"id": id_originale, "target_description": "nuova descrizione", "duration_min": 120, "target_zone": "Z2"}}
                        ]
                        """
                        resp_replan = model.generate_content(replan_prompt)
                        text_rep = resp_replan.text.strip()
                        if "```json" in text_rep:
                            text_rep = text_rep.split("```json")[1].split("```")[0].strip()
                        elif "```" in text_rep:
                            text_rep = text_rep.split("```")[1].split("```")[0].strip()
                        
                        updated_schedule = json.loads(text_rep)
                        
                        # Aggiorna su Supabase
                        for item in updated_schedule:
                            supabase.table("cycling_training_plans").update({
                                "target_description": item.get("target_description"),
                                "duration_min": item.get("duration_min"),
                                "target_zone": item.get("target_zone")
                            }).eq("id", item.get("id")).execute()
                            
                        st.success("✨ Piano aggiornato e adattato con successo in base alla tua condizione reale!")
                        st.rerun()
                    else:
                        st.success("Allenamento registrato. Non ci sono sessioni future da ricalcolare.")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Errore durante l'elaborazione IA: {e}")
                    
    st.markdown("---")
    st.subheader("📅 Programma Attivo")
    
    for p in plans:
        cols = st.columns([2, 2, 4, 2, 1])
        with cols[0]:
            st.markdown(f"**Sett. {p['week_number']}**<br>{p['workout_date']} ({p['day_of_week']})", unsafe_allow_html=True)
        with cols[1]:
            badge = "🟢" if p['workout_type'] == "Medio" else ("🔵" if p['workout_type'] == "Lungo" else "🟠")
            st.markdown(f"{badge} **{p['workout_type']}**<br>`{p['target_zone']}`", unsafe_allow_html=True)
        with cols[2]:
            st.write(p['target_description'])
            if p.get('completed'):
                st.caption(f"🏁 *Completato | TSS Reale: {p.get('actual_tss', 0)}*")
        with cols[3]:
            st.write(f"⏱️ {p['duration_min']} min")
        with cols[4]:
            is_done = st.checkbox("Fatto", value=p['completed'], key=f"chk_{p['id']}")
            if is_done != p['completed']:
                supabase.table("cycling_training_plans").update({"completed": is_done}).eq("id", p['id']).execute()
                st.rerun()
        st.divider()
else:
    st.info("Nessun piano attivo. Usa il pannello laterale per generare il programma base.")
