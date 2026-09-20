from datetime import datetime
import io
import json
import os
import time
from typing import Optional

from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
import streamlit as st

# Configurazione della pagina Streamlit
st.set_page_config(page_title="Gestione Scontrini", layout="centered")
st.title("🧾 Scatta, Registra e Genera PDF")

FILE_STORICO = "storico_scontrini.json"


# Schema Pydantic per i dati di input
class ScontrinoData(BaseModel):
    nome_negozio: str = Field(description="Nome dell'esercente")
    data: Optional[str] = Field(
        default=None,
        description="Data dello scontrino (YYYY-MM-DD) se ben visibile, altrimenti null",
    )
    totale_euro: float = Field(
        description="Importo totale finale pagato in Euro"
    )


# --- FUNZIONI DI GESTIONE STORICO ---
def carica_storico() -> list:
    """Carica lo storico dal file JSON se esiste."""
    if os.path.exists(FILE_STORICO):
        with open(FILE_STORICO, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def salva_scontrino(negozio: str, data: str, totale: float):
    """Aggiunge uno scontrino allo storico e ordina la lista per data (più recenti prima)."""
    storico = carica_storico()
    storico.append({"negozio": negozio, "data": data, "totale": totale})

    # Ordinamento per data decrescente (da più recente a meno recente)
    storico.sort(key=lambda x: x["data"], reverse=True)

    with open(FILE_STORICO, "w", encoding="utf-8") as f:
        json.dump(storico, f, ensure_ascii=False, indent=2)


# --- FUNZIONE GENERAZIONE PDF ---
def genera_pdf_storico(storico: list) -> bytes:
    """Crea un documento PDF formattato contenente lo storico degli scontrini."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    # Titolo del report
    title = Paragraph("<b>Report Generale Scontrini</b>", styles["Heading1"])
    story.append(title)
    
    data_generazione = Paragraph(
        f"<i>Generato il: {datetime.now().strftime('%d/%m/%Y alle %H:%M')}</i>", styles["Normal"]
    )
    story.append(data_generazione)
    story.append(Spacer(1, 15))

    # Definizione dati tabella
    table_data = [["Data", "Esercente / Negozio", "Importo (€)"]]
    totale_complessivo = 0.0

    for item in storico:
        table_data.append([item["data"], item["negozio"], f"€ {item['totale']:.2f}"])
        totale_complessivo += item["totale"]

    # Riga del totale
    table_data.append(["TOTALE COMPLESSIVO", "", f"€ {totale_complessivo:.2f}"])

    # Stile della tabella PDF
    table_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#31333F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("GRID", (0, 0), (-1, -2), 0.5, colors.grey),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E0E0E0")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("SPAN", (0, -1), (1, -1)),  # Unisce le prime due celle della riga totale
    ])

    table = Table(table_data, colWidths=[100, 300, 120])
    table.setStyle(table_style)
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# --- INTERFACCIA APP STREAMLIT ---
tab1, tab2 = st.tabs(["📷 Scansiona Scontrino", "📊 Storico & Export PDF"])

# TAB 1: ACQUISIZIONE
with tab1:
    foto_scattata = st.camera_input("Scatta una foto allo scontrino")

    if foto_scattata is not None:
        immagine = Image.open(foto_scattata)

        if st.button("Analizza e Salva Scontrino", type="primary"):
            with st.spinner("Analisi in corso con Gemini..."):
                modelli = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-1.5-flash"]
                dati = None
                ultimo_errore = None

                client = genai.Client()
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ScontrinoData,
                    temperature=0.1,
                )
                prompt = (
                    "Analizza questo scontrino ed estrai nome negozio, data e totale finale in euro. "
                    "Se la data non è visibile o è tagliata nella foto, lascia il campo data vuoto/null."
                )

                for modello in modelli:
                    for tentativo in range(2):
                        try:
                            response = client.models.generate_content(
                                model=modello,
                                contents=[immagine, prompt],
                                config=config,
                            )
                            dati = response.parsed
                            break
                        except Exception as e:
                            ultimo_errore = e
                            if "503" in str(e):
                                time.sleep(2)
                                continue
                            else:
                                break
                    if dati is not None:
                        break

                if dati is not None:
                    # Calcolo data finale
                    data_finale = (
                        dati.data
                        if dati.data
                        else datetime.now().strftime("%Y-%m-%d")
                    )

                    # Salva lo scontrino nello storico locale ordinato
                    salva_scontrino(dati.nome_negozio, data_finale, dati.totale_euro)

                    st.success("Scontrino analizzato e salvato nello storico!")
                    st.metric("Totale Euro", f"€ {dati.totale_euro:.2f}")
                    st.write(f"**Negozio:** {dati.nome_negozio}")
                    st.write(f"**Data registrata:** {data_finale}")
                else:
                    st.error(f"Si è verificato un errore durante l'analisi: {ultimo_errore}")

# TAB 2: STORICO & PDF
with tab2:
    storico_attuale = carica_storico()

    if storico_attuale:
        st.subheader("Elenco Scontrini Registrati (Ordinati per Data)")
        st.dataframe(storico_attuale, use_container_width=True)

        totale_speso = sum(item["totale"] for item in storico_attuale)
        st.metric("Totale Spesa Accumulata", f"€ {totale_speso:.2f}")

        # Generazione del file PDF al volo
        pdf_bytes = genera_pdf_storico(storico_attuale)

        st.download_button(
            label="📄 Scarica Report PDF",
            data=pdf_bytes,
            file_name=f"report_scontrini_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            type="primary",
        )
    else:
        st.info("Nessun uno scontrino salvato nello storico. Scansiona uno scontrino dalla prima scheda.")
