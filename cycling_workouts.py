import streamlit as st
from supabase import create_client
from datetime import datetime, timedelta
import io

# Import per la generazione del PDF con ReportLab
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Configurazione della pagina
st.set_page_config(page_title="Smart Cycling Coach", page_icon="🚴‍♂️", layout="wide")

# Connessione a Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Funzione per generare il PDF formattato correttamente senza sovrapposizioni
def generate_pdf(plans_data):
    # Usiamo margini laterali stretti (20 mm) per sfruttare tutta la larghezza dell'A4
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=30, bottomMargin=30)
    elements = []
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=10,
        alignment=1 # Centrato
    )
    
    subtitle_style = ParagraphStyle(
        'SubTitleStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#4b5563'),
        spaceAfter=15,
        alignment=1
    )
    
    # Stili per il testo dentro le celle della tabella (per garantire il ritorno a capo automatico)
    th_style = ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=8, textColor=colors.whitesmoke, alignment=1)
    td_center = ParagraphStyle('TDC', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#1f2937'), alignment=1)
    td_left = ParagraphStyle('TDL', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#1f2937'), alignment=0)
    
    elements.append(Paragraph("<b>PROGRAMMA DI ALLENAMENTO CICLISMO</b>", title_style))
    elements.append(Paragraph(f"Generato il {datetime.today().strftime('%d/%m/%Y')} | Obiettivo: 3 giorni fissi (Mer, Sab, Dom)", subtitle_style))
    elements.append(Spacer(1, 5))
    
    # Intestazione della tabella con Paragraph
    table_data = [[
        Paragraph("Sett.", th_style),
        Paragraph("Data", th_style),
        Paragraph("Giorno", th_style),
        Paragraph("Tipologia", th_style),
        Paragraph("Descrizione", th_style),
        Paragraph("Durata", th_style),
        Paragraph("Zona", th_style)
    ]]
    
    # Righe della tabella con Paragraph per evitare sovrapposizioni
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
        
    # Larghezze calcolate sulla larghezza utile del foglio A4 (~545 punti totali)
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

st.title("🚴‍♂️ Smart Cycling Coach - 3 Giorni Fissi (Mer, Sab, Dom)")
st.markdown("Programma di allenamento strutturato con blocco periodico di scarico alla 4ª settimana.")

# --- FETCH DATI ATTUALI ---
try:
    response = supabase.table("cycling_training_plans").select("*").order("workout_date", desc=False).execute()
    plans = response.data
except Exception as e:
    plans = []
    st.error(f"Errore di connessione a Supabase: {e}")

# --- SIDEBAR: PARAMETRI E GENERATORE ---
with st.sidebar:
    st.header("⚙️ Parametri Atleta")
    age = st.number_input("Età", min_value=18, max_value=80, value=56)
    ftp = st.number_input("FTP attuale (W)", value=268)
    
    training_days_count = st.selectbox("Giorni di allenamento a settimana", [3], index=0)
    
    st.markdown("---")
    st.header("🛠 Genera Tabella")
    start_date = st.date_input("Data di inizio (es. un Lunedì)", value=datetime.today())
    num_weeks = st.slider("Numero di settimane da pianificare", min_value=1, max_value=8, value=4)
    
    if st.button("Genera Programma", type="primary"):
        try:
            # Pulizia preventiva del database
            supabase.table("cycling_training_plans").delete().neq("id", 0).execute()
            
            generated_data = []
            current_monday = start_date - timedelta(days=start_date.weekday())
            
            for week in range(1, num_weeks + 1):
                week_start = current_monday + timedelta(weeks=week - 1)
                is_recovery_week = (week % 4 == 0)
                
                if is_recovery_week:
                    exact_workouts = [
                        {"day_index": 2, "day_name": "Mercoledì", "type": "Scarico - Agilità", "desc": "Agilità e scarico attivo, brevi richiami agili senza fuorigiri", "dur": 75, "zone": "Z2 / Recupero"},
                        {"day_index": 5, "day_name": "Sabato", "type": "Scarico - Uscita Breve", "desc": "Uscita corta e tranquilla in pianura o collinare leggero", "dur": 90, "zone": "Z2"},
                        {"day_index": 6, "day_name": "Domenica", "type": "Scarico - Fondo Lungo ridotto", "desc": "Giro di fondo lungo ma a intensità ridotta e senza dislivelli impegnativi", "dur": 120, "zone": "Z2"}
                    ]
                else:
                    exact_workouts = [
                        {"day_index": 2, "day_name": "Mercoledì", "type": "Lavori Specifici / Soglia", "desc": f"Riscaldamento + Ripetute in Z4/Soglia (target ~{round(ftp*0.9)}W) + defaticamento", "dur": 135, "zone": "Z4 / Soglia"},
                        {"day_index": 5, "day_name": "Sabato", "type": "Uscita Collinare con Intervalli", "desc": "Giro collinare con variazioni di ritmo e blocchi ripetuti in salita", "dur": 195, "zone": "Z3 / Z4 / Z5"},
                        {"day_index": 6, "day_name": "Domenica", "type": "Giro Lungo di Resistenza", "desc": "Giro lungo in prevalenza Z2 con brevi tratti a ritmo costante", "dur": 220, "zone": "Z2 / Z3"}
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
                        "completed": False
                    })

            supabase.table("cycling_training_plans").insert(generated_data).execute()
            st.success(f"Programma di {num_weeks} settimane generato con successo!")
            st.rerun()
            
        except Exception as e:
            st.error(f"Errore nella generazione: {e}")
            
    if st.button("🗑️ Svuota database allenamenti"):
        supabase.table("cycling_training_plans").delete().neq("id", 0).execute()
        st.warning("Database pulito.")
        st.rerun()

    # --- SEZIONE DOWNLOAD PDF ---
    if plans:
        st.markdown("---")
        st.header("📄 Esporta Programma")
        pdf_data = generate_pdf(plans)
        st.download_button(
            label="📥 Scarica PDF del Periodo",
            data=pdf_data,
            file_name=f"programma_ciclismo_{datetime.today().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            type="secondary"
        )

# --- CORPO PRINCIPALE ---
st.header("📅 Programma Attivo")

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
                is_recovery = "Scarico" in p['workout_type']
                badge = "🔵" if is_recovery else ("🔴" if "Soglia" in p['workout_type'] or "Intervalli" in p['workout_type'] else "🟢")
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
    st.info("Nessun piano attivo. Usa il pannello laterale per generare il programma e sbloccare il download del PDF.")
    
