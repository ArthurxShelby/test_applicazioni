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
st.set_page_config(page_title="Smart Adaptive Cycling Coach (AI Vision)", page_icon="🚴‍♂️", layout="wide")

# Connessione a Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Funzione per estrarre i dati dallo screenshot tramite IA (Gemini Vision)
def extract_workout_data_from_image(image):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = """
        Analizza questo screenshot di una schermata di ciclismo (es. Intervals.icu) ed estrai i seguenti valori numerici in formato JSON puro:
        - duration_minutes: durata totale dell'attività in minuti
        - tss: il valore del Carico / TSS
        - intensity: percentuale di intensità
        - avg_power: potenza media in watt
        - norm_power: potenza normalizzata in watt
        - avg_hr: frequenza cardiaca media
        - fitness: valore di Fitness se presente
        - fatigue: valore di Fatica se presente
        - form: valore di Forma se presente
        Restituisci SOLO un dizionario JSON valido con queste esatte chiavi.
        """
        response = model.generate_content([image, prompt])
        import json
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith:
