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
BUCKET_NAME = "fatture_pdf"

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
if "fatture" not in st.session_state:
  st.session_state.fatture = carica_fatture_da_supabase()
if "pagamenti" not in st.session_state:
  st.session_state.pagamenti = carica_pagamenti_da_supabase()


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

  elements.append(Paragraph("<b>RIEPILOGO RIPARTO SPESE CONDOMINIALI (su MQ)</b>", title_style))
  elements.append(Paragraph(f"Contesto: {titolo_contesto}", subtitle_style))
  elements.append(Spacer(1, 10))

  data = [list(df_reparto.columns)] + df_reparto.values.tolist()

  table = Table(data, colWidths=[100, 70, 70, 95, 95, 95])
  table.setStyle(
      TableStyle([
          ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
          ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
          ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
          ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
          ('FONTSIZE', (0, 0), (-1, 0), 8),
          ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
          ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#f8f9fa')),
          ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e2e8f0')),
          ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
          ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
          ('FONTSIZE', (0, 1), (-1, -1), 8),
          ('TOPPADDING', (0, 1), (-1, -1), 5),
          ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
      ])
  )

  elements.append(table)
  doc.build(elements)
  buffer.seek(0)
  return buffer.getvalue()


def genera_ricevuta_pagamento(row_pag, df_fatture_ref):
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=30, bottomMargin=30)
  styles = getSampleStyleSheet()
  title_style = ParagraphStyle('TitleReceipt', parent=styles['Heading1'], fontSize=16, alignment=1, spaceAfter=12, textColor=colors.HexColor('#2c3e50'))
  normal = ParagraphStyle('NormalReceipt', parent=styles['Normal'], fontSize=11, leading=16)
  small = ParagraphStyle('SmallReceipt', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.grey)

  condominio = row_pag.get('condominio','')
  data_pag = str(row_pag.get('data_pagamento',''))
  importo_pagato = float(row_pag.get('importo_pagato',0))
  importo_da_pagare = float(row_pag.get('importo_da_pagare',0))
  accredito = float(row_pag.get('accredito',0))
  riporto = float(row_pag.get('riporto',0))
  rif = row_pag.get('Riferimento','N/A')
  id_pag = row_pag.get('id','')

  fatt_id = row_pag.get('fattura_id')
  fornitore = ''
  tipo = ''
  tot_fatt = ''
  if not df_fatture_ref.empty and fatt_id in df_fatture_ref['id'].values:
    fr = df_fatture_ref[df_fatture_ref['id']==fatt_id].iloc[0]
    fornitore = str(fr.get('fornitore',''))
    tipo = str(fr.get('tipo',''))
    tot_fatt = f"€ {float(fr.get('totale',0)):,.2f}"

  elements = []
  elements.append(Paragraph("<b>RICEVUTA DI PAGAMENTO CONDOMINIALE</b>", title_style))
  elements.append(Spacer(1, 8))
  elements.append(Paragraph(f"Condominio di <b>{condominio}</b> - Ricevuta n. {id_pag}", normal))
  elements.append(Spacer(1, 12))

  data_table = [
    ["Data Versamento:", data_pag],
    ["Condomino:", condominio],
    ["Riferimento Fattura:", rif],
    ["Tipo Spesa / Fornitore:", f"{tipo} {('- ' + fornitore) if fornitore else ''}".strip()],
    ["Totale Fattura Originale:", tot_fatt],
    ["Quota Dovuta:", f"€ {importo_da_pagare:,.2f}"],
    ["Accredito Iniziale (riporto prec.):", f"€ {accredito:,.2f}"],
    ["Importo Versato:", f"€ {importo_pagato:,.2f}"],
    ["Riporto Generato (credito/debito):", f"€ {riporto:,.2f}"],
  ]
  t = Table(data_table, colWidths=[200, 280])
  t.setStyle(TableStyle([
      ('BACKGROUND', (0,0),(0,-1), colors.HexColor('#f1f5f9')),
      ('FONTNAME', (0,0),(0,-1), 'Helvetica-Bold'),
      ('ALIGN', (0,0),(-1,-1), 'LEFT'),
      ('FONTSIZE', (0,0),(-1,-1), 10),
      ('GRID', (0,0),(-1,-1), 0.5, colors.grey),
      ('TOPPADDING', (0,0),(-1,-1), 8),
      ('BOTTOMPADDING', (0,0),(-1,-1), 8),
  ]))
  elements.append(t)
  elements.append(Spacer(1, 20))

  saldo_text = ""
  if riporto > 0:
    saldo_text = f"Il pagamento risulta in <b>credito di € {riporto:,.2f}</b> che verrà riportato come accredito sul prossimo riparto."
  elif riporto < 0:
    saldo_text = f"Il pagamento risulta in <b>debito residuo di € {abs(riporto):,.2f}</b> da saldare."
  else:
    saldo_text = "Il pagamento salda esattamente la quota dovuta."

  elements.append(Paragraph(saldo_text, normal))
  elements.append(Spacer(1, 24))
  elements.append(Paragraph("Si attesta che in data indicata è stato ricevuto il versamento sopra descritto per la quota condominiale di riferimento, comprensivo di eventuale riporto precedente.", small))
  elements.append(Spacer(1, 30))
  elements.append(Paragraph("Firma Amministratore ______________________", normal))
  elements.append(Spacer(1, 12))
  elements.append(Paragraph(f"Documento generato automaticamente il {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}", small))

  doc.build(elements)
  buffer.seek(0)
  return buffer.getvalue()


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

  st.session_state.fatture = carica_fatture_da_supabase()
  st.session_state.pagamenti = carica_pagamenti_da_supabase()
  st.session_state.mq_appartamenti = carica_mq_da_supabase()

  df_fatture = st.session_state.fatture
  tot_mq_reali = sum(st.session_state.mq_appartamenti.values())

  mese_map = {
      "Gennaio": 1, "Febbraio": 2, "Marzo": 3, "Aprile": 4, 
      "Maggio": 5, "Giugno": 6, "Luglio": 7, "Agosto": 8, 
      "Settembre": 9, "Ottobre": 10, "Novembre": 11, "Dicembre": 12
  }

  # --- 1. DASHBOARD & RIEPILOGO ---
  if menu == "Dashboard & Riepilogo":
    st.title("📊 Dashboard e Riparto Spese (su MQ)")

    if df_fatture.empty:
      st.info("La tabella 'fatture' su Supabase è attualmente vuota. Inserisci una fattura dalla sezione 'Inserisci Fattura' per popolare i calcoli.")
      tot_imp, tot_iva, tot_complessivo = 0.0, 0.0, 0.0
      descrizione_contesto = "Nessuna fattura"
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
          
          row_selezionata = df_calcolo.iloc[0]
          mese_selezionato = row_selezionata["mese"]
          anno_selezionato = row_selezionata["anno"]
          tipo_selezionato = row_selezionata["tipo"]
          descrizione_contesto = f"{tipo_selezionato} {mese_selezionato} {anno_selezionato}"
          
          file_selezionato = row_selezionata.get("file", None)

        tot_imp = df_calcolo["imponibile"].sum()
        tot_iva = df_calcolo["iva"].sum()
        tot_complessivo = df_calcolo["totale"].sum()

      if not df_filtered.empty and 'selected_option' in locals() and selected_option != "-- Tutte le fatture filtrate --":
        st.markdown("### 📎 File Fattura Collegato")
        if file_selezionato and str(file_selezionato).strip() != "" and str(file_selezionato).lower() != "nan":
          st.success(f"File allegato registrato: **{file_selezionato}**")
          try:
            res = supabase.storage.from_(BUCKET_NAME).download(str(file_selezionato).strip())
            if res:
              st.download_button(
                  label="📥 Scarica PDF Fattura",
                  data=res,
                  file_name=str(file_selezionato).strip(),
                  mime="application/pdf",
                  key="dl_supabase_storage",
                  use_container_width=True
              )
          except Exception as e:
            st.warning(f"Impossibile scaricare il file dal bucket '{BUCKET_NAME}': {e}")
        else:
          st.info("Nessun file PDF associato a questa fattura.")

    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    col1.metric("Totale Imponibile", f"€ {tot_imp:,.2f}")
    col2.metric("Totale IVA", f"€ {tot_iva:,.2f}")
    col3.metric("Totale Generale", f"€ {tot_complessivo:,.2f}")

    st.markdown("---")
    st.subheader("Tabella di Riparto per Condomino (Basata su Metri Quadri Reali)")

    reparto_data = []
    sum_mq = 0.0
    sum_imp = 0.0
    sum_iva = 0.0
    sum_tot = 0.0

    for app, mq in st.session_state.mq_appartamenti.items():
      # Calcolo del rapporto basato sui mq reali bloccato a 11 cifre decimali[cite: 1]
      rapporto_reale = round(mq / tot_mq_reali, 11) if tot_mq_reali > 0 else 0

      # Applicazione del rapporto e arrotondamento finale al centesimo[cite: 1]
      quota_imp = round(tot_imp * rapporto_reale, 2)
      quota_iva = round(tot_iva * rapporto_reale, 2)
      quota_tot = round(tot_complessivo * rapporto_reale, 2)

      sum_mq += mq
      sum_imp += quota_imp
      sum_iva += quota_iva
      sum_tot += quota_tot

      reparto_data.append(
          {
              "Condomino": app,
              "Metri Quadri (MQ)": mq,
              "Rapporto (%)": f"{rapporto_reale * 100:.4f}%",
              "Quota Imponibile (€)": quota_imp,
              "Quota IVA (€)": quota_iva,
              "Quota Totale (€)": quota_tot,
          }
      )

    reparto_data.append(
        {
            "Condomino": "TOTALE",
            "Metri Quadri (MQ)": round(sum_mq, 2),
            "Rapporto (%)": "100.00%",
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
          file_name="riparto_spese_condominio_mq.pdf",
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

    st.markdown("#### Filtra Fatture per il Pagamento")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
      anni_disponibili_pag = sorted(df_fatture["anno"].unique(), reverse=True) if not df_fatture.empty and "anno" in df_fatture.columns else []
      filtro_tipo_pag = st.selectbox(
          "Filtra per Tipo di Spesa",
          ["Tutte le tipologie", "Energia Elettrica", "Gasolio"],
          key="reg_filtro_tipo"
      )
    with col_p2:
      filtro_anno_pag = st.selectbox(
          "Filtra per Anno Fiscale",
          ["Tutti gli anni"] + list(anni_disponibili_pag),
          key="reg_filtro_anno"
      )
      
    df_fatture_form = df_fatture.copy()
    if not df_fatture_form.empty:
      if filtro_tipo_pag != "Tutte le tipologie" and "tipo" in df_fatture_form.columns:
          df_fatture_form = df_fatture_form[df_fatture_form["tipo"] == filtro_tipo_pag]
      if filtro_anno_pag != "Tutti gli anni" and "anno" in df_fatture_form.columns:
          df_fatture_form = df_fatture_form[df_fatture_form["anno"] == int(filtro_anno_pag)]

    opzioni_fatture_pagamento = ["-- Seleziona una fattura --"]
    if not df_fatture_form.empty:
      for _, row in df_fatture_form.iterrows():
        opzioni_fatture_pagamento.append(
            f"ID: {row['id']} | {row['anno']} - {row['mese']} |"
            f" {row['tipo']} | {row['fornitore']} | Totale: €"
            f" {row['totale']:,.2f}"
        )

    fattura_scelta_str = st.selectbox(
        "Seleziona Fattura di Riferimento", opzioni_fatture_pagamento, key="reg_fattura"
    )

    quota_dovuta_automatica = 0.0
    if fattura_scelta_str != "-- Seleziona una fattura --" and not df_fatture_form.empty:
      try:
        id_fat_temp = int(fattura_scelta_str.split("|")[0].replace("ID:", "").strip())
        row_f_temp = df_fatture_form[df_fatture_form["id"] == id_fat_temp].iloc[0]
        tot_fat_temp = float(row_f_temp["totale"])
        mq_c = st.session_state.mq_appartamenti.get(cond_attivo, 0.0)
        
        # APPLICATO LO STESSO METODO: 11 cifre sui mq reali e arrotondamento al centesimo[cite: 1]
        rapporto_temp = round(mq_c / tot_mq_reali, 11) if tot_mq_reali > 0 else 0.0
        quota_dovuta_automatica = round(tot_fat_temp * rapporto_temp, 2)
      except Exception:
        pass

    current_selection_key = f"{cond_attivo}_{fattura_scelta_str}"
    if "last_selection_key" not in st.session_state:
      st.session_state.last_selection_key = current_selection_key

    if st.session_state.last_selection_key != current_selection_key:
      st.session_state.reg_importo_dovuto = round(quota_dovuta_automatica, 2)
      st.session_state.reg_importo = 0.0
      st.session_state.reg_data = ""
      st.session_state.last_selection_key = current_selection_key
    else:
      st.session_state.reg_importo_dovuto = round(quota_dovuta_automatica, 2)

    with st.form("form_registra_pagamento"):
      st.write(f"Stai registrando un pagamento per: **{cond_attivo}** (Fattura selezionata: *{fattura_scelta_str}*)")
      
      col_form1, col_form2 = st.columns(2)
      with col_form1:
        importo_da_pagare_input = st.number_input(
            "Importo da Pagare (Quota Condomino) (€)", min_value=0.0, format="%.2f", key="reg_importo_dovuto"
        )
      with col_form2:
        importo_versato = st.number_input(
            "Importo Pagato (€)", min_value=0.0, format="%.2f", key="reg_importo"
        )
      
      data_versamento = st.text_input(
          "Data o Mese di Registrazione Pagamento", key="reg_data"
      )

      submit_pagamento = st.form_submit_button("Registra Pagamento su Supabase")

      if submit_pagamento:
        if fattura_scelta_str != "-- Seleziona una fattura --":
          id_fattura_collegata = int(fattura_scelta_str.split("|")[0].replace("ID:", "").strip())
        else:
          id_fattura_collegata = None

        st.session_state.pagamenti = carica_pagamenti_da_supabase()
        df_pag_corrente = st.session_state.pagamenti
        
        accredito_precedente = 0.0
        if not df_pag_corrente.empty:
          df_cond_prec = df_pag_corrente[df_pag_corrente["condominio"] == cond_attivo]
          if not df_cond_prec.empty:
            ultimo_record = df_cond_prec.iloc[-1]
            accredito_precedente = float(ultimo_record.get("riporto", 0.0))

        importo_versato_f = float(importo_versato)
        quota_dovuta_f = float(importo_da_pagare_input)
        
        riporto_generato = round(importo_versato_f - quota_dovuta_f + accredito_precedente, 2)

        nuovo_pagamento = {
            "condominio": cond_attivo,
            "fattura_id": id_fattura_collegata,
            "data_pagamento": data_versamento if data_versamento else "Data non specificata",
            "importo_da_pagare": round(quota_dovuta_f, 2),
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
          df_fatture_all['rif_fattura'] = df_fatture_all['anno'].astype(str) + " - " + df_fatture_all['mese'] + " (" + df_fatture_all['tipo'] + ")"
          lookup_fat = df_fatture_all.set_index('id')['rif_fattura']
          df_pag['Riferimento'] = df_pag['fattura_id'].map(lookup_fat).fillna("N/A")
      else:
          df_pag['Riferimento'] = "N/A"

      mostra_tutti = st.checkbox("Mostra storico completo di tutti i condomini", value=False)
      df_visual = df_pag.copy()
      
      if not mostra_tutti:
          df_visual = df_visual[df_visual["condominio"] == cond_attivo]
          st.write(f"Visualizzazione filtrata per: **{cond_attivo}** (Modifica la cella 'accredito' e clicca salva sotto)")
      else:
          df_visual = df_visual.copy()
          st.write("Visualizzazione: **Storico Completo** (Modifica la cella 'accredito' e clicca salva sotto)")
      
      col_ordine = ["id", "condominio", "Riferimento", "data_pagamento", "importo_da_pagare", "importo_pagato", "accredito", "riporto"]
      col_presenti = [c for c in col_ordine if c in df_visual.columns]
      
      df_editato = st.data_editor(
          df_visual[col_presenti],
          key="editor_pagamenti_tabella",
          num_rows="fixed",
          disabled=[c for c in col_presenti if c != "accredito"]
      )

      col_save, col_pdf = st.columns([1,1])
      with col_save:
        salva_clicked = st.button("💾 Salva Modifiche Accredito", key="btn_salva_accredito")
      with col_pdf:
        if not df_visual.empty:
          opzioni_ricevuta = [f"ID: {r['id']} | {r['condominio']} | {r['Riferimento']} | € {float(r['importo_pagato']):.2f} del {r['data_pagamento']}" for _, r in df_visual.iterrows()]
          sel_ricevuta = st.selectbox("Seleziona pagamento per ricevuta PDF", opzioni_ricevuta, key="sel_ricevuta_pdf")
          id_ricevuta = int(sel_ricevuta.split("|")[0].replace("ID:", "").strip())
          row_ricevuta = df_visual[df_visual["id"]==id_ricevuta].iloc[0] if not df_visual[df_visual["id"]==id_ricevuta].empty else df_visual.iloc[0]
          pdf_ricevuta = genera_ricevuta_pagamento(row_ricevuta, df_fatture_all)
          st.download_button("🖨️ Stampa Ricevuta PDF", data=pdf_ricevuta, file_name=f"ricevuta_{row_ricevuta['condominio']}_{row_ricevuta['id']}.pdf", mime="application/pdf", key="btn_pdf_ricevuta")
        else:
          st.info("Nessun pagamento per generare ricevuta")

      if salva_clicked:
        try:
          df_db = carica_pagamenti_da_supabase()
          
          if df_db.empty:
            st.warning("Nessun dato presente nel database.")
          else:
            valori_editati = {}
            for _, row_edited in df_editato.iterrows():
              id_riga = int(row_edited["id"])
              val_acc = row_edited["accredito"]
              valori_editati[id_riga] = float(val_acc) if val_acc is not None and str(val_acc).strip() != "" else 0.0

            sub_indices = df_db[df_db["condominio"] == cond_attivo].sort_values(by="id", ascending=True).index
            
            forzatura_attiva = False
            riporto_precedente = 0.0

            for i, idx in enumerate(sub_indices):
              id_riga = int(df_db.loc[idx, "id"])
              
              valore_db_precedente = float(df_db.loc[idx, "accredito"])
              valore_utente = valori_editati.get(id_riga, valore_db_precedente)

              if valore_utente != valore_db_precedente:
                accredito_corrente = valore_utente
                forzatura_attiva = True
              elif i == 0:
                accredito_corrente = valore_utente
                forzatura_attiva = False
              else:
                if forzatura_attiva or i > 0:
                  accredito_corrente = riporto_precedente
                else:
                  accredito_corrente = valore_utente

              df_db.loc[idx, "accredito"] = round(accredito_corrente, 2)

              importo_pagato = float(df_db.loc[idx, "importo_pagato"])
              importo_da_pagare = float(df_db.loc[idx, "importo_da_pagare"])
              
              riporto_corrente = round(importo_pagato + accredito_corrente - importo_da_pagare, 2)
              df_db.loc[idx, "riporto"] = riporto_corrente
              
              riporto_precedente = riporto_corrente

            sub_df_updated = df_db[df_db["condominio"] == cond_attivo]
            for _, row in sub_df_updated.iterrows():
              id_riga = int(row["id"])
              payload_update = {
                  "accredito": float(row["accredito"]),
                  "riporto": float(row["riporto"])
              }
              try:
                supabase.table("pagamenti").update(payload_update).eq("id", id_riga).execute()
              except Exception:
                supabase.table("pagamneti").update(payload_update).eq("id", id_riga).execute()

            st.session_state.pagamenti = carica_pagamenti_da_supabase()
            st.success(f"Modifiche salvate e catena perpetua aggiornata per {cond_attivo}!")
            st.rerun()

        except Exception as e:
          st.error(f"Errore durante il salvataggio: {e}")
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

  # --- 2. INSERISCI E GESTISCI FATTURE ---
  elif menu == "Inserisci Fattura":
    st.title("📝 Inserimento e Gestione Fatture")

    st.subheader("Nuova Fattura")
    with st.form("form_fattura_nuova", clear_on_submit=True):
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
      st.markdown("### 📄 Carica File PDF Fattura")
      uploaded_file = st.file_uploader("Carica File PDF Fattura", type=["pdf"], label_visibility="collapsed")

      submit_fat = st.form_submit_button("Salva Fattura su Supabase")
      
      if submit_fat:
        nome_file = ""
        if uploaded_file is not None:
          nome_file = uploaded_file.name
          try:
            file_bytes = uploaded_file.getvalue()
            supabase.storage.from_(BUCKET_NAME).upload(nome_file, file_bytes, file_options={"upsert": "true"})
          except Exception as e:
            st.error(f"Errore caricamento file su Supabase Storage: {e}")

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

    st.markdown("---")
    st.subheader("🗑️ Elimina Fattura Esistente")
    
    if df_fatture.empty:
      st.info("Nessuna fattura presente nel database da poter eliminare.")
    else:
      opzioni_elimina_fattura = []
      for _, row in df_fatture.iterrows():
        opzioni_elimina_fattura.append(
            f"ID: {row['id']} | {row['anno']} - {row['mese']} | {row['tipo']} | Fornitore: {row['fornitore']} | Tot: € {row['totale']:,.2f}"
        )

      fattura_da_eliminare_str = st.selectbox("Seleziona la fattura da eliminare", opzioni_elimina_fattura, key="select_elimina_fat")

      if st.button("Conferma ed Elimina Fattura"):
        id_fat_el = int(fattura_da_eliminare_str.split("|")[0].replace("ID:", "").strip())
        
        row_del = df_fatture[df_fatture["id"] == id_fat_el]
        if not row_del.empty:
          nome_file_as = row_del.iloc[0].get("file", None)
          if nome_file_as and str(nome_file_as).strip() != "" and str(nome_file_as).lower() != "nan":
            try:
              supabase.storage.from_(BUCKET_NAME).remove([str(nome_file_as).strip()])
            except Exception:
              pass

        supabase.table("fatture").delete().eq("id", id_fat_el).execute()
        st.session_state.fatture = carica_fatture_da_supabase()
        st.success(f"Fattura ID {id_fat_el} eliminata con successo!")
        st.rerun()

  # --- 3. STORICO E DETTAGLIO ---
  elif menu == "Storico e Dettaglio":
    st.title("📂 Storico Fatture e Scadenze")
    
    if df_fatture.empty:
      st.info("Nessuna fattura presente nello storico.")
    else:
      col_storico1, col_storico2 = st.columns(2)
      with col_storico1:
        anni_disp_storico = sorted(df_fatture["anno"].unique(), reverse=True) if "anno" in df_fatture.columns else []
        filtro_anno_storico = st.selectbox(
            "Filtra per Anno Fiscale",
            ["Tutti gli anni"] + list(anni_disp_storico),
            key="storico_filtro_anno"
        )
      with col_storico2:
        filtro_tipo_storico = st.selectbox(
            "Filtra per Tipologia Spesa",
            ["Tutte le tipologie", "Energia Elettrica", "Gasolio"],
            key="storico_filtro_tipo"
        )

      df_storico_filtered = df_fatture.copy()
      if filtro_anno_storico != "Tutti gli anni" and "anno" in df_storico_filtered.columns:
        df_storico_filtered = df_storico_filtered[df_storico_filtered["anno"] == int(filtro_anno_storico)]
      if filtro_tipo_storico != "Tutte le tipologie" and "tipo" in df_storico_filtered.columns:
        df_storico_filtered = df_storico_filtered[df_storico_filtered["tipo"] == filtro_tipo_storico]

      st.markdown("---")
      if df_storico_filtered.empty:
        st.warning("Nessuna fattura trovata con i filtri selezionati.")
      else:
        st.dataframe(df_storico_filtered, use_container_width=True)

      # --- MONITORAGGIO SCADENZE E QUOTE NON PAGATE ---
      st.markdown("---")
      st.subheader("🚨 Monitoraggio Scadenze e Quote Non Pagate (su MQ)")

      df_pagamenti_check = carica_pagamenti_da_supabase()
      
      pagate_set = set()
      if not df_pagamenti_check.empty and "fattura_id" in df_pagamenti_check.columns:
        for _, prow in df_pagamenti_check.iterrows():
          if pd.notna(prow["fattura_id"]) and pd.notna(prow["condominio"]):
            pagate_set.add((str(prow["condominio"]), int(prow["fattura_id"])))

      report_scaduti = []
      
      for _, f_row in df_fatture.iterrows():
        f_id = int(f_row["id"])
        f_anno = f_row["anno"]
        f_mese = f_row["mese"]
        f_tipo = f_row["tipo"]
        f_fornitore = f_row["fornitore"]
        f_totale = float(f_row["totale"])
        
        for app, mq in st.session_state.mq_appartamenti.items():
          # APPLICATO LO STESSO METODO: 11 cifre sui mq reali e arrotondamento al centesimo[cite: 1]
          rapporto_temp = round(mq / tot_mq_reali, 11) if tot_mq_reali > 0 else 0.0
          quota_dovuta = round(f_totale * rapporto_temp, 2)
          is_pagato = (app, f_id) in pagate_set
          
          if not is_pagato:
            report_scaduti.append({
                "Condomino": app,
                "Fattura ID": f_id,
                "Periodo": f"{f_anno} - {f_mese}",
                "Tipo Spesa": f_tipo,
                "Fornitore": f_fornitore,
                "Quota Dovuta (€)": round(quota_dovuta, 2),
                "Stato": "Scaduto / Non Pagato"
            })

      df_scaduti = pd.DataFrame(report_scaduti)

      if df_scaduti.empty:
        st.success("Ottimo! Non ci sono quote scoperte: tutte le fatture risultano pagate dai condomini.")
      else:
        col_sc1, col_sc2 = st.columns(2)
        with col_sc1:
          conds_selezionabili = ["Tutti i condomini"] + APP_NAMES
          filtro_scad_cond = st.selectbox("Filtra per Condomino Inadempiente", conds_selezionabili, key="scad_cond")
        with col_sc2:
          tipi_scad = ["Tutte le tipologie", "Energia Elettrica", "Gasolio"]
          filtro_scad_tipo = st.selectbox("Filtra per Tipo Spesa Scaduta", tipi_scad, key="scad_tipo")

        df_scad_filtered = df_scaduti.copy()
        if filtro_scad_cond != "Tutti i condomini":
          df_scad_filtered = df_scad_filtered[df_scad_filtered["Condomino"] == filtro_scad_cond]
        if filtro_scad_tipo != "Tutte le tipologie":
          df_scad_filtered = df_scad_filtered[df_scad_filtered["Tipo Spesa"] == filtro_scad_tipo]

        tot_insoluto = df_scad_filtered["Quota Dovuta (€)"].sum()
        st.metric("Totale Residuo da Incassare", f"€ {tot_insoluto:,.2f}")

        st.dataframe(df_scad_filtered, use_container_width=True)

        def genera_pdf_scaduti(df_res, filtro_c, filtro_t, totale_res):
          buf = io.BytesIO()
          doc = SimpleDocTemplate(buf, pagesize=letter)
          elems = []
          styles = getSampleStyleSheet()
          
          t_style = ParagraphStyle('TStyle', parent=styles['Heading1'], fontSize=14, alignment=1, spaceAfter=8)
          sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=9, alignment=1, spaceAfter=12)
          
          elems.append(Paragraph("<b>REPORT QUOTE NON PAGATE / SCADENZE</b>", t_style))
          elems.append(Paragraph(f"Filtro Condomino: {filtro_c} | Filtro Tipo: {filtro_t}", sub_style))
          elems.append(Spacer(1, 8))
          
          table_data = [list(df_res.columns)] + df_res.values.tolist()
          t = Table(table_data, colWidths=[80, 60, 90, 90, 80, 80])
          t.setStyle(TableStyle([
              ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#c0392b')),
              ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
              ('ALIGN', (0,0), (-1,-1), 'CENTER'),
              ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
              ('FONTSIZE', (0,0), (-1,0), 8),
              ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8f9fa')),
              ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
              ('FONTSIZE', (0,1), (-1,-1), 8),
              ('TOPPADDING', (0,1), (-1,-1), 4),
              ('BOTTOMPADDING', (0,1), (-1,-1), 4),
          ]))
          elems.append(t)
          elems.append(Spacer(1, 15))
          
          tot_style = ParagraphStyle('TotStyle', parent=styles['Normal'], fontSize=11, fontName='Helvetica-Bold', alignment=2)
          elems.append(Paragraph(f"Totale Residuo da Incassare: € {totale_res:,.2f}", tot_style))
          
          doc.build(elems)
          buf.seek(0)
          return buf.getvalue()

        col_p_btn1, _ = st.columns([1, 2])
        with col_p_btn1:
          pdf_scadenze_bytes = genera_pdf_scaduti(df_scad_filtered, filtro_scad_cond, filtro_scad_tipo, tot_insoluto)
          st.download_button(
              label="📥 Stampa / Scarica PDF Scadenze",
              data=pdf_scadenze_bytes,
              file_name="report_quote_scadute.pdf",
              mime="application/pdf",
              use_container_width=True,
              key="btn_print_scadenze"
          )

  # --- 4. GESTIONE METRATURE ---
  elif menu == "Gestione Millesimi & Riporti":
    st.title("⚙️ Gestione Metrature Appartamenti")

    st.subheader("Modifica Metrature Appartamenti")
    with st.form("form_mq"):
      nuovi_mq = {}
      for app in APP_NAMES:
        val_attuale = st.session_state.mq_appartamenti.get(app, 70.0)
        nuovi_mq[app] = st.number_input(
            f"MQ {app}",
            min_value=1.0,
            value=float(val_attuale),
            step=0.01,
            format="%.2f",
            key=f"mq_{app}"
        )
      
      if st.form_submit_button("Salva Metrature"):
        if salva_mq_su_supabase(nuovi_mq):
          st.session_state.mq_appartamenti = novos = nuovi_mq
          st.success("Metrature aggiornate con successo!")
          st.rerun()

    st.markdown("---")
    st.subheader("Rapporto Metrature ed Edificio")
    tot_mq_aggiornato = sum(st.session_state.mq_appartamenti.values())
    df_mill = pd.DataFrame([
        {
            "Appartamento": k, 
            "MQ": v, 
            "Incidenza (%)": f"{(v / tot_mq_aggiornato)*100:.4f}%" if tot_mq_aggiornato > 0 else "0%"
        } 
        for k, v in st.session_state.mq_appartamenti.items()
    ])
    st.dataframe(df_mill, use_container_width=True)
