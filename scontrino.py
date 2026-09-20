import os
import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel, Field

# Configurazione della pagina Streamlit
st.set_page_config(page_title="Lettore Scontrini", layout="centered")
st.title("🧾 Scatta e Analizza Scontrino")


# Schema dei dati di output
class ScontrinoData(BaseModel):
    nome_negozio: str = Field(description="Nome dell'esercente")
    data: str = Field(description="Data dello scontrino (YYYY-MM-DD)")
    totale_euro: float = Field(
        description="Importo totale finale pagato in Euro"
    )


# Acquisizione foto da fotocamera
foto_scattata = st.camera_input("Scatta una foto allo scontrino")

if foto_scattata is not None:
    immagine = Image.open(foto_scattata)

    if st.button("Analizza Scontrino", type="primary"):
        with st.spinner("Analisi in corso con Gemini..."):
            try:
                # Inizializzazione del client
                client = genai.Client()

                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ScontrinoData,
                    temperature=0.1,
                )

                prompt = "Analizza questo scontrino ed estrai nome negozio, data e totale finale in euro."

                # Chiamata API con il modello attivo gemini-3.6-flash
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[immagine, prompt],
                    config=config,
                )

                dati: ScontrinoData = response.parsed

                st.success("Estrazione completata!")
                st.metric("Totale Euro", f"€ {dati.totale_euro:.2f}")
                st.write(f"**Negozio:** {dati.nome_negozio}")
                st.write(f"**Data:** {dati.data}")

            except Exception as e:
                st.error(f"Si è verificato un errore durante l'analisi: {e}")
