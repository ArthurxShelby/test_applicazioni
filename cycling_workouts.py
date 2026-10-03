import streamlit as st
from supabase import create_client
from datetime import datetime, timedelta
import io
import google.generativeai as genai
from PIL import Image

# Import per la generazione del PDF con ReportLab
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Configurazione della pagina
st.set_page_config(page_title="Smart Adaptive Cycling Coach (AI Vision)", page_icon="🚴‍♂️️", layout="wide")

# Connessione a Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Funzione corretta: legge le etichette reali di Intervals.icu dal file caricato
def extract_workout_data(uploaded_file):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = """
        Analizza questo report di Intervals.icu ed estrai in formato JSON puro i seguenti valori numerici trovati nel documento:
        - duration_minutes: converti la durata totale (es. 2:25:54) in minuti totali (numero intero)
        - tss: il valore del "Carico" o TRIMP (numero intero)
        - intensity: la percentuale di "Intensità" senza il simbolo % (numero intero)
        - avg_power: la "Potenza media" in watt (numero intero)
        - norm_power: la "Potenza Norm" in watt (numero intero)
        - avg_hr: la "FC media" (frequenza cardiaca media, numero intero)
        - fitness: il valore di "Fitness" (numero intero o 0)
        - fatigue: il valore di "Fatica" (numero intero o 0)
        - form: il valore di "Forma" (può essere negativo, es. -11, numero intero o 0)
        
        Restituisci SOLO un dizionario JSON valido con queste esatte chiavi, senza altri testi.
        """
        
        file_bytes = uploaded_file.getvalue()
        mime_type = uploaded_file.type
        
        file_part = {
            "mime_type": mime_type,
            "data": file_bytes
        }
        
        response = model.generate_content([file_part, prompt])
            
        import json
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
        return json.loads(text)
    except Exception as e:
        st.error(f"Errore nell'estrazione dei dati: {e}")
        return None

# Funzione per generare il PDF del piano
def generate_pdf(plans_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=30, bottomMargin=30)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#1f2937'), spaceAfter=10, alignment=1)
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#4b5563'), spaceAfter=15, alignment=1)
    
    th_style = ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=8, textColor=colors.whitesmoke, alignment=1)
    td_center = ParagraphStyle('TDC', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#1f2937'), alignment=1)
    td_left = ParagraphStyle('TDL', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#1f2937'), alignment=0)
    
    elements.append(Paragraph("<b>PROGRAMMA DI ALLENAMENTO CICLISMO ADATTIVO (AI)</b>", title_style))
    elements.append(Paragraph(f"Generato il {datetime.today().strftime('%d/%m/%Y')} | Sincronizzato con metriche reali", subtitle_style))
    elements.append(Spacer(1, 5))
    
    table_data = [[
        Paragraph("Sett.", th_style),
        Paragraph("Data", th_style),
        Paragraph("Giorno", th_style),
        Paragraph("Tipologia", th_style),
        Paragraph("Descrizione", th_style),
        Paragraph("Durata", th_style),
        Paragraph("Zona", th_style)
    ]]
    
    for p in plans_data:
        table_data.append([
            Paragraph(f"Sett. {p['week_number']}", td_center),
            Paragraph(str(p['workout_date']), td_center),
            Paragraph(p['day_of_week'], td_center),
            Paragraph(p['workout_type'], td_left),
            Paragraph(p['target_description'], td_left),
            Paragraph(f"{p['duration_min']} min", td_center),
            Paragraph(p['target_zone'], td_center)
        ])
        
    t = Table(table_data, colWidths=[40, 65, 60, 95, 200, 45, 40])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#3b82f6')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f9fafb')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d1d5db')),
        ('TOPPADDING', (0,1), (-1,-1), 5),
        ('BOTTOMPADDING', (0,1), (-1,-1), 5),
    ]))
    
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer

st.title("🚴‍♂️ Smart Adaptive Cycling Coach")
st.markdown("Carica il file **PDF** o lo **screenshot** della tua uscita per aggiornare istantaneamente il programma.")

# --- FETCH DATI ATTUALI ---
try:
    response = supabase.table("cycling_training_plans").select("*").order("workout_date", desc=False).execute()
    plans = response.data
except Exception as e:
    plans = []
    st.error(f"Errore di connessione a Supabase: {e}")

# --- SIDEBAR: PARAMETRI E GENERATORE INIZIALE ---
with st.sidebar:
    st.header("⚙ Parametri Atleta & FTP")
    age = st.number_input("Età", min_value=18, max_value=80, value=56)
    current_ftp = st.number_input("FTP attuale (W)", value=268)
    
    training_days_count = st.selectbox(
        "Giorni di allenamento a settimana", 
        [3, 4], 
        index=0, 
        format_func=lambda x: f"{x} giorni (Mer, Sab, Dom)" if x == 3 else f"{x} giorni (Mar, Gio, Sab, Dom)"
    )
    
    st.markdown("---")
    st.header("🛠 Genera / Reset Piano Base")
    start_date = st.date_input("Data di inizio (Lunedì)", value=datetime.today())
    num_weeks = st.slider("Numero di settimane", min_value=1, max_value=8, value=4)
    
    if st.button("Genera Nuovo Piano Base", type="primary"):
        try:
            supabase.table("cycling_training_plans").delete().neq("id", 0).execute()
            generated_data = []
            current_monday = start_date - timedelta(days=start_date.weekday())
            
            for week in range(1, num_weeks + 1):
                week_start = current_monday + timedelta(weeks=week - 1)
                is_recovery_week = (week % 4 == 0)
                
                if training_days_count == 3:
                    if is_recovery_week:
                        exact_workouts = [
                            {"day_index": 2, "day_name": "Mercoledì", "type": "Scarico - Agilità", "desc": "Agilità e scarico attivo, brevi richiami agili senza fuorigiri", "dur": 75, "zone": "Z2 / Recupero"},
                            {"day_index": 5, "day_name": "Sabato", "type": "Scarico - Uscita Breve", "desc": "Uscita corta e tranquilla in pianura o collinare leggero", "dur": 90, "zone": "Z2"},
                            {"day_index": 6, "day_name": "Domenica", "type": "Scarico - Fondo Lungo ridotto", "desc": "Giro di fondo lungo ma a intensità ridotta e senza dislivelli impegnativi", "dur": 120, "zone": "Z2"}
                        ]
                    else:
                        exact_workouts = [
                            {"day_index": 2, "day_name": "Mercoledì", "type": "Lavori Specifici / Soglia", "desc": f"Riscaldamento + Ripetute in Z4/Soglia (target ~{round(current_ftp*0.9)}W) + defaticamento", "dur": 135, "zone": "Z4 / Soglia"},
                            {"day_index": 5, "day_name": "Sabato", "type": "Uscita Collinare con Intervalli", "desc": "Giro collinare con variazioni di ritmo e blocchi ripetuti in salita", "dur": 195, "zone": "Z3 / Z4 / Z5"},
                            {"day_index": 6, "day_name": "Domenica", "type": "Giro Lungo di Resistenza", "desc": "Giro lungo in prevalenza Z2 con brevi tratti a ritmo costante", "dur": 220, "zone": "Z2 / Z3"}
                        ]
                else:
                    if is_recovery_week:
                        exact_workouts = [
                            {"day_index": 1, "day_name": "Martedì", "type": "Scarico - Agilità", "desc": "Agilità leggera e scioltezza", "dur": 60, "zone": "Z2"},
                            {"day_index": 3, "day_name": "Giovedì", "type": "Scarico - Fondo Agile", "desc": "Uscita facile di richiamo", "dur": 75, "zone": "Z2"},
                            {"day_index": 5, "day_name": "Sabato", "type": "Scarico - Uscita Breve", "desc": "Giro corto e tranquillo", "dur": 90, "zone": "Z2"},
                            {"day_index": 6, "day_name": "Domenica", "type": "Scarico - Fondo Lungo", "desc": "Fondo lungo ridotto e costante", "dur": 120, "zone": "Z2"}
                        ]
                    else:
                        exact_workouts = [
                            {"day_index": 1, "day_name": "Martedì", "type": "Ripetute / VO2Max", "desc": f"Lavori brevi ad alta intensità (target ~{round(current_ftp*1.05)}W)", "dur": 90, "zone": "Z5 / VO2Max"},
                            {"day_index": 3, "day_name": "Giovedì", "type": "Forza / Sweet Spot", "desc": f"Intervalli lunghi in Sweet Spot (target ~{round(current_ftp*0.88)}W)", "dur": 105, "zone": "Z3 / Sweet Spot"},
                            {"day_index": 5, "day_name": "Sabato", "type": "Uscita Collinare", "desc": "Giro collinare con variazioni e salite brillanti", "dur": 180, "zone": "Z3 / Z4"},
                            {"day_index": 6, "day_name": "Domenica", "type": "Fondo Lungo", "desc": "Giro lungo di resistenza aerobica", "dur": 210, "zone": "Z2"}
                        ]
                
                for workout in exact_workouts:
                    w_date = week_start + timedelta(days=workout["day_index"])
                    generated_data.append({
                        "week_number": week,
                        "workout_date": str(w_date),
                        "day_of_week": workout["day_name"],
                        "workout_type": workout["type"],
                        "target_description": workout["desc"],
                        "duration_min": workout["dur"],
                        "target_zone": workout["zone"],
                        "completed": False,
                        "perceived_effort": 5
                    })

            supabase.table("cycling_training_plans").insert(generated_data).execute()
            st.success("Nuovo piano base generato!")
            st.rerun()
            
        except Exception as e:
            st.error(f"Errore: {e}")

    if st.button("🗑️ Svuota database allenamenti"):
        supabase.table("cycling_training_plans").delete().neq("id", 0).execute()
        st.warning("Database pulito.")
        st.rerun()

    if plans:
        st.markdown("---")
        st.header("📄 Esporta")
        pdf_data = generate_pdf(plans)
        st.download_button("📥 Scarica PDF Aggiornato", data=pdf_data, file_name="programma_adattivo_ai.pdf", mime="application/pdf")

# --- CORPO PRINCIPALE: UPLOAD FILE & ADATTAMENTO ---
st.header("📤 Carica Rapporto Attività (PDF o Immagine)")

if plans:
    with st.expander("🤖 Estrazione dati & Ricalcolo sessioni future", expanded=True):
        uploaded_file = st.file_uploader("Carica il file PDF o lo screenshot dell'uscita", type=["pdf", "png", "jpg", "jpeg"])
        
        completed_plans = [p for p in plans if not p.get('completed', False)]
        if completed_plans and uploaded_file is not None:
            selected_workout_id = st.selectbox(
                "A quale sessione pianificata corrisponde questa uscita?",
                options=[p['id'] for p in completed_plans],
                format_func=lambda x: next(f"Sett. {p['week_number']} - {p['workout_date']} ({p['workout_type']})" for p in completed_plans if p['id'] == x)
            )
            
            if st.button("Elabora File e Aggiorna Programma", type="primary"):
                with st.spinner("Analisi visiva del file in corso..."):
                    extracted_data = extract_workout_data(uploaded_file)
                
                if extracted_data:
                    st.success("Dati estratti con successo:")
                    st.json(extracted_data)
                    
                    tss_val = extracted_data.get("tss", 100)
                    fatigue_val = extracted_data.get("fatigue", 80)
                    
                    # 1. Aggiorna la sessione completata
                    supabase.table("cycling_training_plans").update({
                        "completed": True,
                        "duration_min": extracted_data.get("duration_minutes", 120),
                        "actual_tss": tss_val,
                        "perceived_effort": 8 if tss_val > 130 else 5
                    }).eq("id", selected_workout_id).execute()
                    
                    # 2. Ricalcolo automatico delle sessioni successive
                    if tss_val > 130 or fatigue_val > 90:
                        future_workouts = [p for p in completed_plans if p['id'] != selected_workout_id][:2]
                        for fw in future_workouts:
                            new_desc = fw['target_description'] + " (Adattato: scarico preventivo post-carico elevato)"
                            new_dur = max(60, int(fw['duration_min'] * 0.85))
                            supabase.table("cycling_training_plans").update({
                                "target_description": new_desc,
                                "duration_min": new_dur
                            }).eq("id", fw['id']).execute()
                        st.warning(f"⚠️ Carico elevato rilevato (TSS {tss_val}). Il coach ha automaticamente alleggerito le prossime 2 sessioni.")
                    else:
                        st.info("✅ Carico ottimale registrato. Sessioni successive confermate.")
                    
                    st.rerun()
        elif not completed_plans:
            st.info("Tutte le sessioni pianificate sono completate!")
        else:
            st.info("Carica un file PDF o un'immagine per procedere.")

    st.markdown("---")
    st.header("📅 Programma Attivo")
    
    for p in plans:
        with st.container():
            c1, c2, c3, c4, c5 = st.columns([2, 2, 3, 2, 1])
            with c1:
                st.markdown(f"**Settimana {p['week_number']}**<br>{p['workout_date']} ({p['day_of_week']})", unsafe_allow_html=True)
            with c2:
                is_recovery = "Scarico" in p['workout_type'] if 'workout_type' in p else False
                badge = "🔵" if is_recovery else ("🔴" if "Soglia" in p['workout_type'] or "Intervalli" in p['workout_type'] else "🟢")
                st.markdown(f"{badge} **{p['workout_type']}**<br>Target: `{p['target_zone']}`", unsafe_allow_html=True)
            with c3:
                st.write(p['target_description'])
                if p.get('completed'):
                    st.caption(f"🏁 *Completato | TSS Reale: {p.get('actual_tss', 'N/D')}*")
            with c4:
                st.write(f"⏱️ {p['duration_min']} min")
            with c5:
                is_done = st.checkbox("Fatto", value=p['completed'], key=f"plan_{p['id']}")
                if is_done != p['completed']:
                    supabase.table("cycling_training_plans").update({"completed": is_done}).eq("id", p['id']).execute()
                    st.rerun()
            st.divider()
else:
    st.info("Nessun piano attivo. Usa il pannello laterale per generare il programma base.")
