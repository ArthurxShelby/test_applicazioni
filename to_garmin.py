from datetime import date
import xml.etree.ElementTree as ET
import streamlit as st

# Configurazione della pagina Streamlit
st.set_page_config(
    page_title="Generatore Allenamenti ZWO", page_icon="🚴", layout="wide"
)
st.title("Generatore Allenamenti per Garmin / Zwift (.zwo)")

st.write(
    "Crea i tuoi allenamenti strutturati in formato standard `.zwo`. "
    "Il file potrà essere scaricato e caricato direttamente nella sezione"
    " **Allenamenti** di Garmin Connect."
)

# Inizializzazione della variabile di sessione per il file XML
if "zwo_data" not in st.session_state:
  st.session_state.zwo_data = None
if "zwo_filename" not in st.session_state:
  st.session_state.zwo_filename = "allenamento.zwo"

with st.form("zwo_form"):
  workout_name = st.text_input(
      "Nome Allenamento", value="Consolidamento_Streamlit"
  )
  author_name = st.text_input("Autore", value="Atleta")

  st.subheader("Parametri Blocco Ripetute")
  col1, col2 = st.columns(2)
  with col1:
    num_repeats = st.number_input(
        "Numero di Ripetizioni", min_value=1, max_value=20, value=4
    )
    power_min = st.number_input(
        "Potenza Min (W)", min_value=50, max_value=500, value=250
    )
  with col2:
    duration_minutes = st.number_input(
        "Durata Sforzo (minuti)", min_value=1, max_value=60, value=10
    )
    power_max = st.number_input(
        "Potenza Max (W)", min_value=50, max_value=500, value=260
    )

  ftp_ref = st.number_input(
      "Tua FTP di riferimento (W) [per calcolo percentuali]",
      min_value=100,
      max_value=400,
      value=260,
  )

  submitted = st.form_submit_button("Genera Contenuto ZWO")

  if submitted:
    try:
      # Creazione della struttura XML per il file .zwo standard
      root = ET.Element("workout_file")

      author = ET.SubElement(root, "author")
      author.text = author_name

      name = ET.SubElement(root, "name")
      name.text = workout_name

      description = ET.SubElement(root, "description")
      description.text = (
          f"Ripetute: {num_repeats}x {duration_minutes}min"
          f" ({power_min}-{power_max}W)"
      )

      sportType = ET.SubElement(root, "sportType")
      sportType.text = "bike"

      workout_elem = ET.SubElement(root, "workout")

      # Riscaldamento iniziale
      ET.SubElement(
          workout_elem,
          "Warmup",
          Duration="300",
          PowerLow="0.50",
          PowerHigh="0.75",
      )

      # Blocco Ripetute
      repeat_elem = ET.SubElement(workout_elem, "Repeat")
      repeat_elem.set("Repeat", str(num_repeats))
      repeat_elem.set("OnDuration", str(duration_minutes * 60))
      repeat_elem.set("OffDuration", "180")

      p_avg_pct = round(
          (((power_min + power_max) / 2) / ftp_ref),
          2,
      )

      ET.SubElement(
          repeat_elem,
          "SteadyState",
          Duration=str(duration_minutes * 60),
          Power=str(p_avg_pct),
      )
      ET.SubElement(repeat_elem, "Recovery", Duration="180", Power="0.55")

      # Defaticamento finale
      ET.SubElement(
          workout_elem,
          "Cooldown",
          Duration="300",
          PowerLow="0.75",
          PowerHigh="0.50",
      )

      # Salvataggio nella sessione anziché usare il download button dentro il form
      st.session_state.zwo_data = ET.tostring(
          root, encoding="utf-8", method="xml"
      ).decode("utf-8")
      st.session_state.zwo_filename = f"{workout_name.replace(' ', '_')}.zwo"

      st.success("Parametri elaborati con successo! Scarica il file qui sotto.")

    except Exception as e:
      st.error(f"Errore nella generazione del file: {str(e)}")

# --- Pulsante di download posizionato FUORI dal form ---
if st.session_state.zwo_data is not None:
  st.divider()
  st.download_button(
      label="📥 Clicca qui per scaricare il file .zwo",
      data=st.session_state.zwo_data,
      file_name=st.session_state.zwo_filename,
      mime="application/xml",
  )
