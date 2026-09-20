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
st.title("🧾 Scatta, Inserisci e Genera PDF")

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
                data = json.load(f)
                for idx, item in enumerate(data):
                    if "id" not in item:
                        item["id"] = idx
                return data
            except json.JSONDecodeError:
                return []
    return []


def salva_lista_storico(storico: list):
    """Salva l'intera lista dello storico ordinata per data (più recente prima)."""
    storico.sort(key=lambda x: x["data"], reverse=True)
    with open(FILE_STORICO, "w", encoding="utf-8") as f:
        json.dump(storico, f, ensure_ascii=False, indent=2)


def salva_scontrino(negozio: str, data: str, totale: float):
    """Aggiunge uno scontrino allo storico."""
    storico = carica_storico()
    nuovo_id = max([item.get("id", 0) for item in storico], default=0) + 1
    storico.append({"id": nuovo_id, "negozio": negozio, "data": data, "totale": totale})
    salva_lista_storico(storico)


# --- FUNZIONE GENERAZIONE PDF ---
def genera_pdf_storico(storico: list) -> bytes:
    """Crea un documento PDF formattato contenente lo storico degli scontrini."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    title = Paragraph("<b>Report Generale Scontrini</b>", styles["Heading1"])
    story.append(title)

    data_generazione = Paragraph(
        f"<i>Generato il: {datetime.now().strftime('%d/%m/%Y alle %H:%M')}</i>", styles["Normal"]
    )
    story.append(data_generazione)
    story.append(Spacer(1, 15))

    table_data = [["Data", "Esercente / Negozio", "Importo (€)"]]
    totale_complessivo = 0.0

    for item in storico:
        table_data.append([item["data"], item["negozio"], f"€ {item['totale']:.2f}"])
        totale_complessivo += item["totale"]

    table_data.append(["TOTALE COMPLESSIVO", "", f"€ {totale_complessivo:.2f}"])

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
        ("SPAN", (0, -1), (1, -1)),
    ])

    table = Table(table_data, colWidths=[100, 300, 120])
    table.setStyle(table_style)
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# --- INTERFACCIA APP STREAMLIT ---
tab1, tab2, tab3 = st.tabs(["📷 Scansiona con Camera", "✍️ Inserimento Manuale", "📊 Storico & Export PDF"])

# TAB 1: ACQUISIZIONE CON CAMERA
with tab1:
    if "camera_attiva" not in st.session_state:
        st.session_state["camera_attiva"] = False

    col_cam1, col_cam2 = st.columns([1, 1])

    with col_cam1:
        if st.button("📷 Attiva Fotocamera", use_container_width=True):
            st.session_state["camera_attiva"] = True

    with col_cam2:
        if st.session_state["camera_attiva"]:
            if st.button("🚫 Disattiva Fotocamera", use_container_width=True):
                st.session_state["camera_attiva"] = False
                st.rerun()

    foto_scattata = None
    if st.session_state["camera_attiva"]:
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
                    data_finale = (
                        dati.data
                        if dati.data
                        else datetime.now().strftime("%Y-%m-%d")
                    )

                    salva_scontrino(dati.nome_negozio, data_finale, dati.totale_euro)

                    st.success("Scontrino analizzato e salvato!")
                    st.metric("Totale Euro", f"€ {dati.totale_euro:.2f}")
                    st.write(f"**Negozio:** {dati.nome_negozio}")
                    st.write(f"**Data registrata:** {data_finale}")
                else:
                    st.error(f"Si è verificato un errore durante l'analisi: {ultimo_errore}")

# TAB 2: INSERIMENTO MANUALE
with tab2:
    st.subheader("Inserisci una nuova voce manualmente")

    with st.form("form_inserimento_manuale", clear_on_submit=True):
        m_negozio = st.text_input("Nome Negozio / Esercente", placeholder="Es. Bar Centrale")
        m_data = st.date_input("Data dello scontrino", value=datetime.now())
        m_totale = st.number_input("Importo Totale (€)", min_value=0.01, step=0.10, format="%.2f")

        submit_manuale = st.form_submit_button("➕ Aggiungi allo Storico", type="primary")

        if submit_manuale:
            if m_negozio.strip() == "":
                st.error("Inserisci il nome del negozio.")
            else:
                data_str = m_data.strftime("%Y-%m-%d")
                salva_scontrino(m_negozio, data_str, float(m_totale))
                st.success(f"Aggiunto con successo: **{m_negozio}** - € {m_totale:.2f} ({data_str})")

# TAB 3: STORICO, MODIFICA, CANCELLAZIONE & PDF
with tab3:
    storico_attuale = carica_storico()

    if storico_attuale:
        st.subheader("Elenco Scontrini Registrati")

        totale_speso = sum(item["totale"] for item in storico_attuale)
        st.metric("Totale Spesa Accumulata", f"€ {totale_speso:.2f}")

        st.divider()

        scontrino_da_rimuovere = None
        scontrino_modificato = False

        for idx, item in enumerate(storico_attuale):
            col_info, col_modifica, col_elimina = st.columns([3, 1, 1])

            with col_info:
                st.write(f"📅 **{item['data']}** | 🏪 **{item['negozio']}** | 💶 **€ {item['totale']:.2f}**")

            with col_modifica:
                if st.button("✏️ Modifica", key=f"edit_{item['id']}"):
                    st.session_state[f"editing_{item['id']}"] = not st.session_state.get(f"editing_{item['id']}", False)

            with col_elimina:
                if st.button("🗑️ Elimina", key=f"del_{item['id']}", type="secondary"):
                    scontrino_da_rimuovere = item["id"]

            if st.session_state.get(f"editing_{item['id']}", False):
                with st.form(key=f"form_edit_{item['id']}"):
                    nuovo_negozio = st.text_input("Negozio", value=item["negozio"])
                    nuova_data = st.text_input("Data (YYYY-MM-DD)", value=item["data"])
                    nuovo_totale = st.number_input("Totale (€)", value=float(item["totale"]), step=0.1)

                    if st.form_submit_button("💾 Salva Modifiche"):
                        item["negozio"] = nuovo_negozio
                        item["data"] = nuova_data
                        item["totale"] = nuovo_totale
                        scontrino_modificato = True
                        st.session_state[f"editing_{item['id']}"] = False

            st.divider()

        if scontrino_da_rimuovere is not None:
            storico_attuale = [x for x in storico_attuale if x["id"] != scontrino_da_rimuovere]
            salva_lista_storico(storico_attuale)
            st.success("Scontrino eliminato con successo!")
            st.rerun()

        if scontrino_modificato:
            salva_lista_storico(storico_attuale)
            st.success("Modifiche salvate con successo!")
            st.rerun()

        pdf_bytes = genera_pdf_storico(storico_attuale)
        st.download_button(
            label="📄 Scarica Report PDF",
            data=pdf_bytes,
            file_name=f"report_scontrini_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            type="primary",
        )
    else:
        st.info("Nessuno scontrino presente nello storico. Scansiona una foto o inserisci una voce manualmente.")
