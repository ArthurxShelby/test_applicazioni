import os
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel, Field


# 1. Definiamo lo schema JSON desiderato tramite Pydantic
class ScontrinoData(BaseModel):
    nome_negozio: str = Field(description="Nome o ragione sociale dell'esercente")
    data: str = Field(
        description="Data dello scontrino nel formato YYYY-MM-DD, se visibile"
    )
    totale_euro: float = Field(
        description="Importo totale finale pagato espresso in Euro (float con 2 decimali)"
    )
    valuta: str = Field(
        default="EUR", description="Codice ISO della valuta (es. EUR)"
    )


def estrai_totale_scontrino(percorso_immagine: str) -> ScontrinoData:
    # 2. Inizializziamo il client dell'SDK (legge automaticamente GEMINI_API_KEY)
    client = genai.Client()

    # 3. Carichiamo l'immagine dello scontrino
    try:
        immagine = Image.open(percorso_immagine)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Impossibile trovare l'immagine nel percorso: {percorso_immagine}"
        )

    # 4. Configuriamo la richiesta fornendo lo schema Pydantic
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ScontrinoData,
        temperature=0.1,  # Temperatura bassa per ridurre la creatività dell'AI
    )

    prompt = (
        "Analizza questa immagine di uno scontrino fiscale. "
        "Estrai il nome del negozio, la data e l'importo totale finale pagato espresso in euro."
    )

    # 5. Inviamo l'immagine e il prompt al modello vision (Gemini 2.5/3.5 Flash)
    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=[immagine, prompt], config=config
    )

    # 6. L'SDK deserializza automaticamente la risposta nello schema Pydantic fornito
    dati_estratte: ScontrinoData = response.parsed
    return dati_estratte


# === ESECUZIONE DI ESEMPIO ===
if __name__ == "__main__":
    file_scontrino = "scontrino.jpg"  # Inserisci il percorso della tua foto

    if os.path.exists(file_scontrino):
        risultato = estrai_totale_scontrino(file_scontrino)

        print("\n--- RISULTATO ESTRAZIONE ---")
        print(f"Negozio: {risultato.nome_negozio}")
        print(f"Data: {risultato.data}")
        print(f"Totale: {risultato.totale_euro:.2f} {risultato.valuta}")
    else:
        print(
            f"Aggiungi un'immagine 'scontrino.jpg' nella cartella corrente per testare il codice."
        )
