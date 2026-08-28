from decimal import Decimal
import sqlite3
from tabulate import tabulate  # Opzionale per tabelle pulite, usa print base se preferisci


def inizializza_db():
  conn = sqlite3.connect("contabilita_bancomat.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS transazioni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            tipo TEXT NOT NULL, -- 'ENTRATA' o 'USCITA'
            importo TEXT NOT NULL, -- Usiamo TEXT per Decimal
            esercente TEXT,
            categoria TEXT,
            scontrino_conservato INTEGER DEFAULT 0 -- 0 = No, 1 = Sì
        )
    """)
  conn.commit()
  conn.close()


def aggiungi_transazione(
    data, tipo, importo, esercente, categoria, scontrino_conservato
):
  conn = sqlite3.connect("contabilita_bancomat.db")
  cursor = conn.cursor()
  # Convertiamo in Decimal e stringa per precisione finanziaria
  valore = str(Decimal(str(importo)).quantize(Decimal("0.01")))
  cursor.execute(
      """
        INSERT INTO transazioni (data, tipo, importo, esercente, categoria, scontrino_conservato)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
      (
          data,
          tipo.upper(),
          valore,
          esercente,
          categoria,
          scontrino_conservato,
      ),
  )
  conn.commit()
  conn.close()
  print("Transazione registrata con successo.")


def riconciliazione_mensile(mese, anno):
  conn = sqlite3.connect("contabilita_bancomat.db")
  cursor = conn.cursor()
  prefisso_data = f"{anno}-{mese:02d}"

  cursor.execute(
      """
        SELECT tipo, importo, esercente, scontrino_conservato 
        FROM transazioni 
        WHERE data LIKE ?
    """,
      (f"{prefisso_data}%",),
  )

  risultati = cursor.fetchall()
  conn.close()

  totale_entrate = Decimal("0.00")
  totale_uscite = Decimal("0.00")
  mancanti_scontrino = []

  for tipo, importo, esercente, scontrino in risultati:
    val = Decimal(importo)
    if tipo == "ENTRATA":
      totale_entrate += val
    elif tipo == "USCITA":
      totale_uscite += val
      if scontrino == 0:
        mancanti_scontrino.append((esercente, val))

  saldo = totale_entrate - totale_uscite

  print(f"\n--- RICONCILIAZIONE MENSILE: {prefisso_data} ---")
  print(f"Totale Entrate: € {totale_entrate}")
  print(f"Totale Uscite:  € {totale_uscite}")
  print(f"Saldo Netto:    € {saldo}")

  if mancanti_scontrino:
    print(
        "\nATTENZIONE: Le seguenti uscite non hanno uno scontrino abbinato:"
    )
    for esc, imp in mancanti_scontrino:
      print(f" - {esc}: € {imp}")
  else:
    print(
        "\nOttimo! Tutte le uscite del mese hanno uno scontrino registrato."
    )


if __name__ == "__main__":
  inizializza_db()
  # Esempio di utilizzo rapido:
  # aggiungi_transazione("2026-08-01", "ENTRATA", "1500.00", "Azienda", "Stipendio", 1)
  # aggiungi_transazione("2026-08-05", "USCITA", "45.50", "Supermercato", "Spesa", 1)
  # aggiungi_transazione("2026-08-10", "USCITA", "12.00", "Bar", Colazione, 0)
  # riconciliazione_mensile(8, 2026)
