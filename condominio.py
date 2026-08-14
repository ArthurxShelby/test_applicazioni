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
      st.info("La tabella 'fatture' su Supabase è attualmente vuota. Inserisci una fattura dalla sezione 'Inserisci Fattura' per popolare i calcoli.")
      df_filtered = pd.DataFrame(columns=["id", "anno", "mese", "tipo", "fornitore", "imponibile", "iva", "totale", "file"])
      selected_option = "-- Tutte le fatture filtrate --"
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
            ["Tutti"] + list(anni_disponibili) if anni_disponibili else ["Tutti"]
        )
      with col_f2:
        tipi_disponibili = sorted(df_fatture["tipo"].dropna().unique()) if "tipo" in df_fatture.columns else []
        selected_tipo = st.selectbox(
            "Filtra per Tipo Spesa",
            ["Tutti"] + tipi_disponibili if tipi_disponibili else ["Tutti"]
        )

      df_filtered = df_fatture.copy()
      if selected_anno!= "Tutti":
        df_filtered = df_filtered[df_filtered["anno"] == selected_anno]
      if selected_tipo!= "Tutti":
        df_filtered = df_filtered[df_filtered["tipo"] == selected_tipo]

      if df_filtered.empty:
        st.warning(f"Nessuna fattura trovata per i filtri selezionati (Anno: {selected_anno}, Tipo: {selected_tipo}).")
        selected_option = "-- Nessuna fattura disponibile per questa selezione --"
        tot_imp, tot_iva, tot_complessivo = 0.0, 0.0, 0.0
        descrizione_contesto = f"Filtri: Anno {selected_anno}, Tipo {selected_tipo} - Vuoto"
      else:
        df_filtered['mese_num'] = df_filtered['mese'].map(mese_map)
        df_filtered = df_filtered.sort_values(by=['anno', 'mese_num'], ascending=[False, False])

        opzioni_fatture = ["-- Tutte le fatture filtrate --"] + [
            f"ID: {row['id']} | {row['anno']} - {row['mese']} | {row['tipo']} | Tot: € {row['totale']:,.2f}" for _, row in df_filtered.iterrows()
        ]
        selected_option = st.selectbox("Seleziona una fattura specifica o tutte quelle filtrate", opzioni_fatture)

        if selected_option == "-- Tutte le fatture filtrate --":
          tot_imp = df_filtered["imponibile"].sum()
          tot_iva = df_filtered["iva"].sum()
          tot_complessivo = df_filtered["totale"].sum()
          descrizione_contesto = f"Riepilogo: Anno {selected_anno}, Tipo {selected_tipo} ({len(df_filtered)} fatture)"
        else:
          id_selezionato = int(selected_option.split("|")[0].replace("ID:", "").strip())
          fattura_singola = df_filtered[df_filtered["id"] == id_selezionato].iloc[0]
          tot_imp = fattura_singola["imponibile"]
          tot_iva = fattura_singola["iva"]
          tot_complessivo = fattura_singola["totale"]
          descrizione_contesto = f"Dettaglio Fattura ID {id_selezionato}: {fattura_singola['anno']} {fattura_singola['mese']} - {fattura_singola['tipo']}"

    st.markdown("---")
    st.subheader(f"📊 Totali per: {descrizione_contesto}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Totale Imponibile", f"€ {tot_imp:,.2f}")
    c2.metric("Totale IVA", f"€ {tot_iva:,.2f}")
    c3.metric("TOTALE COMPLESSIVO", f"€ {tot_complessivo:,.2f}")

    st.markdown("---")
    st.subheader("🏠 Riparto Spese per Appartamento")

    if tot_complessivo == 0:
      st.info("Nessun costo da ripartire per la selezione corrente.")
      df_reparto_display = pd.DataFrame(columns=["Appartamento", "MQ", "Millesimi", "Importo Dovuto (€)"])
    else:
      dati_reparto = []
      for app in APP_NAMES:
        mq = st.session_state.mq_appartamenti.get(app, 0)
        mill = millesimi.get(app, 0)
        importo = round((mill / 1000) * tot_complessivo, 2) if tot_millesimi > 0 else 0
        dati_reparto.append({"Appartamento": app, "MQ": mq, "Millesimi": mill, "Importo Dovuto (€)": importo})
      df_reparto_display = pd.DataFrame(dati_reparto)

    st.dataframe(df_reparto_display, use_container_width=True)

    if not df_reparto_display.empty and tot_complessivo > 0:
      pdf_bytes = genera_pdf_riparto(df_reparto_display, descrizione_contesto)
      st.download_button(
          label="📄 Scarica PDF Riparto",
          data=pdf_bytes,
          file_name=f"riparto_{descrizione_contesto.replace(' ', '_')}.pdf",
          mime="application/pdf"
      )

  # --- 2. INSERISCI E GESTISCI FATTURE ---
  elif menu == "Inserisci Fattura":
    st.title("📝 Inserimento e Gestione Fatture")

    st.subheader("Nuova Fattura")

    if "form_submitted" not in st.session_state:
      st.session_state.form_submitted = False

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
          if nome_file_as and str(nome_file_as).strip()!= "" and str(nome_file_as).lower()!= "nan":
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
    st.title("📂 Storico Fatture")
    if df_fatture.empty:
      st.info("Nessuna fattura presente nello storico.")
    else:
      st.dataframe(df_fatture, use_container_width=True)

  # --- 4. GESTIONE MILLESIMI (SENZA RIPORTI) ---
  elif menu == "Gestione Millesimi & Riporti":
    st.title("⚙️ Gestione Metrature e Millesimi")

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

    st.markdown("---")
    st.subheader("Millesimi Calcolati")
    millesimi = calcola_millesimi_da_mq(st.session_state.mq_appartamenti)
    df_mill = pd.DataFrame([{"Appartamento": k, "MQ": st.session_state.mq_appartamenti[k], "Millesimi": v} for k, v in millesimi.items()])
    st.dataframe(df_mill, use_container_width=True)

    # NOTA: tab Riporti Iniziali rimosso
