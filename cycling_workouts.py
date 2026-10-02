import streamlit as st
from supabase import create_client

# Configurazione della pagina
st.set_page_config(page_title="Cycling Training Manager", page_icon="🚴", layout="wide")

# Connessione a Supabase tramite secrets
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

st.title("🚴 Gestione Programma Allenamenti Bici")
st.markdown("Pianifica i tuoi lavori specifici, le uscite in solitaria e i giri di gruppo.")

# Sidebar per inserire nuovi allenamenti
with st.sidebar:
    st.header("Nuovo Allenamento")
    with st.form("workout_form", clear_on_submit=True):
        w_date = st.date_input("Data Allenamento")
        day = st.selectbox("Giorno", ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"])
        w_type = st.selectbox("Tipologia", ["Soglia / Ripetute", "Fondo / Agilità", "Uscita di Gruppo", "Scarico / Riposo"])
        desc = st.text_area("Dettagli (es. ripetute su salita, watt target)")
        duration = st.number_input("Durata stimata (minuti)", min_value=30, max_value=480, value=120, step=15)
        
        submitted = st.form_submit_button("Aggiungi al Calendario")
        
        if submitted:
            try:
                data = {
                    "workout_date": str(w_date),
                    "day_of_week": day,
                    "workout_type": w_type,
                    "description": desc,
                    "duration_min": duration,
                    "completed": False
                }
                supabase.table("cycling_workouts").insert(data).execute()
                st.success("Allenamento aggiunto con successo!")
                st.rerun()
            except Exception as e:
                st.error(f"Errore durante il salvataggio: {e}")

# Visualizzazione principale del programma
st.header("Tabellone Attività")

try:
    response = supabase.table("cycling_workouts").select("*").order("workout_date", desc=False).execute()
    workouts = response.data
    
    if workouts:
        # Mostra come tabella interattiva
        for w in workouts:
            col1, col2, col3, col4, col5 = st.columns([2, 2, 3, 2, 1])
            with col1:
                st.markdown(f"**{w['workout_date']}** ({w['day_of_week']})")
            with col2:
                st.badge = "🔴" if "Soglia" in w['workout_type'] else "🟢"
                st.markdown(f"{st.badge} `{w['workout_type']}`")
            with col3:
                st.write(w['description'] or "Nessun dettaglio")
            with col4:
                st.write(f"⏱️ {w['duration_min']} min")
            with col5:
                # Pulsante per marcare come completato
                status = st.checkbox("Fatto", value=w['completed'], key=f"chk_{w['id']}")
                if status != w['completed']:
                    supabase.table("cycling_workouts").update({"completed": status}).eq("id", w['id']).execute()
                    st.rerun()
            st.divider()
    else:
        st.info("Nessun allenamento pianificato. Utilizza la sidebar per aggiungerne uno.")

except Exception as e:
    st.error(f"Impossibile caricare i dati da Supabase: {e}")
