import pandas as pd
import streamlit as st

# Configurazione della pagina
st.set_page_config(
    page_title="Gestione Spese Condominiali", page_icon="🏢", layout="wide"
)

# --- CONFIGURAZIONE MILLESIMI E APPARTAMENTI (7 unità) ---
# Puoi modificare i nomi dei condomini o i millesimi iniziali (totale deve fare 1000)
DEFAULT_MILLESIMI = {
    "Appartamento 1": 120,
    "Appartamento 2": 130,
    "Appartamento 3": 140,
    "Appartamento 4": 150,
    "Appartamento 5": 160,
    "Appartamento 6": 150,
    "Appartamento 7": 150,
}

# --- SIMULAZIONE DATABASE IN SESSION STATE ---
if "logged_in" not in st.session_state:
  st.session_state.logged_in = False

if "millesimi" not in st.session_state:
  st.session_state.millesimi = DEFAULT_MILLESIMI.copy()

if "fatture" not in st.session_state:
  # Inizializziamo con vuoto (storico dal 2022)
  st.session_state.fatture = pd.DataFrame(
      columns=[
          "ID",
          "Anno",
          "Mese",
          "Tipo",
          "Fornitore",
          "Imponibile",
          "IVA",
          "Totale",
      ]
  )


# --- SISTEMA DI LOGIN ---
def login_screen():
  st.title("🏢 Accesso Gestione Condominio")
  with st.form("login_form"):
    username = st.text_input("Nome Utente")
    password = st.text_input("Password", type="password")
    submit = st.form_submit_button("Accedi")

    if submit:
      # Credenziali di esempio (modificabili a piacimento)
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
          "Gestione Millesimi",
      ],
  )

  if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

  df_fatture = st.session_state.fatture
  millesimi = st.session_state.millesimi
  tot_millesimi = sum(millesimi.values())

  # --- 1. DASHBOARD & RIEPILOGO ---
  if menu == "Dashboard & Riepilogo":
    st.title("📊 Dashboard e Riparto Spese")

    if df_fatture.empty:
      st.info(
          "Nessuna fattura presente. Inizia ad inserirle dalla sezione"
          " 'Inserisci Fattura'."
      )
    else:
      # Filtro per Anno
      anni_disponibili = sorted(df_fatture["Anno"].unique())
      selected_anno = st.selectbox(
          "Seleziona Anno Fiscale",
          ["Tutti gli anni (da 2022)"] + list(anni_disponibili),
      )

      if selected_anno != "Tutti gli anni (da 2022)":
        df_filtered = df_fatture[df_fatture["Anno"] == selected_anno]
      else:
        df_filtered = df_fatture

      # Metriche principali
      col1, col2, col3 = st.columns(3)
      tot_imp = df_filtered["Imponibile"].sum()
      tot_iva = df_filtered["IVA"].sum()
      tot_complessivo = df_filtered["Totale"].sum()

      col1.metric("Totale Imponibile", f"€ {tot_imp:,.2f}")
      col2.metric("Totale IVA", f"€ {tot_iva:,.2f}")
      col3.metric("Totale Generale", f"€ {tot_complessivo:,.2f}")

      st.markdown("---")
      st.subheader("Tabella di Riparto per Appartamento (Millesimi)")

      # Calcolo quote per ogni appartamento
      reparto_data = []
      for app, mil in millesimi.items():
        quota_imp = tot_imp * (mil / tot_millesimi)
        quota_iva = tot_iva * (mil / tot_millesimi)
        quota_tot = tot_complessivo * (mil / tot_millesimi)
        reparto_data.append(
            {
                "Appartamento": app,
                "Millesimi": mil,
                "Quota Imponibile (€)": round(quota_imp, 2),
                "Quota IVA (€)": round(quota_iva, 2),
                "Quota Totale (€)": round(quota_tot, 2),
            }
        )

      df_reparto = pd.DataFrame(reparto_data)
      st.dataframe(df_reparto, use_container_width=True)

  # --- 2. INSERISCI FATTURA ---
  elif menu == "Inserisci Fattura":
    st.title("📝 Inserimento Nuova Fattura")
    st.markdown("Inserisci i dati distinti tra Imponibile e IVA.")

    with st.form("form_fattura"):
      col1, col2 = st.columns(2)
      with col1:
        anno = st.selectbox(
            "Anno", options=list(range(2022, 2028)), index=4
        )  # Default 2026
        mese = st.selectbox(
            "Mese",
            [
                "Gennaio",
                "Febbraio",
                "Marzo",
                "Aprile",
                "Maggio",
                "Giugno",
                "Luglio",
                "Agosto",
                "Settembre",
                "Ottobre",
                "Novembre",
                "Dicembre",
            ],
        )
        tipo = st.selectbox("Tipologia Spesa", ["Energia Elettrica", "Gasolio"])
      with col2:
        fornitore = st.text_input(
            "Fornitore (es. Enel, Servizio Elettrico, Deposito Gasolio)"
        )
        imponibile = st.number_input(
            "Imponibile (€)", min_value=0.0, format="%.2f"
        )
        iva = st.number_input("IVA (€)", min_value=0.0, format="%.2f")

      submit_fat = st.form_submit_button("Salva Fattura")

      if submit_fat:
        if not fornitore:
          st.warning("Inserisci il nome del fornitore.")
        else:
          totale = imponibile + iva
          new_id = len(st.session_state.fatture) + 1
          nuova_riga = pd.DataFrame(
              [{
                  "ID": new_id,
                  "Anno": anno,
                  "Mese": mese,
                  "Tipo": tipo,
                  "Fornitore": fornitore,
                  "Imponibile": imponibile,
                  "IVA": iva,
                  "Totale": totale,
              }]
          )
          st.session_state.fatture = pd.concat(
              [st.session_state.fatture, nuova_riga], ignore_index=True
          )
          st.success("Fattura inserita con successo!")

  # --- 3. STORICO E DETTAGLIO ---
  elif menu == "Storico e Dettaglio":
    st.title("📂 Storico Fatture (Dal 2022)")

    if df_fatture.empty:
      st.info("Nessuna fattura registrata nello storico.")
    else:
      st.dataframe(df_fatture, use_container_width=True)

      st.markdown("### Elimina Fattura")
      id_da_eliminare = st.number_input(
          "Inserisci l'ID della fattura da rimuovere",
          min_value=1,
          step=1,
          value=1,
      )
      if st.button("Elimina"):
        if id_da_eliminare in df_fatture["ID"].values:
          st.session_state.fatture = df_fatture[
              df_fatture["ID"] != id_da_eliminare
          ].reset_index(drop=True)
          st.success(f"Fattura ID {id_da_eliminare} eliminata.")
          st.rerun()
        else:
          st.error("ID non trovato.")

  # --- 4. GESTIONE MILLESIMI TRAMITE METRATURA (MQ) ---
  elif menu == "Gestione Millesimi":
    st.title("⚙️ Calcolo Millesimi da Metrature (Mq)")
    st.markdown(
        "Inserisci la superficie in metri quadrati (mq) per ciascuno dei 7"
        " appartamenti. Il sistema calcolerà automaticamente i millesimi in"
        " proporzione."
    )

    with st.form("form_mq"):
      mq_appartamenti = {}
      col1, col2 = st.columns(2)

      app_names = [
          "Appartamento 1",
          "Appartamento 2",
          "Appartamento 3",
          "Appartamento 4",
          "Appartamento 5",
          "Appartamento 6",
          "Appartamento 7",
      ]

      for i, app in enumerate(app_names):
        with col1 if i < 4 else col2:
          default_mq = 70.0 + (i * 5)  # Valore indicativo iniziale
          mq_appartamenti[app] = st.number_input(
              f"Superficie {app} (mq)",
              min_value=1.0,
              value=float(default_mq),
              format="%.2f",
          )

      submit_calc = st.form_submit_button("Calcola e Aggiorna Millesimi")

      if submit_calc:
        tot_mq = sum(mq_appartamenti.values())
        if tot_mq <= 0:
          st.error("La superficie totale deve essere maggiore di zero.")
        else:
          nuovi_millesimi = {}
          for app, mq in mq_appartamenti.items():
            nuovi_millesimi[app] = round((mq / tot_mq) * 1000, 2)

          st.session_state.millesimi = nuevos_millesimi if 'nuevos_millesimi' in locals() else nuovi_millesimi
          st.session_state.millesimi = nuovi_millesimi
          st.success(
              f"Millesimi ricalcolati con successo! Superficie totale:"
              f" {tot_mq:.2f} mq"
          )
          st.rerun()
