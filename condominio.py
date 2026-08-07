import io
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
  SUPABASE_URL = st.secrets["SUPABASE_URL"]
  SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception as e:
  st.error(
      "Configurazione Supabase mancante nei Secrets di Streamlit! Controlla"
      " le impostazioni dell'app."
  )
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
  except Exception as e:
    st.error(f"Errore di connessione a Supabase (condominio): {e}")

  default_mq = {
      "ESPOSITO": 70.0,
      "MARANGI": 75.0,
      "LINCESSO": 80.0,
      "FUSO": 85.0,
      "PUCA": 90.0,
      "BAVILA": 85.0,
      "TESTA": 85.0,
  }
  return default_mq


def salva_mq_su_supabase(mq_dict):
  try:
    supabase.table("condominio").delete().neq("id", 0).execute()
    for cond, mq in mq_dict.items():
      supabase.table("condominio").insert(
          {"condominio": cond, "mq": mq}
      ).execute()
    return True
  except Exception as e:
    st.error(f"Errore nel salvataggio delle metrature su Supabase: {e}")
    return False


def carica_riporti_da_supabase():
  try:
    response = supabase.table("riporti").select("*").execute()
    data = response.data
    if data and len(data) > 0:
      return {row["condominio"]: float(row["riporto"]) for row in data}
  except Exception as e:
    pass
  return {app: 0.0 for app in APP_NAMES}


def salva_riporti_su_supabase(riporti_dict):
  try:
    supabase.table("riporti").delete().neq("id", 0).execute()
    for cond, rip in riporti_dict.items():
      supabase.table("riporti").insert(
          {"condominio": cond, "riporto": rip}
      ).execute()
    return True
  except Exception as e:
    st.error(f"Errore nel salvataggio dei riporti su Supabase: {e}")
    return False


def carica_fatture_da_supabase():
  try:
    response = supabase.table("fatture").select("*").execute()
    data = response.data
    if data:
      return pd.DataFrame(data)
  except Exception as e:
    st.error(f"Errore di connessione a Supabase (fatture): {e}")
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
      ]
  )


def carica_pagamenti_da_supabase():
  try:
    response = supabase.table("pagamenti").select("*").execute()
    data = response.data
    if data:
      return pd.DataFrame(data)
  except Exception as e:
    try:
      response = supabase.table("pagamneti").select("*").execute()
      data = response.data
      if data:
        return pd.DataFrame(data)
    except Exception as ex:
      pass
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

  table = Table(data, colWidths=[100, 70, 95, 95, 95, 95])
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

  df_fatture = st.session_state.fatture
  millesimi = calcola_millesimi_da_mq(st.session_state.mq_appartamenti)
  tot_millesimi = sum(millesimi.values())
  dict_riporti = st.session_state.riporti

  # Dizionario di mappatura mesi per ordinamento cronologico
  mese_map = {
      "Gennaio": 1, "Febbraio": 2, "Marzo": 3, "Aprile": 4, 
      "Maggio": 5, "Giugno": 6, "Luglio": 7, "Agosto": 8, 
      "Settembre": 9, "Ottobre": 10, "Novembre": 11, "Dicembre": 12
  }

  # --- 1. DASHBOARD & RIEPILOGO ---
  if menu == "Dashboard & Riepilogo":
    st.title("📊 Dashboard e Riparto Spese")

    if df_fatture.empty:
      st.info(
          "Nessuna fattura presente. Inizia ad inserirle dalla sezione"
          " 'Inserisci Fattura'."
      )
    else:
      df_sorted = df_fatture.copy()
      df_sorted['mese_num'] = df_sorted['mese'].map(mese_map)
      df_sorted = df_sorted.sort_values(by=['anno', 'mese_num'], ascending=[False, False])

      col_f1, col_f2 = st.columns(2)
      with col_f1:
        anni_disponibili = sorted(df_fatture["anno"].unique(), reverse=True)
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
          descrizione_contesto = (
              f"Anno: {selected_anno} | Tipo: {selected_tipo}"
          )
        else:
          id_estratto = int(selected_option.split("|")[0].replace("ID:", "").strip())
          df_calcolo = df_filtered[df_filtered["id"] == id_estratto]
          descrizione_contesto = f"Fattura Singola ID {id_estratto}"

        tot_imp = df_calcolo["imponibile"].sum()
        tot_iva = df_calcolo["iva"].sum()
        tot_complessivo = df_calcolo["totale"].sum()

      st.markdown("---")

      col1, col2, col3 = st.columns(3)
      col1.metric("Totale Imponibile", f"€ {tot_imp:,.2f}")
      col2.metric("Totale IVA", f"€ {tot_iva:,.2f}")
      col3.metric("Totale Generale", f"€ {tot_complessivo:,.2f}")

      st.markdown("---")
      st.subheader(
          "Tabella di Riparto per Condomino"
      )

      reparto_data = []
      sum_millesimi = 0.0
      sum_imp = 0.0
      sum_iva = 0.0
      sum_tot = 0.0
      sum_dovuto = 0.0

      for app, mil in millesimi.items():
        quota_imp = tot_imp * (mil / tot_millesimi) if tot_millesimi > 0 else 0
        quota_iva = tot_iva * (mil / tot_millesimi) if tot_millesimi > 0 else 0
        quota_tot = (
            tot_complessivo * (mil / tot_millesimi) if tot_millesimi > 0 else 0
        )
        
        val_riporto = dict_riporti.get(app, 0.0)
        totale_complessivo_dovuto = quota_tot + val_riporto

        sum_millesimi += mil
        sum_imp += quota_imp
        sum_iva += quota_iva
        sum_tot += quota_tot
        sum_dovuto += totale_complessivo_dovuto

        reparto_data.append(
            {
                "Condomino": app,
                "Millesimi": mil,
                "Quota Imponibile (€)": round(quota_imp, 2),
                "Quota IVA (€)": round(quota_iva, 2),
                "Quota Totale (€)": round(quota_tot, 2),
                "Totale Dovuto (€)": round(totale_complessivo_dovuto, 2),
            }
        )

      reparto_data.append(
          {
              "Condomino": "TOTALE",
              "Millesimi": round(sum_millesimi, 2),
              "Quota Imponibile (€)": round(sum_imp, 2),
              "Quota IVA (€)": round(sum_iva, 2),
              "Quota Totale (€)": round(sum_tot, 2),
              "Totale Dovuto (€)": round(sum_dovuto, 2),
          }
      )

      df_reparto = pd.DataFrame(reparto_data)
      st.dataframe(df_reparto, use_container_width=True)

      # --- BOTTONE STAMPA PDF ---
      col_pdf1, col_pdf2 = st.columns([1, 2])
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
      with st.form("form_registra_pagamento"):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
          condomino_selezionato = st.selectbox(
              "Seleziona Condomino", APP_NAMES, key="reg_condomino"
          )
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

        submit_pagamento = st.form_submit_button(
            "Registra Pagamento su Supabase"
        )

        if submit_pagamento:
          if not fattura_scelta_str:
            st.warning("Seleziona una fattura valida.")
          else:
            id_fattura_collegata = int(
                fattura_scelta_str.split("|")[0]
                .replace("ID:", "")
                .strip()
            )
            
            row_fattura = df_fatture[df_fatture["id"] == id_fattura_collegata].iloc[0]
            totale_singola_fattura = float(row_fattura["totale"])
            
            mil_condomino = millesimi.get(condomino_selezionato, 0.0)
            quota_dovuta_esatta = (totale_singola_fattura * (mil_condomino / tot_millesimi)) if tot_millesimi > 0 else 0.0
            
            st.session_state.pagamenti = carica_pagamenti_da_supabase()
            df_pag_corrente = st.session_state.pagamenti
            
            accredito_precedente = 0.0
            if not df_pag_corrente.empty:
              df_cond_prec = df_pag_corrente[df_pag_corrente["condominio"] == condomino_selezionato]
              if not df_cond_prec.empty:
                ultimo_record = df_cond_prec.iloc[-1]
                accredito_precedente = float(ultimo_record.get("riporto", 0.0))

            importo_versato_f = float(importo_versato)
            riporto_generato = round(importo_versato_f - quota_dovuta_esatta + accredito_precedente, 2)

            nuovo_pagamento = {
                "condominio": condomino_selezionato,
                "fattura_id": id_fattura_collegata,
                "data_pagamento": data_versamento,
                "importo_da_pagare": round(quota_dovuta_esatta, 2),
                "importo_pagato": importo_versato_f,
                "accredito": round(accredito_precedente, 2),
                "riporto": riporto_generato,
            }

            try:
              try:
                supabase.table("pagamenti").insert(nuovo_pagamento).execute()
              except Exception:
                supabase.table("pagamneti").insert(nuovo_pagamento).execute()

              st.session_state.pagamenti = carica_pagamenti_da_supabase()
              st.success(
                  f"Pagamento registrato per {condomino_selezionato} "
                  f"(Dovuto: € {quota_dovuta_esatta:,.2f} | Riporto: € {riporto_generato:,.2f})!"
              )
              st.rerun()
            except Exception as e:
              st.error(f"Errore durante il salvataggio del pagamento: {e}")

      # --- TABELLA STORICO PAGAMENTI (DINAMICA E FILTRATA) ---
      st.markdown("### Storico Pagamenti Ricevuti")
      st.session_state.pagamenti = carica_pagamenti_da_supabase()
      df_pag = st.session_state.pagamenti
      
      if not df_pag.empty:
        filtro_condomino = st.selectbox(
            "Filtra storico per Condomino", 
            ["Tutti"] + APP_NAMES, 
            index=0,
            key="filtro_storico_pagamenti"
        )
        
        df_visual = df_pag.copy()
        if filtro_condomino != "Tutti":
            df_visual = df_visual[df_visual["condominio"] == filtro_condomino]
        
        col_ordine = [
            "id", "condominio", "fattura_id", "data_pagamento",
            "importo_da_pagare", "importo_pagato", "accredito", "riporto",
        ]
        col_presenti = [c for c in col_ordine if c in df_visual.columns]
        st.dataframe(df_visual[col_presenti], use_container_width=True)
      else:
        st.info("Nessun pagamento registrato finora.")

      # --- ELIMINAZIONE ---
      st.markdown("### Elimina Pagamento Registrato")
      if not df_pag.empty:
        opzioni_pagamenti_elimina = []
        for _, row in df_pag.iterrows():
          p_imp = float(row.get("importo_pagato") or 0.0)
          opzioni_pagamenti_elimina.append(
              f"ID: {row['id']} | Condomino: {row['condominio']} | Importo: € {p_imp:,.2f} | Data: {row['data_pagamento']}"
          )

        pagamento_scelto_da_eliminare = st.selectbox(
            "Seleziona il pagamento da rimuovere",
            opzioni_pagamenti_elimina,
            key="select_elimina_pagamento"
        )

        if st.button("Elimina Pagamento Selezionato"):
          try:
            id_pagamento_da_eliminare = int(
                pagamento_scelto_da_eliminare.split("|")[0].replace("ID:", "").strip()
            )
            try:
              supabase.table("pagamenti").delete().eq("id", id_pagamento_da_eliminare).execute()
            except:
              supabase.table("pagamneti").delete().eq("id", id_pagamento_da_eliminare).execute()
            
            st.session_state.pagamenti = carica_pagamenti_da_supabase()
            st.success("Pagamento eliminato!")
            st.rerun()
          except Exception as e:
            st.error(f"Errore durante l'eliminazione: {e}")

  # --- 2. INSERISCI FATTURA ---
  elif menu == "Inserisci Fattura":
    st.title("📝 Inserimento Nuova Fattura")
    with st.form("form_fattura"):
      col1, col2 = st.columns(2)
      with col1:
        anno = st.selectbox("Anno", options=list(range(2022, 2028)), index=4)
        mese = st.selectbox("Mese", ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"])
        tipo = st.selectbox("Tipologia Spesa", ["Energia Elettrica", "Gasolio"])
      with col2:
        fornitore = st.text_input("Fornitore")
        imponibile = st.number_input("Imponibile (€)", min_value=0.0, format="%.2f")
        iva = st.number_input("IVA (€)", min_value=0.0, format="%.2f")

      submit_fat = st.form_submit_button("Salva Fattura su Supabase")
      if submit_fat:
        nuova_fattura = {"anno": int(anno), "mese": mese, "tipo": tipo, "fornitore": fornitore, "imponibile": float(imponibile), "iva": float(iva), "totale": float(imponibile + iva)}
        supabase.table("fatture").insert(nuova_fattura).execute()
        st.session_state.fatture = carica_fatture_da_supabase()
        st.success("Fattura salvata!")

  # --- 3. STORICO E DETTAGLIO ---
  elif menu == "Storico e Dettaglio":
    st.title("📂 Storico Fatture")
    st.dataframe(df_fatture, use_container_width=True)

  # --- 4. GESTIONE MILLESIMI & RIPORTI ---
  elif menu == "Gestione Millesimi & Riporti":
    st.title("⚙️ Gestione Metrature e Riporti")
