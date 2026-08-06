import pandas as pd
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

  # Valori di default nel caso la tabella sia vuota
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


# --- INIZIALIZZAZIONE SESSION STATE ---
if "logged_in" not in st.session_state:
  st.session_state.logged_in = False

if "mq_appartamenti" not in st.session_state:
  st.session_state.mq_appartamenti = carica_mq_da_supabase()

if "fatture" not in st.session_state:
  st.session_state.fatture = carica_fatture_da_supabase()


def calcola_millesimi_da_mq(mq_dict):
  tot_mq = sum(mq_dict.values())
  if tot_mq <= 0:
    return {k: 0 for k in mq_dict}
  return {app: round((mq / tot_mq) * 1000, 2) for app, mq in mq_dict.items()}


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
  millesimi = calcola_millesimi_da_mq(st.session_state.mq_appartamenti)
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
      # Filtri in alto
      col_f1, col_f2 = st.columns(2)
      with col_f1:
        anni_disponibili = sorted(df_fatture["anno"].unique())
        selected_anno = st.selectbox(
            "Seleziona Anno Fiscale",
            ["Tutti gli anni (da 2022)"] + list(anni_disponibili),
        )
      with col_f2:
        selected_tipo = st.selectbox(
            "Seleziona Tipologia Spesa",
            ["Tutte le tipologie", "Energia Elettrica", "Gasolio"],
        )

      # Applicazione filtri
      df_filtered = df_fatture.copy()
      if selected_anno != "Tutti gli anni (da 2022)":
        df_filtered = df_filtered[df_filtered["anno"] == selected_anno]
      if selected_tipo != "Tutte le tipologie":
        df_filtered = df_filtered[df_filtered["tipo"] == selected_tipo]

      st.markdown("---")

      # Indicatori metrici
      col1, col2, col3 = st.columns(3)
      tot_imp = df_filtered["imponibile"].sum()
      tot_iva = df_filtered["iva"].sum()
      tot_complessivo = df_filtered["totale"].sum()

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

      # Mostra anche l'elenco delle fatture filtrate incluse in questo calcolo
      with st.expander(
          "Visualizza l'elenco delle fatture incluse in questo calcolo"
      ):
        if df_filtered.empty:
          st.info(
              "Nessuna fattura corrisponde ai filtri selezionati."
          )
        else:
          st.dataframe(
              df_filtered[
                  [
                      "id",
                      "anno",
                      "mese",
                      "tipo",
                      "fornitore",
                      "imponibile",
                      "iva",
                      "totale",
                  ]
              ],
              use_container_width=True,
          )

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

      submit_fat = st.form_submit_button("Salva Fattura su Supabase")

      if submit_fat:
        if not fornitore:
          st.warning("Inserisci il nome del fornitore.")
        else:
          totale = imponibile + iva
          nuova_fattura = {
              "anno": int(anno),
              "mese": mese,
              "tipo": tipo,
              "fornitore": fornitore,
              "imponibile": float(imponibile),
              "iva": float(iva),
              "totale": float(totale),
          }

          try:
            supabase.table("fatture").insert(nuova_fattura).execute()
            st.session_state.fatture = carica_fatture_da_supabase()
            st.success("Fattura salvata con successo su Supabase!")
          except Exception as e:
            st.error(f"Errore durante il salvataggio della fattura: {e}")

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
        try:
          supabase.table("fatture").delete().eq(
              "id", int(id_da_eliminare)
          ).execute()
          st.session_state.fatture = carica_fatture_da_supabase()
          st.success(
              f"Fattura ID {id_da_eliminare} eliminata da Supabase con successo!"
          )
          st.rerun()
        except Exception as e:
          st.error(f"Errore durante l'eliminazione: {e}")

  # --- 4. GESTIONE MILLESIMI TRAMITE METRATURA (MQ) ---
  elif menu == "Gestione Millesimi":
    st.title("⚙️ Calcolo Millesimi da Metrature (Mq)")
    st.markdown(
        "Inserisci la superficie in metri quadrati (mq) per ciascun condomino."
        " I dati verranno salvati direttamente nel database cloud Supabase."
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

      submit_calc = st.form_submit_button("Calcola e Salva su Supabase")

      if submit_calc:
        tot_mq = sum(nuovi_mq.values())
        if tot_mq <= 0:
          st.error("La superficie totale deve essere maggiore di zero.")
        else:
          successo = salva_mq_su_supabase(nuovi_mq)
          if successo:
            st.session_state.mq_appartamenti = carica_mq_da_supabase()
            st.success(
                f"Metrature salvate permanentemente su Supabase! Superficie"
                f" totale: {tot_mq:.2f} mq"
            )
            st.rerun()

    st.markdown("---")
    st.subheader("Tabella Millesimale Attuale")
    df_mil_current = pd.DataFrame(
        list(millesimi.items()), columns=["Condomino", "Valore Millesimale"]
    )
    st.dataframe(df_mil_current, use_container_width=True)
