import io
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Gestione Spese Condominiali", page_icon="🏢", layout="wide")

try:
  SUPABASE_URL = (st.secrets.get("SUPABASE_URL") or st.secrets["supabase"]["SUPABASE_URL"]).strip()
  SUPABASE_KEY = (st.secrets.get("SUPABASE_KEY") or st.secrets["supabase"]["SUPABASE_KEY"]).strip()
except Exception:
  st.error("Configurazione Supabase mancante nei Secrets di Streamlit!")
  st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET_NAME = "fatture_pdf"
APP_NAMES = ["ESPOSITO","MARANGI","LINCESSO","FUSO","PUCA","BAVILA","TESTA"]

def carica_mq_da_supabase():
  try:
    response = supabase.table("condominio").select("*").execute()
    if response.data and len(response.data) > 0:
      return {row["condominio"]: float(row["mq"]) for row in response.data}
  except Exception:
    pass
  return {"ESPOSITO": 70.0,"MARANGI": 75.0,"LINCESSO": 80.0,"FUSO": 85.0,"PUCA": 90.0,"BAVILA": 85.0,"TESTA": 85.0}

def salva_mq_su_supabase(mq_dict):
  try:
    supabase.table("condominio").delete().gte("id", 0).execute()
  except Exception:
    pass
  for cond, mq in mq_dict.items():
    supabase.table("condominio").insert({"condominio": cond, "mq": mq}).execute()
  return True

def carica_fatture_da_supabase():
  try:
    response = supabase.table("fatture").select("*").execute()
    if response.data is not None:
      return pd.DataFrame(response.data)
  except Exception as e:
    st.error(f"Errore lettura tabella 'fatture': {e}")
  return pd.DataFrame(columns=["id","anno","mese","tipo","fornitore","imponibile","iva","totale","file"])

def carica_pagamenti_da_supabase():
  for nome_tabella in ["pagamenti", "pagamneti"]:
    try:
      response = supabase.table(nome_tabella).select("*").execute()
      if response.data is not None:
        return pd.DataFrame(response.data)
    except Exception:
      continue
  return pd.DataFrame(columns=["id","condominio","fattura_id","data_pagamento","importo_da_pagare","importo_pagato","accredito","riporto"])

if "logged_in" not in st.session_state:
  st.session_state.logged_in = False
if "mq_appartamenti" not in st.session_state:
  st.session_state.mq_appartamenti = carica_mq_da_supabase()
if "fatture" not in st.session_state:
  st.session_state.fatture = carica_fatture_da_supabase()
if "pagamenti" not in st.session_state:
  st.session_state.pagamenti = carica_pagamenti_da_supabase()

def calcola_millesimi_da_mq(mq_dict):
  tot_mq = sum(mq_dict.values())
  if tot_mq <= 0:
    return {k: 0 for k in mq_dict}
  return {app: round((mq / tot_mq) * 1000, 2) for app, mq in mq_dict.items()}

def genera_pdf_riparto(df_reparto, titolo_contesto):
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(buffer, pagesize=letter)
  elements = []
  styles = getSampleStyleSheet()
  title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=15, alignment=1, spaceAfter=10)
  subtitle_style = ParagraphStyle('SubtitleStyle', parent=styles['Normal'], fontSize=9, alignment=1, spaceAfter=15)
  elements.append(Paragraph("<b>RIEPILOGO RIPARTO SPESE CONDOMINIALI</b>", title_style))
  elements.append(Paragraph(f"Contesto: {titolo_contesto}", subtitle_style))
  elements.append(Spacer(1, 10))
  data = [list(df_reparto.columns)] + df_reparto.values.tolist()
  table = Table(data, colWidths=[110, 80, 110, 110, 110])
  table.setStyle(TableStyle([
          ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
          ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
          ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
          ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
          ('FONTSIZE', (0, 0), (-1, 0), 9),
          ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
          ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#f8f9fa')),
          ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e2e8f0')),
          ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
          ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
          ('FONTSIZE', (0, 1), (-1, -1), 9),
          ('TOPPADDING', (0, 1), (-1, -1), 5),
          ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
      ]))
  elements.append(table)
  doc.build(elements)
  buffer.seek(0)
