import streamlit as st
import pandas as pd
from supabase import create_client, Client
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Gestione Condominio", page_icon="🏢", layout="wide")

# --- CONNESSIONE A SUPABASE ---
SUPABASE_URL = st.secrets["supabase"]["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["supabase"]["SUPABASE_KEY"]

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

# --- DATI FISSI CONDOMINIO ---
millesimi = {
    "Interno 1 (Rossi)": 100.0,
    "Interno 2 (Bianchi)": 150.0,
    "Interno 3 (Verdi)": 200.0,
    "Interno 4 (Neri)": 120.0,
    "Interno 5 (Gialli)": 180.0,
    "Interno 6 (Blu)": 130.0,
    "Interno 7 (Viola)": 120.0,
}
tot_millesimi = sum(millesimi.values())
APP_NAMES = list(millesimi.keys())

mese_map = {
    "Gennaio": 1, "Febbraio": 2, "Marzo": 3, "Aprile": 4,
    "Maggio": 5, "Giugno": 6, "Luglio": 7, "Agosto": 8,
    "Settembre": 9, "Ottobre": 10, "Novembre": 11, "Dicembre": 12
}

# --- FUNZIONI CARICAMENTO DATI ---
def carica_fatture_da_supabase():
    try:
        response = supabase.table("fatture").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception:
        try:
            response = supabase.table("fature").select("*").execute()
            return pd.DataFrame(response.data)
        except Exception as e:
            st.error(f"Errore caricamento fatture: {e}")
            return pd.DataFrame()

def carica_pagamenti_da_supabase():
    try:
        response = supabase.table("pagamenti").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception:
        try:
            response = supabase.table("pagamneti").select("*").execute()
            return pd.DataFrame(response.data)
        except Exception as e:
            return pd.DataFrame()

# --- FUNZIONE GENERAZIONE PDF ---
def genera_pdf_riparto(df_reparto, contesto):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=15,
        alignment=1,
        textColor=colors.HexColor('#1f77b4')
    )
    
    elements.append(Paragraph("<b>RIEPILOGO RIPARTO SPESE CONDOMINIALI</b>", title_style))
    elements.append(Paragraph(f"<b>Riferimento:</b> {contesto}", styles['Normal']))
    elements.append(Spacer(1, 15))
    
    data = [df_reparto.columns.tolist()] + df_reparto.values.tolist()
    
    table = Table(data, colWidths=[150, 60, 95, 95, 95])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0e0e0')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# --- MENU LATERALE ---
st.sidebar.title("🏢 Gestione Condominio")
menu = st.sidebar.selectbox("Navigazione", ["Dashboard & Riepilogo", "Inserisci Fattura"])

df_fatture = carica_fatture_da_supabase()

# --- 1. DASHBOARD & RIEPILOGO ---
if menu == "Dashboard & Riepilogo":
    st.title("📊 Dashboard e Riparto Spese")

    if df_fatture.empty:
      st.info("Nessuna fattura presente. Inizia ad inserirle dalla sezione 'Inserisci Fattura'.")
    else:
      df_sorted = df_fatture.copy()
      df_sorted['mese_num'] = df_sorted['mese'].map(mese_map)
      df_sorted = df_sorted.sort_values(by=['anno', 'mese_num'], ascending=[False, False])

      col_f1, col_f2 = st.columns(2)
      with col_f1:
        anni_disponibili = sorted(df_fatture["anno"].unique(), reverse=True)
        selected_anno = st.selectbox("Filtra per Anno Fiscale", ["Tutti gli anni (da 2022)"] + list(anni_disponibili))
      with col_f2:
        selected_tipo = st.selectbox("Filtra per Tipologia Spesa", ["Tutte le tipologie", "Energia Elettrica", "Gasolio"])

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
          desc = f"ID: {row['id']} | {row['anno']} - {row['mese']} | {row['tipo']} | {row['fornitore']} | Tot: € {row['totale']:,.2f}"
          opzioni_fatture.append(desc)

        selected_option = st.selectbox("Scegli una singola fattura (esclude le altre)", opzioni_fatture)

        if selected_option == "-- Tutte le fatture filtrate --":
          df_calcolo = df_filtered
          descrizione_contesto = f"Anno: {selected_anno} | Tipo: {selected_tipo}"
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
      st.subheader("Tabella di Riparto per Condomino")

      reparto_data = []
      sum_millesimi = 0.0
      sum_imp = 0.0
      sum_iva = 0.0
      sum_tot = 0.0

      for app, mil in millesimi.items():
        quota_imp = tot_imp * (mil / tot_millesimi) if tot_millesimi > 0 else 0
        quota_iva = tot_iva * (mil / tot_millesimi) if tot_millesimi > 0 else 0
        quota_tot = (tot_complessivo * (mil / tot_millesimi) if tot_millesimi > 0 else 0)
        
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
              try:
                supabase.table("pagamenti").insert(nuovo_pagamento).execute()
              except Exception:
                supabase.table("pagamneti").insert(nuovo_pagamento).execute()
              st.session_state.pagamenti = carica_pagamenti_da_supabase()
              st.success(f"Pagamento registrato per {cond_attivo}!")
              st.rerun()
            except Exception as e:
              st.error(f"Errore: {e}")

      # --- TABELLA STORICO PAGAMENTI (ARRICCHITA) ---
      st.markdown("### 📂 Storico Pagamenti Ricevuti")
      st.session_state.pagamenti = carica_pagamenti_da_supabase()
      df_pag = st.session_state.pagamenti
      
      df_fatture_all = carica_fatture_da_supabase() 
      
      if not df_pag.empty:
        if not df_fatture_all.empty:
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

      # --- ELIMINAZIONE PAGAMENTO (SINCRONIZZATA) ---
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
            try:
              supabase.table("pagamenti").delete().eq("id", id_da_el).execute()
            except:
              supabase.table("pagamneti").delete().eq("id", id_da_el).execute()
            st.session_state.pagamenti = carica_pagamenti_da_supabase()
            st.success("Pagamento eliminato!")
            st.rerun()
          except Exception as e:
            st.error(f"Errore: {e}")
      else:
        st.info(f"Nessun pagamento trovato per {cond_attivo}.")

# --- 2. INSERISCI FATTURA ---
elif menu == "Inserisci Fattura":
    st.title("📝 Inserisci Nuova Fattura")

    with st.form("form_inserisci_fattura"):
      col_i1, col_i2 = st.columns(2)
      with col_i1:
        anno = st.selectbox("Anno Fiscale", [2026, 2025, 2024, 2023, 2022], index=0)
        mese = st.selectbox("Mese di Riferimento", list(mese_map.keys()))
        tipo = st.selectbox("Tipologia Spesa", ["Energia Elettrica", "Gasolio"])
      with col_i2:
        fornitore = st.text_input("Fornitore (es. Enel, fornitore gas)")
        imponibile = st.number_input("Imponibile (€)", min_value=0.0, format="%.2f")
        iva = st.number_input("IVA (€)", min_value=0.0, format="%.2f")

      totale_inserito = imponibile + iva
      st.write(f"**Totale Calcolato (Imponibile + IVA):** € {totale_inserito:,.2f}")

      submit_fattura = st.form_submit_button("Salva Fattura su Supabase")

      if submit_fattura:
        if not fornitore.strip():
          st.warning("Inserisci il nome del fornitore.")
        else:
          nuova_fattura = {
              "anno": int(anno),
              "mese": mese,
              "tipo": tipo,
              "fornitore": fornitore,
              "imponibile": float(imponibile),
              "iva": float(iva),
              "totale": float(totale_inserito),
          }
          try:
            try:
              supabase.table("fatture").insert(nuova_fattura).execute()
            except Exception:
              supabase.table("fature").insert(nuova_fattura).execute()
            st.success("Fattura inserita con successo!")
            st.rerun()
          except Exception as e:
            st.error(f"Errore durante il salvataggio: {e}")

    st.markdown("---")
    st.subheader("Elenco Fatture Registrate")
    df_fatture_corrente = carica_fatture_da_supabase()
    if not df_fatture_corrente.empty:
      st.dataframe(df_fatture_corrente, use_container_width=True)
    else:
      st.info("Nessuna fattura presente nel database.")
