from datetime import datetime
import os
import time
from typing import Optional
import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel, Field

# Configurazione della pagina Streamlit
st.set_page_config(page_title="Lettore Scontrini", layout="centered")
st.title("🧾 Scatta e Analizza Scontrino")


# Schema dei dati di output (con data opzionale)
class ScontrinoData(BaseModel):
    nome_negozio: str = Field(description="Nome dell'esercente")
    data: Optional[str] = Field(
        default=None,
        description="Data dello scontrino nel formato YYYY-MM-DD se ben visibile, altrimenti null",
    )
    totale_euro: float = Field(
        description="Importo totale finale pagato in Euro"
    )


# Acquisizione foto da fotocamera
foto_scattata = st.camera_input("Scatta una foto allo scontrino")

if foto_scattata is not None:
    immagine = Image.open(foto_scattata)

    if st.button("Analizza Scontrino", type="primary"):
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

            # Tentativo di chiamata API
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
                # Se la data non è presente nella foto, usa la data odierna
                data_finale = (
                    dati.data
                    if dati.data
                    else f"{datetime.now().strftime('%Y-%m-%d')} (Data odierna)"
                )

                st.success("Estrazione completata!")
                st.metric("Totale Euro", f"€ {dati.totale_euro:.2f}")
                st.write(f"**Negozio:** {dati.nome_negozio}")
                st.write(f"**Data:** {data_finale}")
            else:
                st.error(f"Si è verificato un errore durante l'analisi: {ultimo_errore}")
