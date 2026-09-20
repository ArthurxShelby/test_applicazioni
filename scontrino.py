import os
import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel, Field

# Configurazione della pagina Streamlit
st.set_page_config(page_title="Lettore Scontrini", layout="centered")
st.title("🧾 Estrazione Totale Scontrino")


# Definizione dello schema dati per l'output strutturato
class ScontrinoData(BaseModel):
    nome_negozio: str = Field(description="Nome dell'esercente")
    data: str = Field(description="Data dello scontrino (YYYY-MM-DD)")
    totale_euro: float = Field(
        description="Importo totale finale pagato in Euro"
    )


# Componente per il caricamento del file
uploaded_file = st.file_uploader(
    "Carica la foto dello scontrino", type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    # Mostra l'immagine caricata
    immagine = Image.open(uploaded_file)
    st.image(immagine, caption="Scontrino caricato", use_container_width=True)

    if st.button("Analizza Scontrino", type="primary"):
        with st.spinner("Analisi in corso con Gemini..."):
            try:
                # Inizializzazione del client Gemini
                client = genai.Client()

                # Configurazione della generazione con schema JSON
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ScontrinoData,
                    temperature=0.1,
                )

                prompt = "Analizza questo scontrino ed estrai nome negozio, data e totale finale in euro."

                # Chiamata al modello multimodale
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[immagine, prompt],
                    config=config,
                )

                # Parsing dei dati ottenuti
                dati: ScontrinoData = response.parsed

                # Visualizzazione dei risultati
                st.success("Estrazione completata!")
                st.metric("Totale Euro", f"€ {dati.totale_euro:.2f}")
                st.write(f"**Negozio:** {dati.nome_negozio}")
                st.write(f"**Data:** {dati.data}")

            except Exception as e:
                st.error(f"Si è verificato un errore durante l'analisi: {e}")
