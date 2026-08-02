from datetime import date
import streamlit as st

# Configurazione della pagina Streamlit
st.set_page_config(
    page_title="Guida Strutturata Allenamenti Garmin",
    page_icon="🚴",
    layout="wide",
)
st.title("Generatore Guida Allenamenti per Garmin Connect")

st.write(
    "Inserisci i parametri dell'allenamento: l'app ti restituirà la struttura"
    " esatta da ricopiare nell'editor ufficiale di Garmin Connect (sezione"
    " Allenamenti -> Crea allenamento)."
)

with st.form("guide_form"):
  workout_name = st.text_input(
      "Nome Allenamento", value="Consolidamento_Streamlit"
  )

  st.subheader("Parametri Principali")
  col1, col2 = st.columns(2)
  with col1:
    num_repeats = st.number_input(
        "Numero di Ripetizioni", min_value=1, max_value=20, value=4
    )
    power_min = st.number_input(
        "Potenza Min Sforzo (W)", min_value=50, max_value=500, value=250
    )
  with col2:
    duration_minutes = st.number_input(
        "Durata Sforzo (minuti)", min_value=1, max_value=60, value=10
    )
    power_max = st.number_input(
        "Potenza Max Sforzo (W)", min_value=50, max_value=500, value=260
    )

  ftp_ref = st.number_input(
      "Tua FTP di riferimento (W)", min_value=100, max_value=400, value=260
  )

  submitted = st.form_submit_button("Genera Guida per Garmin")

  if submitted:
    st.session_state.show_guide = True
    st.session_state.g_name = workout_name
    st.session_state.g_repeats = num_repeats
    st.session_state.g_dur = duration_minutes
    st.session_state.g_pmin = power_min
    st.session_state.g_pmax = power_max
    st.session_state.g_ftp = ftp_ref

# --- Visualizzazione della Guida Passo-Passo ---
if "show_guide" in st.session_state and st.session_state.show_guide:
  st.divider()
  st.header(
      f"📋 Guida per la creazione di: '{st.session_state.g_name}'"
  )
  st.info(
      "Apri Garmin Connect -> Allenamento e pianificazione -> Allenamenti ->"
      " **Crea allenamento** -> **Bici**, quindi compila i blocchi come"
      " indicato di seguito:"
  )

  # Calcoli di supporto
  avg_power = round((st.session_state.g_pmin + st.session_state.g_pmax) / 2)
  p_pct = round((avg_power / st.session_state.g_ftp) * 100)

  col_a, col_b = st.columns(2)

  with col_a:
    st.markdown("### 1️⃣ Riscaldamento (Warmup)")
    st.markdown("- **Durata:** 5 minuti (o a pressione tasto Lap)")
    st.markdown("- **Target:** Senza target o Potenza al 50-75% FTP")

    st.markdown("### 2️⃣ Blocco Ripetute (Ripeti X volte)")
    st.markdown(
        f"- **Numero di ripetizioni:** `{st.session_state.g_repeats}` volte"
    )
    st.markdown(
        f"- **Fase ON (Sforzo):** Durata `{st.session_state.g_dur} minuti`"
    )
    st.markdown(
        f"  - *Target Potenza:* Range da **{st.session_state.g_pmin}W** a"
        f" **{st.session_state.g_pmax}W** (circa {p_pct}% FTP)"
    )
    st.markdown(
        f"- **Fase OFF (Recupero):** Durata `3 minuti` (o a pressione tasto"
        " Lap)"
    )
    st.markdown("  - *Target:* Potenza leggera (circa 55% FTP)")

  with col_b:
    st.markdown("### 3️⃣ Defaticamento (Cooldown)")
    st.markdown("- **Durata:** 5 minuti")
    st.markdown("- **Target:** Senza target o Potenza decrescente")

    st.markdown("---")
    st.success(
        f"✅ Una volta inseriti questi blocchi nell'editor web di Garmin,"
        f" clicca su **Salva allenamento**. Sarà subito pronto nel tuo"
        f" elenco per essere pianificato sul calendario!"
    )
