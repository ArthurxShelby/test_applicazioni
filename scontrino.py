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
st.set_page_config(page_title="Gestione Bilancio & Scontrini", layout="centered")
st.title("🧾 Gestione Entrate, Uscite e PDF")

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
                    if "tipo" not in item:
                        item["tipo"] = "Uscita"  # Default per compatibilità passata
                return data
            except json.JSONDecodeError:
                return []
    return []


def salva_lista_storico(storico: list):
    """Salva l'intera lista dello storico ordinata per data (più recente prima)."""
    storico.sort(key=lambda x: x["data"], reverse=True)
    with open(FILE_STORICO, "w", encoding="utf-8") as f:
        json.dump(storico, f, ensure_ascii=False, indent=2)


def salva_movimento(negozio: str, data: str, totale: float, tipo: str = "Uscita"):
    """Aggiunge una voce (Entrata/Uscita) allo storico."""
    storico = carica_storico()
    nuovo_id = max([item.get("id", 0) for item in storico], default=0) + 1
    storico.append({
        "id": nuovo_id,
        "negozio": negozio,
        "data": data,
        "totale": totale,
        "tipo": tipo
    })
    salva_lista_storico(storico)


# --- FUNZIONE GENERAZIONE PDF ---
def genera_pdf_storico(storico: list) -> bytes:
    """Crea un documento PDF formattato con saldo, entrate e uscite."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    title = Paragraph("<b>Report Bilancio: Entrate e Uscite</b>", styles["Heading1"])
    story.append(title)

    data_generazione = Paragraph(
        f"<i>Generato il: {datetime.now().strftime('%d/%m/%Y alle %H:%M')}</i>", styles["Normal"]
    )
    story.append(data_generazione)
    story.append(Spacer(1, 15))

    tot_entrate = sum(item["totale"] for item in storico if item.get("tipo") == "Entrata")
    tot_uscite = sum(item["totale"] for item in storico if item.get("tipo", "Uscita") == "Uscita")
    saldo = tot_entrate - tot_uscite

    table_data = [["Data", "Descrizione / Negozio", "Tipo", "Importo (€)"]]

    for item in storico:
        tipo = item.get("tipo", "Uscita")
        segno = "+" if tipo == "Entrata" else "-"
        table_data.append([
            item["data"],
            item["negozio"],
            tipo,
            f"{segno} € {item['totale']:.2f}"
        ])

    table_data.append(["TOTALE ENTRATE", "", "", f"+ € {tot_entrate:.2f}"])
    table_data.append(["TOTALE USCITE", "", "", f"- € {tot_uscite:.2f}"])
    table_data.append(["SALDO NETTO", "", "", f"€ {saldo:.2f}"])

    table_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#31333F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("GRID", (0, 0), (-1, -4), 0.5, colors.grey),
        ("BACKGROUND", (0, -3), (-1, -1), colors.HexColor("#F0F2F6")),
        ("FONTNAME", (0, -3), (-1, -1), "Helvetica-Bold"),
        ("SPAN", (0, -3), (2, -3)),
        ("SPAN", (0, -2), (2, -2)),
        ("SPAN", (0, -1), (2, -1)),
    ])

    table = Table(table_data, colWidths=[80, 240, 80, 120])
    table.setStyle(table_style)
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# --- INTERFACCIA APP STREAMLIT ---
tab1, tab2, tab3 = st.tabs(["📷 Scansiona Scontrino (Uscita)", "✍️ Inserimento Manuale", "📊 Bilancio & Export PDF"])

# TAB 1: ACQUISIZIONE CON CAMERA (Predefinito Uscita)
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

        if st.button("Analizza e Salva come Uscita", type="primary"):
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

                    salva_movimento(dati.nome_negozio, data_finale, dati.totale_euro, tipo="Uscita")

                    st.success("Scontrino registrato come Uscita!")
                    st.metric("Spesa Registrarla", f"€ {dati.totale_euro:.2f}")
                    st.write(f"**Negozio:** {dati.nome_negozio}")
                    st.write(f"**Data:** {data_finale}")
                else:
                    st.error(f"Si è verificato un errore durante l'analisi: {ultimo_errore}")

# TAB 2: INSERIMENTO MANUALE (Entrata o Uscita)
with tab2:
    st.subheader("Inserisci un'Entrata o un'Uscita")

    with st.form("form_inserimento_manuale", clear_on_submit=True):
        m_tipo = st.radio("Tipo Movimento", ["Uscita (Spesa)", "Entrata (Ricavo)"], horizontal=True)
        m_negozio = st.text_input("Descrizione / Esercente", placeholder="Es. Stipendio, Rimborso, Bar Centrale")
        m_data = st.date_input("Data", value=datetime.now())
        m_totale = st.number_input("Importo Totale (€)", min_value=0.01, step=0.10, format="%.2f")

        submit_manuale = st.form_submit_button("➕ Salva Movimento", type="primary")

        if submit_manuale:
            if m_negozio.strip() == "":
                st.error("Inserisci una descrizione o il nome dell'esercente.")
            else:
                tipo_str = "Entrata" if "Entrata" in m_tipo else "Uscita"
                data_str = m_data.strftime("%Y-%m-%d")
                salva_movimento(m_negozio, data_str, float(m_totale), tipo=tipo_str)
                st.success(f"Registrata {tipo_str}: **{m_negozio}** - € {m_totale:.2f} ({data_str})")

# TAB 3: BILANCIO IN TEMPO REALE, MODIFICA & PDF
with tab3:
    storico_attuale = carica_storico()

    if storico_attuale:
        st.subheader("📊 Bilancio in Tempo Reale")

        # Calcolo Entrate, Uscite e Saldo
        tot_entrate = sum(item["totale"] for item in storico_attuale if item.get("tipo") == "Entrata")
        tot_uscite = sum(item["totale"] for item in storico_attuale if item.get("tipo", "Uscita") == "Uscita")
        saldo = tot_entrate - tot_uscite

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("🟢 Entrate Totali", f"€ {tot_entrate:.2f}")
        col_m2.metric("🔴 Uscite Totali", f"€ {tot_uscite:.2f}")
        col_m3.metric("⚖️ Saldo Netto", f"€ {saldo:.2f}")

        st.divider()
        st.subheader("Elenco Movimenti")

        movimento_da_rimuovere = None
        movimento_modificato = False

        for idx, item in enumerate(storico_attuale):
            tipo = item.get("tipo", "Uscita")
            colore_ico = "🟢" if tipo == "Entrata" else "🔴"
            segno = "+" if tipo == "Entrata" else "-"

            col_info, col_modifica, col_elimina = st.columns([3, 1, 1])

            with col_info:
                st.write(
                    f"📅 **{item['data']}** | {colore_ico} **{tipo}** | "
                    f"🏪 **{item['negozio']}** | **{segno} € {item['totale']:.2f}**"
                )

            with col_modifica:
                if st.button("✏️ Modifica", key=f"edit_{item['id']}"):
                    st.session_state[f"editing_{item['id']}"] = not st.session_state.get(f"editing_{item['id']}", False)

            with col_elimina:
                if st.button("🗑️ Elimina", key=f"del_{item['id']}", type="secondary"):
                    movimento_da_rimuovere = item["id"]

            if st.session_state.get(f"editing_{item['id']}", False):
                with st.form(key=f"form_edit_{item['id']}"):
                    nuovo_tipo = st.selectbox("Tipo", ["Uscita", "Entrata"], index=0 if tipo == "Uscita" else 1)
                    nuovo_negozio = st.text_input("Descrizione/Negozio", value=item["negozio"])
                    nuova_data = st.text_input("Data (YYYY-MM-DD)", value=item["data"])
                    nuovo_totale = st.number_input("Totale (€)", value=float(item["totale"]), step=0.1)

                    if st.form_submit_button("💾 Salva Modifiche"):
                        item["tipo"] = nuovo_tipo
                        item["negozio"] = nuovo_negozio
                        item["data"] = nuova_data
                        item["totale"] = nuovo_totale
                        movimento_modificato = True
                        st.session_state[f"editing_{item['id']}"] = False

            st.divider()

        if movimento_da_rimuovere is not None:
            storico_attuale = [x for x in storico_attuale if x["id"] != movimento_da_rimuovere]
            salva_lista_storico(storico_attuale)
            st.success("Movimento eliminato con successo!")
            st.rerun()

        if movimento_modificato:
            salva_lista_storico(storico_attuale)
            st.success("Modifiche salvate con successo!")
            st.rerun()

        pdf_bytes = genera_pdf_storico(storico_attuale)
        st.download_button(
            label="📄 Scarica Report PDF Bilancio",
            data=pdf_bytes,
            file_name=f"report_bilancio_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            type="primary",
        )
    else:
        st.info("Nessun movimento registrato. Scansiona uno scontrino o aggiungi una voce manualmente.")
