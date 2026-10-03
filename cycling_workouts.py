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

# Funzione ottimizzata per evitare loop e leggere direttamente PDF o immagini con Gemini
def extract_workout_data(uploaded_file):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        file_bytes = uploaded_file.getvalue()
        mime_type = uploaded_file.type
        
        file_part = {
            "mime_type": mime_type,
            "data": file_bytes
        }
        
        prompt = """
        Analizza questo documento o screenshot di Intervals.icu ed estrai ESATTAMENTE in formato JSON puro i seguenti valori numerici. Se un valore non è presente, metti 0.
        Restituisci SOLO un dizionario JSON con queste chiavi esatte e nessun altro testo:
        {
            "duration_minutes": 0,
            "tss": 0,
            "intensity": 0,
            "avg_power": 0,
            "norm_power": 0,
            "avg_hr": 0,
            "fitness": 0,
            "fatigue": 0,
            "form": 0
        }
        """
        
        response = model.generate_content([file_part, prompt])
            
        import json
        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("
