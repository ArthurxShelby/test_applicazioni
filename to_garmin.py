from datetime import date
import streamlit as st
from garminconnect import Garmin

# Configurazione della pagina Streamlit
st.set_page_config(
    page_title="Gestione Allenamenti Garmin", page_icon="🚴", layout="wide"
)
st.title("Gestione Allenamenti Garmin Connect")

st.write(
    "Gestisci e pianifica i tuoi allenamenti strutturati di ciclismo direttamente"
    " sul calendario Garmin."
)

# --- Sezione Credenziali Garmin (Sidebar) ---
with st.sidebar:
  st.header("Accesso Garmin Connect")
  email = st.text_input("Email Garmin")
  password = st.text_input("Password Garmin", type="password")
  login_btn = st.button("Connetti a Garmin")

# Gestione della sessione Garmin
if "garmin_client" not in st.session_state:
  st.session_state.garmin_client = None

if login_btn and email and password:
  try:
    client = Garmin(email, password)
    client.login()
    st.session_state.garmin_client = client
    st.success("Connessione a Garmin Connect riuscita!")
  except Exception as e:
    st.error(f"Errore durante il login (controlla credenziali o 2FA): {str(e)}")

# --- Interfaccia Principale ---
if st.session_state.garmin_client:
  client = st.session_state.garmin_client

  st.divider()
  st.header("Crea e Programma Nuovo Allenamento")

  with st.form("workout_form"):
    workout_name = st.text_input(
        "Nome Allenamento", value="Consolidamento_Streamlit"
    )
    workout_date = st.date_input("Data di Pianificazione", value=date.today())

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

    submitted = st.form_submit_button("Crea e Programma su Garmin")

    if submitted:
      try:
        # Semplificazione radicale del payload per evitare InvalidTypeIdException
        workout_data = {
            "workoutName": workout_name,
            "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
            "description": (
                f"Ripetute: {num_repeats}x {duration_minutes}min"
                f" ({power_min}-{power_max}W)"
            ),
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
                    "workoutSteps": [
                        {
                            "type": "executableStep",
                            "stepOrder": 1,
                            "description": "Riscaldamento libero",
                            "durationValue": 0,
                            "durationUnit": {
                                "unitId": 1,
                                "unitKey": "distance",
                            },
                            "targetType": {
                                "workoutTargetTypeId": 1,
                                "workoutTargetTypeKey": "no.target",
                            },
                        },
                        {
                            "type": "executableStep",
                            "stepOrder": 2,
                            "description": "Blocco Intervalli",
                            "durationValue": duration_minutes
                            * 60
                            * num_repeats,
                            "durationUnit": {"unitId": 2, "unitKey": "time"},
                            "targetType": {
                                "workoutTargetTypeId": 3,
                                "workoutTargetTypeKey": "power",
                            },
                            "targetValueOne": power_min,
                            "targetValueTwo": power_max,
                        },
                    ],
                }
            ],
        }

        # Invio a Garmin
        response = client.upload_workout(workout_data)
        workout_id = response.get("workoutId")

        date_str = workout_date.strftime("%Y-%m-%d")
        client.schedule_workout(workout_id, date_str)

        st.success(
            f"Allenamento '{workout_name}' creato e pianificato con successo"
            f" per il {date_str}!"
        )

      except Exception as e:
        st.error(f"Errore durante la creazione/programmazione: {str(e)}")
else:
  st.info(
      "Inserisci le credenziali nella barra laterale per connetterti a Garmin"
      " Connect."
  )
