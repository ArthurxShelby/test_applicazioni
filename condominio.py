import io
import os
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import streamlit as st
from supabase import create_client

# Configurazione della pagina
st.set_page_config(
    page_title="Gestione Spese Condominiali", page_icon="🏢", layout="wide"
)

# --- CONFIGURAZIONE SUPABASE DA SECRETS ---
try:
  SUPABASE_URL = (st.secrets.get("SUPABASE_URL") or st.secrets["supabase"]["SUPABASE_URL"]).strip()
  SUPABASE_KEY = (st.secrets.get("SUPABASE_KEY") or st.secrets["supabase"]["SUPABASE_KEY"]).strip()
except Exception:
  st.error("Configurazione Supabase mancante nei Secrets di Streamlit!")
  st.stop()

# Inizializzazione client Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

APP_NAMES = [
    "ESPOSITO",
    "MARANGI",
    "LINCESSO",
    "FUSO",
    "PUCA",
    "BAVILA",
    "TESTA",
]


# --- FUNZIONI DI LETTURA E SCRITTURA SU SUPABASE ---
def carica_mq_da_supabase():
  try:
    response = supabase.table("condominio").select("*").execute()
    data = response.data
    if data and len(data) > 0:
      return {row["condominio"]: float(row["mq"]) for row in data}
  except Exception:
    pass
  return {
      "ESPOSITO": 70.0,
      "MARANGI": 75.0,
      "LINCESSO": 80.0,
      "FUSO": 85.0,
      "PUCA": 90.0,
      "BAVILA": 85.0,
      "TESTA": 85.0,
  }


def salva_mq_su_supabase(mq_dict):
  try:
    supabase.table("condominio").delete().gte("id", 0).execute()
  except Exception:
    pass
  for cond, mq in mq_dict.items():
    supabase.table("condominio").insert(
        {"condominio": cond, "mq": mq}
    ).execute()
  return True


def carica_riporti_da_supabase():
  try:
    response = supabase.table("riporti").select("*").execute()
    data = response.data
    if data and len(data) > 0:
      return {row["condominio"]: float(row["riporto"]) for row in data}
  except Exception:
    pass
  return {app: 0.0 for app in APP_NAMES}


def salva_riporti_su_supabase(riporti_dict):
  try:
    supabase.table("riporti").delete().gte("id", 0).execute()
  except Exception:
    pass
  for cond, rip in riporti_dict.items():
    supabase.table("riporti").insert(
        {"condominio": cond, "riporto": rip}
    ).execute()
  return True


def carica_fatture_da_supabase():
  try:
    response = supabase.table("fatture").select("*").execute()
    if response.data is not None:
      return pd.DataFrame(response.data)
  except Exception as e:
    st.error(f"Errore lettura tabella 'fatture': {e}")
  return pd.DataFrame(
      columns=[
          "id",
          "anno",
          "mese",
          "tipo",
          "fornitore",
          "imponibile",
          "iva",
          "totale",
          "file",
      ]
  )


def carica_pagamenti_da_supabase():
  for nome_tabella in ["pagamenti", "pagamneti"]:
    try:
      response = supabase.table(nome_tabella).select("*").execute()
      if response.data is not None:
        return pd.DataFrame(response.data)
    except Exception:
      continue
  return pd.DataFrame(
      columns=[
          "id",
          "condominio",
          "fattura_id",
          "data_pagamento",
          "importo_da_pagare",
          "importo_pagato",
          "accredito",
          "riporto",
      ]
  )


# --- INIZIALIZZAZIONE SESSION STATE ---
if "logged_in" not in st.session_state:
  st.session_state.logged_in = False

if "mq_appartamenti" not in st.session_state:
  st.session_state.mq_appartamenti = carica_mq_da_supabase()
if "riporti" not in st.session_state:
  st.session_state.riporti = carica_riporti_da_supabase()
if "fatture" not in st.session_state:
  st.session_state.fatture = carica_fatture_da_supabase()
if "pagamenti" not in st.session_state:
  st.session_state.pagamenti = carica_pagamenti_da_supabase()


def calcola_millesimi_da_mq(mq_dict):
  tot_mq = sum(mq_dict.values())
  if tot_mq <= 0:
    return {k: 0 for k in mq_dict}
  return {app: round((mq / tot_mq) * 1000, 2) for app, mq in mq_dict.items()}


# --- FUNZIONE PER GENERARE IL PDF ---
def genera_pdf_riparto(df_reparto, titolo_contesto):
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(buffer, pagesize=letter)
  elements = []

  styles = getSampleStyleSheet()
  title_style = ParagraphStyle(
      'TitleStyle', parent=styles['Heading1'], fontSize=15, alignment=1, spaceAfter=10
  )
  subtitle_style = ParagraphStyle(
      'SubtitleStyle', parent=styles['Normal'], fontSize=9, alignment=1, spaceAfter=15
  )

  elements.append(Paragraph("<b>RIEPILOGO RIPARTO SPESE CONDOMINIALI</b>", title_style))
  elements.append(Paragraph(f"Contesto: {titolo_contesto}", subtitle_style))
  elements.append(Spacer(1, 10))

  data = [list(df_reparto.columns)] + df_reparto.values.tolist()

  table = Table(data, colWidths=[110, 80, 110, 110, 110])
  table.setStyle(
      TableStyle([
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
      ])
  )

  elements.append(table)
  doc.build(elements)
  buffer.seek(0)
  return buffer.getvalue()


# --- SISTEMA DI LOGIN ---
def login_screen():
  st.title("🏢 Accesso Gestione Condominio")
  with st.form("login_form"):
    username = st.text_input("Nome Utente")
    password = st.text_input("Password", type="password")
    submit = st.form_submit_button("Accedi")

    if submit:
      if username == "admin" and password == "condominio2026":
        st.session_state.logged_in = True
        st.rerun()
      else:
        st.error("Credenziali non valide.")


if not st.session_state.logged_in:
  login_screen()
else:
  # --- BARRA LATERALE E NAVIGAZIONE ---
  st.sidebar.title("Menu Principale")
  menu = st.sidebar.selectbox(
      "Seleziona Sezione",
      [
          "Dashboard & Riepilogo",
          "Inserisci Fattura",
          "Storico e Dettaglio",
          "Gestione Millesimi & Riporti",
      ],
  )

  if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

  # Aggiornamento dati da Supabase
  st.session_state.fatture = carica_fatture_da_supabase()
  st.session_state.pagamenti = carica_pagamenti_da_supabase()
  st.session_state.mq_appartamenti = carica_mq_da_supabase()
  st.session_state.riporti = carica_riporti_da_supabase()

  df_fatture = st.session_state.fatture
  millesimi = calcola_millesimi_da_mq(st.session_state.mq_appartamenti)
  tot_millesimi = sum(millesimi.values())

  mese_map = {
      "Gennaio": 1, "Febbraio": 2, "Marzo": 3, "Aprile": 4, 
      "Maggio": 5, "Giugno": 6, "Luglio": 7, "Agosto": 8, 
      "Settembre": 9, "Ottobre": 10, "Novembre": 11, "Dicembre": 12
  }

  # --- 1. DASHBOARD & RIEPILOGO ---
  if menu == "Dashboard & Riepilogo":
    st.title("📊 Dashboard e Riparto Spese")

    if df_fatture.empty:
      st.warning("La tabella 'fatture' su Supabase risulta vuota.")
    else:
      df_sorted = df_fatture.copy()
      if 'mese' in df_sorted.columns:
        df_sorted['mese_num'] = df_sorted['mese'].map(mese_map)
        df_sorted = df_sorted.sort_values(by=['anno', 'mese_num'], ascending=[False, False])

      col_f1, col_f2 = st.columns(2)
      with col_f1:
        anni_disponibili = sorted(df_fatture["anno"].unique(), reverse=True) if "anno" in df_fatture.columns else []
        selected_anno = st.selectbox(
            "Filtra per Anno Fiscale",
            ["Tutti gli anni (da 2022)"] + list(anni_disponibili),
        )
      with col_f2:
        selected_tipo = st.selectbox(
            "Filtra per Tipologia Spesa",
            ["Tutte le tipologie", "Energia Elettrica", "Gasolio"],
        )

      df_filtered = df_sorted.copy()
      if selected_anno != "Tutti gli anni (da 2022)":
        df_filtered = df_filtered[df_filtered["anno"] == selected_anno]
      if selected_tipo != "Tutte le tipologie":
        df_filtered = df_filtered[df_filtered["tipo"] == selected_tipo]

      st.markdown("---")
      st.subheader("Selezione Fattura Specifica")

      if df_filtered.empty:
        st.warning("Nessuna fattura trovata con i filtri selezionati.")
        tot_imp, tot_iva, tot_complessivo = 0.0, 0.0, 0.0
        descrizione_contesto = "Nessuna fattura"
        file_selezionato = None
      else:
        opzioni_fatture = ["-- Tutte le fatture filtrate --"]
        for _, row in df_filtered.iterrows():
          desc = (
              f"ID: {row['id']} | {row['anno']} - {row['mese']} |"
              f" {row['tipo']} | {row['fornitore']} | Tot: €"
              f" {row['totale']:,.2f}"
          )
          opzioni_fatture.append(desc)

        selected_option = st.selectbox(
            "Scegli una singola fattura (esclude le altre)", opzioni_fatture
        )

        if selected_option == "-- Tutte le fatture filtrate --":
          df_calcolo = df_filtered
          descrizione_contesto = f"Anno: {selected_anno} | Tipo: {selected_tipo}"
          file_selezionato = None
        else:
          id_estratto = int(selected_option.split("|")[0].replace("ID:", "").strip())
          df_calcolo = df_filtered[df_filtered["id"] == id_estratto]
          descrizione_contesto = f"Fattura Singola ID {id_estratto}"
          
          row_selezionata = df_calcolo.iloc[0]
          file_selezionato = row_selezionata.get("file", None)

        tot_imp = df_calcolo["imponibile"].sum()
        tot_iva = df_calcolo["iva"].sum()
        tot_complessivo = df_calcolo["totale"].sum()

      # --- VISUALIZZAZIONE FILE FATTURA DI RIFERIMENTO E VISUALIZZATORE PDF ---
      if selected_option != "-- Tutte le fatture filtrate --" and not df_filtered.empty:
        st.markdown("### 📎 File Fattura Collegato")
        if file_selezionato and str(file_selezionato).strip() != "" and str(file_selezionato).lower() != "nan":
          st.success(f"File allegato registrato: **{file_selezionato}**")
          
          # Controllo se il file esiste localmente nella cartella di esecuzione o se è un percorso valido
          nome_f_str = str(file_selezionato).strip()
          if os.path.exists(nome_f_str):
            with open(nome_f_str, "rb") as f_pdf:
              pdf_data = f_pdf.read()
            st.download_button(
                label="📥 Scarica / Apri PDF Collegato",
                data=pdf_data,
                file_name=nome_f_str,
                mime="application/pdf",
                key="download_pdf_collegato",
                use_container_width=True
            )
          else:
            # Se il file non è locale ma è registrato come nome, informiamo l'utente
            st.info("Il file è associato nel database. Se è stato caricato tramite storage remoto o non si trova nella cartella locale, assicurati che sia accessibile o ricaricalo se necessario.")
        else:
          st.info("Nessun file PDF associato a questa fattura.")

      st.markdown("---")

      col1, col2, col3 = st.columns(3)
      col1.metric("Totale Imponibile", f"€ {tot_imp:,.2f}")
      col2.metric("Totale IVA", f"€ {tot_iva:,.2f}")
      col3.metric("Totale Generale", f"€ {tot_complessivo:,.2f}")

      st.markdown("---")
      st.subheader("Tabella di Riparto per Condomino")

      reparto_data = []
      sum_millesimi = 0.0
      sum_imp = 0.0
      sum_iva = 0.0
      sum_tot = 0.0

      for app, mil in millesimi.items():
        quota_imp = tot_imp * (mil / tot_millesimi) if tot_millesimi > 0 else 0
        quota_iva = tot_iva * (mil / tot_millesimi) if tot_millesimi > 0 else 0
        quota_tot = tot_complessivo * (mil / tot_millesimi) if tot_millesimi > 0 else 0

        sum_millesimi += mil
        sum_imp += quota_imp
        sum_iva += quota_iva
        sum_tot += quota_tot

        reparto_data.append(
            {
                "Condomino": app,
                "Millesimi": mil,
                "Quota Imponibile (€)": round(quota_imp, 2),
                "Quota IVA (€)": round(quota_iva, 2),
                "Quota Totale (€)": round(quota_tot, 2),
            }
        )

      reparto_data.append(
          {
              "Condomino": "TOTALE",
              "Millesimi": round(sum_millesimi, 2),
              "Quota Imponibile (€)": round(sum_imp, 2),
              "Quota IVA (€)": round(sum_iva, 2),
              "Quota Totale (€)": round(sum_tot, 2),
          }
      )

      df_reparto = pd.DataFrame(reparto_data)
      st.dataframe(df_reparto, use_container_width=True)

      col_pdf1, _ = st.columns([1, 2])
      with col_pdf1:
        pdf_bytes = genera_pdf_riparto(df_reparto, descrizione_contesto)
        st.download_button(
            label="📥 Scarica / Stampa PDF Riparto",
            data=pdf_bytes,
            file_name="riparto_spese_condominio.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

      st.markdown("---")

      # --- SEZIONE GESTIONE INTROITI E PAGAMENTI ---
      st.subheader("💳 Gestione Introiti e Pagamenti Utenti")
      
      cond_attivo = st.selectbox(
          "Seleziona Condomino (per Pagamento o Storico)", 
          APP_NAMES, 
          key="reg_condomino"
      )

      with st.form("form_registra_pagamento"):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
          st.write(f"Stai registrando un pagamento per: **{cond_attivo}**")
          
          opzioni_fatture_pagamento = []
          for _, row in df_sorted.iterrows():
            opzioni_fatture_pagamento.append(
                f"ID: {row['id']} | {row['anno']} - {row['mese']} |"
                f" {row['tipo']} | {row['fornitore']} | Totale: €"
                f" {row['totale']:,.2f}"
            )

          if not opzioni_fatture_pagamento:
            fattura_scelta_str = None
          else:
            fattura_scelta_str = st.selectbox(
                "Seleziona Fattura di Riferimento", opzioni_fatture_pagamento, key="reg_fattura"
            )

        with col_p2:
          importo_versato = st.number_input(
              "Importo Pagato (€)", min_value=0.0, format="%.2f", key="reg_importo"
          )
          data_versamento = st.text_input(
              "Data o Mese di Registrazione Pagamento", value="Agosto 2026", key="reg_data"
          )

        submit_pagamento = st.form_submit_button("Registra Pagamento su Supabase")

        if submit_pagamento:
          if not fattura_scelta_str:
            st.warning("Seleziona una fattura valida.")
          else:
            id_fattura_collegata = int(fattura_scelta_str.split("|")[0].replace("ID:", "").strip())
            row_fattura = df_fatture[df_fatture["id"] == id_fattura_collegata].iloc[0]
            totale_singola_fattura = float(row_fattura["totale"])
            
            mil_condomino = millesimi.get(cond_attivo, 0.0)
            quota_dovuta_esatta = (totale_singola_fattura * (mil_condomino / tot_millesimi)) if tot_millesimi > 0 else 0.0
            
            st.session_state.pagamenti = carica_pagamenti_da_supabase()
            df_pag_corrente = st.session_state.pagamenti
            
            accredito_precedente = 0.0
            if not df_pag_corrente.empty:
              df_cond_prec = df_pag_corrente[df_pag_corrente["condominio"] == cond_attivo]
              if not df_cond_prec.empty:
                ultimo_record = df_cond_prec.iloc[-1]
                accredito_precedente = float(ultimo_record.get("riporto", 0.0))

            importo_versato_f = float(importo_versato)
            riporto_generato = round(importo_versato_f - quota_dovuta_esatta + accredito_precedente, 2)

            nuovo_pagamento = {
                "condominio": cond_attivo,
                "fattura_id": id_fattura_collegata,
                "data_pagamento": data_versamento,
                "importo_da_pagare": round(quota_dovuta_esatta, 2),
                "importo_pagato": importo_versato_f,
                "accredito": round(accredito_precedente, 2),
                "riporto": riporto_generato,
            }

            try:
              supabase.table("pagamenti").insert(nuovo_pagamento).execute()
            except Exception:
              supabase.table("pagamneti").insert(nuovo_pagamento).execute()

            st.session_state.pagamenti = carica_pagamenti_da_supabase()
            st.success(f"Pagamento registrato per {cond_attivo}!")
            st.rerun()

      # --- TABELLA STORICO PAGAMENTI ---
      st.markdown("### 📂 Storico Pagamenti Ricevuti")
      df_pag = st.session_state.pagamenti
      df_fatture_all = carica_fatture_da_supabase() 
      
      if not df_pag.empty:
        if not df_fatture_all.empty and "anno" in df_fatture_all.columns:
            df_fatture_all['rif_fattura'] = df_fatture_all['anno'].astype(str) + " - " + df_fatture_all['mese']
            lookup_fat = df_fatture_all.set_index('id')['rif_fattura']
            df_pag['Riferimento'] = df_pag['fattura_id'].map(lookup_fat).fillna("N/A")
        else:
            df_pag['Riferimento'] = "N/A"

        mostra_tutti = st.checkbox("Mostra storico completo di tutti i condomini", value=False)
        df_visual = df_pag.copy()
        
        if not mostra_tutti:
            df_visual = df_visual[df_visual["condominio"] == cond_attivo]
            st.write(f"Visualizzazione filtrata per: **{cond_attivo}**")
        else:
            st.write("Visualizzazione: **Storico Completo**")
        
        col_ordine = ["id", "condominio", "Riferimento", "data_pagamento", "importo_da_pagare", "importo_pagato", "accredito", "riporto"]
        col_presenti = [c for c in col_ordine if c in df_visual.columns]
        st.dataframe(df_visual[col_presenti], use_container_width=True)
      else:
        st.info("Nessun pagamento registrato finora.")

      # --- ELIMINAZIONE PAGAMENTO ---
      st.markdown("---")
      st.subheader(f"🗑️ Elimina Pagamento per {cond_attivo}")
      
      df_pag_da_eliminare = df_pag[df_pag["condominio"] == cond_attivo] if not df_pag.empty else pd.DataFrame()
      if not df_pag_da_eliminare.empty:
        opzioni_pagamenti_elimina = []
        for _, row in df_pag_da_eliminare.iterrows():
          opzioni_pagamenti_elimina.append(f"ID: {row['id']} | Rif: {row.get('Riferimento', 'N/A')} | Importo: € {float(row['importo_pagato']):,.2f}")

        pagamento_scelto = st.selectbox("Seleziona pagamento da rimuovere", opzioni_pagamenti_elimina, key="select_elimina")
        
        if st.button("Conferma Eliminazione"):
          id_da_el = int(pagamento_scelto.split("|")[0].replace("ID:", "").strip())
          try:
            supabase.table("pagamenti").delete().eq("id", id_da_el).execute()
          except Exception:
            supabase.table("pagamneti").delete().eq("id", id_da_el).execute()
          st.session_state.pagamenti = carica_pagamenti_da_supabase()
          st.success("Pagamento eliminato!")
          st.rerun()
      else:
        st.info(f"Nessun pagamento trovato per {cond_attivo}.")

  # --- 2. INSERISCI O AGGIORNA FATTURA ---
  elif menu == "Inserisci Fattura":
    st.title("📝 Inserimento Nuova Fattura")

    modalita_form = st.radio(
        "Seleziona Operazione",
        ["Inserisci Nuova Fattura", "Associa PDF a Fattura Esistente"]
    )

    if modalita_form == "Inserisci Nuova Fattura":
      with st.form("form_fattura_nuova"):
        col1, col2 = st.columns(2)
        with col1:
          anno = st.selectbox("Anno", options=list(range(2022, 2028)), index=4)
          mese = st.selectbox("Mese", ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"])
          tipo = st.selectbox("Tipologia Spesa", ["Energia Elettrica", "Gasolio"])
        with col2:
          fornitore = st.text_input("Fornitore")
          imponibile = st.number_input("Imponibile (€)", min_value=0.0, format="%.2f")
          iva = st.number_input("IVA (€)", min_value=0.0, format="%.2f")

        st.markdown("---")
        st.write("Gestione File PDF")
        scelta_file = st.radio(
            "Gestione File PDF",
            ["Carica nuovo file PDF", "Puntare a un file già inserito in precedenza"],
            label_visibility="collapsed"
        )

        uploaded_file = None
        file_esistente_selezionato = ""

        if scelta_file == "Carica nuovo file PDF":
          st.markdown("Carica File PDF Fattura")
          uploaded_file = st.file_uploader("Carica File PDF Fattura", type=["pdf"], label_visibility="collapsed")
        else:
          file_disponibili = []
          if not df_fatture.empty and "file" in df_fatture.columns:
            file_disponibili = [str(f) for f in df_fatture["file"].dropna().unique() if str(f).strip() != "" and str(f).lower() != "nan"]
          
          if file_disponibili:
            file_esistente_selezionato = st.selectbox("Seleziona file esistente", file_disponibili)
          else:
            st.info("Nessun file precedentemente registrato trovato nel database.")

        submit_fat = st.form_submit_button("Salva Fattura su Supabase")
        if submit_fat:
          if scelta_file == "Carica nuovo file PDF":
            nome_file = uploaded_file.name if uploaded_file is not None else ""
            # Salvataggio locale opzionale del file caricato per permetterne l'apertura immediata
            if uploaded_file is not None:
              with open(uploaded_file.name, "wb") as f_out:
                f_out.write(uploaded_file.getbuffer())
          else:
            nome_file = file_esistente_selezionato

          nuova_fattura = {
              "anno": int(anno), 
              "mese": mese, 
              "tipo": tipo, 
              "fornitore": fornitore, 
              "imponibile": float(imponibile), 
              "iva": float(iva), 
              "totale": float(imponibile + iva),
              "file": nome_file
          }
          supabase.table("fatture").insert(nuova_fattura).execute()
          st.session_state.fatture = carica_fatture_da_supabase()
          st.success("Nuova fattura salvata con successo!")
          st.rerun()

    else:
      with st.form("form_aggiorna_pdf"):
        st.subheader("Associa PDF a Fattura Già Inserita")
        
        if df_fatture.empty:
          st.warning("Nessuna fattura presente nel database.")
          opzioni_esistenti = []
        else:
          opzioni_esistenti = []
          for _, row in df_fatture.iterrows():
            file_attuale = row.get("file", "Nessuno")
            opzioni_esistenti.append(
                f"ID: {row['id']} | {row['anno']} - {row['mese']} | {row['tipo']} | Fornitore: {row['fornitore']} | Tot: € {row['totale']:,.2f} [File attuale: {file_attuale}]"
            )

        fattura_target_str = st.selectbox("Seleziona la fattura da aggiornare", opzioni_esistenti if opzioni_esistenti else ["Nessuna fattura disponibile"])

        st.markdown("---")
        st.write("Gestione File PDF")
        scelta_aggiornamento_pdf = st.radio(
            "Gestione File PDF",
            ["Carica nuovo file PDF", "Puntare a un file già inserito in precedenza"],
            key="radio_aggiorna",
            label_visibility="collapsed"
        )

        up_file_agg = None
        file_scelto_esistente_agg = ""

        if scelta_aggiornamento_pdf == "Carica nuovo file PDF":
          st.markdown("Carica File PDF Fattura")
          up_file_agg = st.file_uploader("Carica File PDF Fattura", type=["pdf"], key="up_agg", label_visibility="collapsed")
        else:
          file_disponibili_agg = []
          if not df_fatture.empty and "file" in df_fatture.columns:
            file_disponibili_agg = [str(f) for f in df_fatture["file"].dropna().unique() if str(f).strip() != "" and str(f).lower() != "nan"]
          
          if file_disponibili_agg:
            file_scelto_esistente_agg = st.selectbox("Seleziona file esistente", file_disponibili_agg, key="sel_esistente_agg")
          else:
            st.info("Nessun file precedentemente registrato trovato nel database.")

        submit_agg = st.form_submit_button("Salva Fattura su Supabase")

        if submit_agg:
          if not opzioni_esistenti:
            st.warning("Seleziona una fattura valida.")
          else:
            id_da_aggiornare = int(fattura_target_str.split("|")[0].replace("ID:", "").strip())
            
            if scelta_aggiornamento_pdf == "Carica nuovo file PDF":
              nuovo_nome_file = up_file_agg.name if up_file_agg is not None else ""
              if up_file_agg is not None:
                with open(up_file_agg.name, "wb") as f_out:
                  f_out.write(up_file_agg.getbuffer())
            else:
              nuovo_nome_file = file_scelto_esistente_agg

            supabase.table("fatture").update({"file": nuovo_nome_file}).eq("id", id_da_aggiornare).execute()
            st.session_state.fatture = carica_fatture_da_supabase()
            st.success(f"PDF aggiornato con successo per la fattura ID {id_da_aggiornare}!")
            st.rerun()

  # --- 3. STORICO E DETTAGLIO ---
  elif menu == "Storico e Dettaglio":
    st.title("📂 Storico Fatture")
    st.dataframe(df_fatture, use_container_width=True)

  # --- 4. GESTIONE MILLESIMI & RIPORTI ---
  elif menu == "Gestione Millesimi & Riporti":
    st.title("⚙️ Gestione Metrature e Riporti")
    
    tab1, tab2 = st.tabs(["Metrature (MQ) & Millesimi", "Riporti Iniziali"])
    
    with tab1:
      st.subheader("Modifica Metrature Appartamenti")
      with st.form("form_mq"):
        nuovi_mq = {}
        c1, c2 = st.columns(2)
        for i, app in enumerate(APP_NAMES):
          val_attuale = st.session_state.mq_appartamenti.get(app, 70.0)
          col_target = c1 if i % 2 == 0 else c2
          nuovi_mq[app] = col_target.number_input(f"MQ {app}", min_value=1.0, value=val_attuale, format="%.1f", key=f"mq_{app}")
        
        if st.form_submit_button("Salva Metrature"):
          if salva_mq_su_supabase(nuovi_mq):
            st.session_state.mq_appartamenti = nuovi_mq
            st.success("Metrature aggiornate con successo!")
            st.rerun()

    with tab2:
      st.subheader("Modifica Riporti Iniziali (Debiti/Crediti)")
      with st.form("form_rip"):
        nuovi_riporti = {}
        c1, c2 = st.columns(2)
        for i, app in enumerate(APP_NAMES):
          val_attuale = st.session_state.riporti.get(app, 0.0)
          col_target = c1 if i % 2 == 0 else c2
          nuovi_riporti[app] = col_target.number_input(f"Riporto {app} (€)", value=val_attuale, format="%.2f", key=f"rip_{app}")
        
        if st.form_submit_button("Salva Riporti"):
          if salva_riporti_su_supabase(nuovi_riporti):
            st.session_state.riporti = nuovi_riporti
            st.success("Riporti aggiornati con successo!")
            st.rerun()
