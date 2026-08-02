from datetime import date
import streamlit as st

# Configurazione della pagina Streamlit
st.set_page_config(
    page_title="Generatore Guida Allenamenti Garmin",
    page_icon="🚴",
    layout="wide",
)
st.title("Assistente Strutturazione Allenamenti Garmin")

st.write(
    "Inserisci i parametri dell'allenamento: l'app calcolerà all'istante la"
    " sequenza esatta dei blocchi, le percentuali e i watt da impostare"
    " nell'editor di Garmin Connect."
)

with st.form("guide_form"):
  workout_name = st.text_input(
      "Nome Allenamento", value="Consolidamento_Streamlit"
  )

  st.subheader("Parametri dell'Allenamento")
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

  submitted = st.form_submit_button("Genera Guida Immediata")

  if submitted:
    st.session_state.show_guide = True
    st.session_state.g_name = workout_name
    st.session_state.g_repeats = num_repeats
    st.session_state.g_dur = duration_minutes
    st.session_state.g_pmin = power_min
    st.session_state.g_pmax = power_max
    st.session_state.g_ftp = ftp_ref

# --- Visualizzazione della Guida Strutturata ---
if "show_guide" in st.session_state and st.session_state.show_guide:
  st.divider()
  st.header(f"📋 Guida per: '{st.session_state.g_name}'")
  st.info(
      "Vai su Garmin Connect -> **Allenamento e pianificazione** ->"
      " **Allenamenti** -> **Crea allenamento** -> **Bici**, quindi compila i"
      " blocchi seguendo questi dati calcolati:"
  )

  # Calcoli automatici percentuali FTP
  avg_power = round(
      (st.session_state.g_pmin + st.session_state.g_pmax) / 2
  )
  p_pct = round((avg_power / st.session_state.g_ftp) * 100)
  recovery_power = round(st.session_state.g_ftp * 0.55)

  col_a, col_b = st.columns(2)

  with col_a:
    st.markdown("### 1️⃣ Riscaldamento (Warmup)")
    st.markdown("- **Tipo Durata:** Tempo")
    st.markdown("- **Valore Durata:** `5 minuti`")
    st.markdown("- **Target:** Senza target (o Potenza leggera al 50-75% FTP)")

    st.markdown("### 2️⃣ Blocco Ripetute (Ripetizioni)")
    st.markdown(
        f"- **Numero di ripetizioni:** `{st.session_state.g_repeats} volte`"
    )
    st.markdown("  - **Fase ON (Sforzo):**")
    st.markdown(f"    - Durata: `{st.session_state.g_dur} minuti`")
    st.markdown(
        f"    - Target Potenza: Range da **{st.session_state.g_pmin}W** a"
        f" **{st.session_state.g_pmax}W** (circa {p_pct}% FTP)"
    )
    st.markdown("  - **Fase OFF (Recupero):**")
    st.markdown("    - Durata: `3 minuti`")
    st.markdown(
        f"    - Target Potenza: Circa **{recovery_power}W** (55% FTP)"
    )

  with col_b:
    st.markdown("### 3️⃣ Defaticamento (Cooldown)")
    st.markdown("- **Tipo Durata:** Tempo")
    st.markdown("- **Valore Durata:** `5 minuti`")
    st.markdown("- **Target:** Senza target")

    st.markdown("---")
    st.success(
        "✅ Una volta impostati i blocchi con questi valori nell'editor di"
        " Garmin, clicca su **Salva allenamento**. Sarà subito pronto e"
        " sincronizzato sul tuo ciclocomputer!"
    )
