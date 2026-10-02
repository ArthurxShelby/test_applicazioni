import streamlit as st
from supabase import create_client
from datetime import datetime, timedelta

# Configurazione della pagina
st.set_page_config(page_title="Cycling Coach Planner", page_icon="🚴‍♂️", layout="wide")

# Connessione a Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

st.title("🚴‍♂️ Smart Cycling Training Planner")
st.markdown("Generatore automatico di tabelle di allenamento personalizzate basate sui tuoi parametri.")

# --- SIDEBAR: PARAMETRI E GENERATORE AUTOMATICO ---
with st.sidebar:
    st.header("⚙️ I tuoi Parametri")
    
    # Parametri anagrafici e di volume
    age = st.number_input("Età", min_value=18, max_value=80, value=56)
    weekly_rides = st.slider("Uscite settimanali", min_value=2, max_value=6, value=4)
    target_km = st.number_input("Km settimanali target", value=350)
    target_d_plus = st.number_input("Dislivello (D+) target in metri", value=3800, step=100)
    
    st.markdown("---")
    st.header("🛠️ Genera Tabella")
    start_date = st.date_input("Data inizio blocco", value=datetime.today())
    num_weeks = st.slider("Numero di settimane da generare", min_value=1, max_value=4, value=2)
    
    if st.button("Genera Programma Automatico", type="primary"):
        try:
            # Pulisciamo o creiamo la logica di generazione
            current_date = start_date
            generated_data = []
            
            for week in range(1, num_weeks + 1):
                # Struttura tipo: 4 uscite (2 solitarie infrasettimanali, 2 di gruppo weekend)
                days_plan = [
                    {"day": "Martedì", "type": "Solitaria - Lavori di Soglia", "desc": "Ripetute / Lavori specifici (es. San Servolo) + fondo medio", "dur": 120, "zone": "Z4/Soglia"},
                    {"day": "Giovedì", "type": "Solitaria - Agilità e Forza", "desc": "Agilità, sfr e passista in solitaria", "dur": 150, "zone": "Z3/Tempo"},
                    {"day": "Sabato", "type": "Uscita di Gruppo - Collinare", "desc": "Giro in compagnia, ritmo brillante ma gestito", "dur": 210, "zone": "Z2/Z3"},
                    {"day": "Domenica", "type": "Uscita di Gruppo - Lungo", "desc": "Giro lungo con dislivello e gruppo amatoriale", "dur": 270, "zone": "Z2"},
                ]
                
                # Se l'utente vuole un numero di uscite diverso, adattiamo la logica di base
                active_days = days_plan[:weekly_rides]
                
                for item in active_days:
                    # Calcoliamo una data approssimativa basata sul giorno della settimana
                    generated_data.append({
                        "week_number": week,
                        "workout_date": str(current_date),
                        "day_of_week": item["day"],
                        "workout_type": item["type"],
                        "target_description": item["desc"],
                        "duration_min": item["dur"],
                        "target_zone": item["zone"],
                        "completed": False
                    })
                    current_date += timedelta(days=1)
                
                # Avanziamo i giorni per arrivare alla settimana successiva
                current_date += timedelta(days=(7 - len(active_days)))

            # Salvataggio in batch su Supabase
            supabase.table("cycling_training_plans").insert(generated_data).execute()
            st.success(f"Programma di {num_weeks} settimane generato e salvato su Supabase!")
            st.rerun()
            
        except Exception as e:
            st.error(f"Errore nella generazione: {e}")
            
    if st.button("🗑️ Svuota tutto il database"):
        supabase.table("cycling_training_plans").delete().neq("id", 0).execute()
        st.warning("Database svuotato.")
        st.rerun()

# --- CORPO PRINCIPALE: VISUALIZZAZIONE TABELLA ---
st.header("📅 Il tuo Programma Attuale")

try:
    response = supabase.table("cycling_training_plans").select("*").order("workout_date", desc=False).execute()
    plans = response.data
    
    if plans:
        # Metriche riassuntive
        total_mins = sum([p['duration_min'] for p in plans if not p['completed']])
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Minuti totali pianificati", f"{total_mins} min (~{round(total_mins/60, 1)} ore)")
        col_m2.metric("Uscite in programma", len(plans))
        
        st.markdown("---")
        
        # Mostriamo il tabellone diviso per settimane
        for p in plans:
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([2, 2, 3, 2, 1])
                with c1:
                    st.markdown(f"**Settimana {p['week_number']}**<br>{p['workout_date']} ({p['day_of_week']})", unsafe_allow_html=True)
                with c2:
                    badge_color = "🔴" if "Soglia" in p['workout_type'] else "🟢"
                    st.markdown(f"{badge_color} **{p['workout_type']}**<br>Target: `{p['target_zone']}`", unsafe_allow_html=True)
                with c3:
                    st.write(p['target_description'])
                with c4:
                    st.write(f"⏱️ {p['duration_min']} minuti")
                with c5:
                    is_done = st.checkbox("Fatto", value=p['completed'], key=f"plan_{p['id']}")
                    if is_done != p['completed']:
                        supabase.table("cycling_training_plans").update({"completed": is_done}).eq("id", p['id']).execute()
                        st.rerun()
                st.divider()
    else:
        st.info("Nessun piano di allenamento attivo. Usa i parametri nella barra laterale e clicca su 'Genera Programma Automatico'.")

except Exception as e:
    st.error(f"Errore di caricamento da Supabase: {e}")
