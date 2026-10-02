import streamlit as st
from supabase import create_client
from datetime import datetime, timedelta

# Configurazione della pagina
st.set_page_config(page_title="Smart Cycling Coach", page_icon="🚴‍♂️", layout="wide")

# Connessione a Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

st.title("🚴‍♂️ Smart Cycling Coach - 3 Days Planner")
st.markdown("Pianificazione mirata basata sui tuoi giorni fissi: **Mercoledì (Specifico)**, **Sabato (Collinare/Intervalli)** e **Domenica (Lungo)**.")

# --- SIDEBAR: PARAMETRI E GENERATORE ---
with st.sidebar:
    st.header("⚙️ Parametri Atleta")
    age = st.number_input("Età", min_value=18, max_value=80, value=56)
    ftp = st.number_input("FTP attuale (W)", value=268)
    
    st.markdown("---")
    st.header("🛠️ Genera Tabella (Mer, Sab, Dom)")
    start_date = st.date_input("Data di inizio (scegli un Lunedì o il giorno di avvio)", value=datetime.today())
    num_weeks = st.slider("Numero di settimane da pianificare", min_value=1, max_value=4, value=2)
    
    if st.button("Genera Programma 3 Giorni", type="primary"):
        try:
            current_date = start_date
            generated_data = []
            
            # Pattern fisso sui 3 giorni richiesti
            # Cerchiamo il prossimo Mercoledì, Sabato e Domenica a partire dalla data selezionata
            for week in range(1, num_weeks + 1):
                
                # Definiamo i 3 allenamenti tipo basati sui tuoi grafici Intervals.icu
                weekly_structure = [
                    {
                        "day_offset": 2, # Mercoledì (assumendo lunedì=0 o calcolato dal giorno)
                        "day_name": "Mercoledì",
                        "type": "Lavori Specifici / Soglia",
                        "desc": f"Riscaldamento + Ripetute in Z4/Soglia (target ~{round(ftp*0.9)}W) + defaticamento",
                        "dur": 135,
                        "zone": "Z4 / Soglia"
                    },
                    {
                        "day_offset": 5, # Sabato
                        "day_name": "Sabato",
                        "type": "Uscita Collinare con Intervalli",
                        "desc": "Giro collinare (es. 80-90 km) con variazioni di ritmo e blocchi ripetuti in salita",
                        "dur": 195,
                        "zone": "Z3 / Z4 / Z5"
                    },
                    {
                        "day_offset": 6, # Domenica
                        "day_name": "Domenica",
                        "type": "Giro Lungo di Resistenza",
                        "desc": "Uscita lunga (120+ km) in prevalenza Z2 con brevi tratti a ritmo costante",
                        "dur": 220,
                        "zone": "Z2 / Z3"
                    }
                ]
                
                # Troviamo il lunedì della settimana corrente
                # Portiamo current_date al lunedì della settimana
                start_of_week = current_date - timedelta(days=current_date.weekday())
                
                for workout in weekly_structure:
                    w_date = start_of_week + timedelta(days=workout["day_offset"])
                    generated_data.append({
                        "week_number": week,
                        "workout_date": str(w_date),
                        "day_of_week": workout["day_name"],
                        "workout_type": workout["type"],
                        "target_description": workout["desc"],
                        "duration_min": workout["dur"],
                        "target_zone": workout["zone"],
                        "completed": False
                    })
                
                # Passiamo alla settimana successiva
                current_date += timedelta(weeks=1)

            # Inserimento in Supabase
            supabase.table("cycling_training_plans").insert(generated_data).execute()
            st.success(f"Programma di {num_weeks} settimane generato con successo!")
            st.rerun()
            
        except Exception as e:
            st.error(f"Errore nella generazione: {e}")
            
    if st.button("🗑️ Svuota database allenamenti"):
        supabase.table("cycling_training_plans").delete().neq("id", 0).execute()
        st.warning("Database pulito.")
        st.rerun()

# --- CORPO PRINCIPALE ---
st.header("📅 Programma Attivo (Mercoledì, Sabato, Domenica)")

try:
    response = supabase.table("cycling_training_plans").select("*").order("workout_date", desc=False).execute()
    plans = response.data
    
    if plans:
        total_mins = sum([p['duration_min'] for p in plans if not p['completed']])
        col1, col2 = st.columns(2)
        col1.metric("Minuti totali pianificati", f"{total_mins} min (~{round(total_mins/60, 1)} ore)")
        col2.metric("Sessioni in programma", len(plans))
        
        st.markdown("---")
        
        for p in plans:
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([2, 2, 3, 2, 1])
                with c1:
                    st.markdown(f"**Settimana {p['week_number']}**<br>{p['workout_date']} ({p['day_of_week']})", unsafe_allow_html=True)
                with c2:
                    badge = "🔴" if "Soglia" in p['workout_type'] or "Intervalli" in p['workout_type'] else "🟢"
                    st.markdown(f"{badge} **{p['workout_type']}**<br>Target: `{p['target_zone']}`", unsafe_allow_html=True)
                with c3:
                    st.write(p['target_description'])
                with c4:
                    st.write(f"⏱️ {p['duration_min']} min")
                with c5:
                    is_done = st.checkbox("Fatto", value=p['completed'], key=f"plan_{p['id']}")
                    if is_done != p['completed']:
                        supabase.table("cycling_training_plans").update({"completed": is_done}).eq("id", p['id']).execute()
                        st.rerun()
                st.divider()
    else:
        st.info("Nessun piano attivo. Usa il pannello laterale per generare la tua tabella basata sui tre giorni (Mer, Sab, Dom).")

except Exception as e:
    st.error(f"Errore di connessione a Supabase: {e}")
