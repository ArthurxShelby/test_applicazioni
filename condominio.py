import pandas as pd
import streamlit as st

# Configurazione della pagina
st.set_page_config(
    page_title="Gestione Spese Condominiali", page_icon="🏢", layout="wide"
)

# --- CONFIGURAZIONE NOMI E VALORI INIZIALI (7 unità) ---
APP_NAMES = [
    "ESPOSITO",
    "MARANGI",
    "LINCESSO",
    "FUSO",
    "PUCA",
    "BAVILA",
    "TESTA",
]

DEFAULT_MQ = {
    "ESPOSITO": 70.0,
    "MARANGI": 75.0,
    "LINCESSO": 80.0,
    "FUSO": 85.0,
    "PUCA": 90.0,
    "BAVILA": 85.0,
    "TESTA": 85.0,
}

DEFAULT_MILLESIMI = {
    "ESPOSITO": 120,
    "MARANGI": 130,
    "LINCESSO": 140,
    "FUSO": 150,
    "PUCA": 160,
    "BAVILA": 150,
    "TESTA": 150,
}

# --- SIMULAZIONE DATABASE IN SESSION STATE ---
if "logged_in" not in st.session_state:
  st.session_state.logged_in = False

if "mq_appartamenti" not in st.session_state:
  st.session_state.mq_appartamenti = DEFAULT_MQ.copy()

if "millesimi" not in st.session_state:
  st.session_state.millesimi = DEFAULT_MILLESIMI.copy()

if "fatture" not in st.session_state:
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
      anni_disponibili = sorted(df_fatture["Anno"].unique())
      selected_anno = st.selectbox(
          "Seleziona Anno Fiscale",
          ["Tutti gli anni (da 2022)"] + list(anni_disponibili),
      )

      if selected_anno != "Tutti gli anni (da 2022)":
        df_filtered = df_fatture[df_fatture["Anno"] == selected_anno]
      else:
        df_filtered = df_fatture

      col1, col2, col3 = st.columns(3)
      tot_imp = df_filtered["Imponibile"].sum()
      tot_iva = df_filtered["IVA"].sum()
      tot_complessivo = df_filtered["Totale"].sum()

      col1.metric("Totale Imponibile", f"€ {tot_imp:,.2f}")
      col2.metric("Totale IVA", f"€ {tot_iva:,.2f}")
      col3.metric("Totale Generale", f"€ {tot_complessivo:,.2f}")

      st.markdown("---")
      st.subheader("Tabella di Riparto per Condomino (Millesimi)")

      reparto_data = []
      for app, mil in millesimi.items():
        quota_imp = tot_imp * (mil / tot_millesimi) if tot_millesimi > 0 else 0
        quota_iva = tot_iva * (mil / tot_millesimi) if tot_millesimi > 0 else 0
        quota_tot = (
            tot_complessivo * (mil / tot_millesimi) if tot_millesimi > 0 else 0
        )
        reparto_data.append(
            {
                "Condomino": app,
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
        anno = st.selectbox("Anno", options=list(range(2022, 2028)), index=4)
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

  # --- 4. GESTIONE MILLESIMI TRAMITE METRATURA (MQ) CON PERSISTENZA ---
  elif menu == "Gestione Millesimi":
    st.title("⚙️ Calcolo Millesimi da Metrature (Mq)")
    st.markdown(
        "Inserisci la superficie in metri quadrati (mq) per ciascun condomino."
        " I valori rimarranno salvati in memoria."
    )

    with st.form("form_mq"):
      nuovi_mq = {}
      col1, col2 = st.columns(2)

      for i, app in enumerate(APP_NAMES):
        with col1 if i < 4 else col2:
          val_corrente = st.session_state.mq_appartamenti.get(app, 70.0)
          nuovi_mq[app] = st.number_input(
              f"Superficie {app} (mq)",
              min_value=1.0,
              value=float(val_corrente),
              format="%.2f",
          )

      submit_calc = st.form_submit_button("Calcola e Salva Millesimi")

      if submit_calc:
        tot_mq = sum(nuovi_mq.values())
        if tot_mq <= 0:
          st.error("La superficie totale deve essere maggiore di zero.")
        else:
          nuovi_millesimi = {}
          for app, mq in nuovi_mq.items():
            nuovi_millesimi[app] = round((mq / tot_mq) * 1000, 2)

          # Salvataggio persistente nello state
          st.session_state.mq_appartamenti = nuovi_mq
          st.session_state.millesimi = nuovi_millesimi
          st.success(
              f"Metrature e millesimi salvati con successo! Superficie totale:"
              f" {tot_mq:.2f} mq"
          )
          st.rerun()

    st.markdown("---")
    st.subheader("Tabella Millesimale Attuale")
    df_mil_current = pd.DataFrame(
        list(st.session_state.millesimi.items()),
        columns=["Condomino", "Valore Millesimale"],
    )
    st.dataframe(df_mil_current, use_container_width=True)
