import os
import time
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
            # Elenco di modelli da provare in ordine di priorità
            modelli = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-1.5-flash"]
            dati = None
            ultimo_errore = None

            client = genai.Client()
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ScontrinoData,
                temperature=0.1,
            )
            prompt = "Analizza questo scontrino ed estrai nome negozio, data e totale finale in euro."

            # Tentativo di chiamata con retry e fallback su modelli alternativi
            for modello in modelli:
                for tentativo in range(2):  # Prova fino a 2 volte per modello
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
                            time.sleep(2)  # Attende 2 secondi prima di riprovare
                            continue
                        else:
                            break
                if dati is not None:
                    break

            if dati is not None:
                st.success("Estrazione completata!")
                st.metric("Totale Euro", f"€ {dati.totale_euro:.2f}")
                st.write(f"**Negozio:** {dati.nome_negozio}")
                st.write(f"**Data:** {dati.data}")
            else:
                st.error(f"Si è verificato un errore durante l'analisi: {ultimo_errore}")
