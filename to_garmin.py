from datetime import date
import streamlit as st
from garminconnect import Garmin

# Configurazione della pagina Streamlit
st.title("Gestione Allenamenti Garmin Connect")
st.write(
    "Crea e pianifica i tuoi allenamenti strutturati (es. ripetute di potenza) direttamente nel calendario."
)

# --- Sezione Credenziali Garmin ---
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
    # Inizializzazione e login (gestisce anche l'autenticazione a due fattori se salvata nei token)
    client = Garmin(email, password)
    client.login()
    st.session_state.garmin_client = client
    st.success("Connessione a Garmin Connect riuscita!")
  except Exception as e:
    st.error(
        f"Errore durante il login (controlla credenziali o 2FA): {str(e)}"
    )

# --- Interfaccia di Creazione Allenamento ---
if st.session_state.garmin_client:
  st.divider()
  st.header("Configura Nuovo Allenamento Bici")

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
      client = st.session_state.garmin_client
      try:
        # Struttura dati richiesta dall'API Garmin per un workout di ciclismo
        # Nota: La struttura JSON esatta per i workout complessi richiede i codici categoria Garmin.
        # Qui impostiamo la struttura logica di base per un allenamento di ciclismo.

        # Creazione del payload dell'allenamento
        workout_data = {
            "workoutName": workout_name,
            "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": {"sportTypeId": 2, "sportTypeKey": "cycling"},
                    "workoutSteps": [
                        {
                            "type": "executableStep",
                            "stepOrder": 1,
                            "description": "Riscaldamento",
                            "endCondition": {
                                "conditionTypeId": 1,
                                "conditionTypeKey": "lap.button",
                            },
                            "targetType": {
                                "workoutTargetTypeId": 1,
                                "workoutTargetTypeKey": "no.target",
                            },
                        },
                        {
                            "type": "repeatGroup",
                            "stepOrder": 2,
                            "numberOfIterations": num_repeats,
                            "workoutSteps": [
                                {
                                    "type": "executableStep",
                                    "stepOrder": 1,
                                    "description": "Fase di spinta",
                                    "endCondition": {
                                        "conditionTypeId": 2,
                                        "conditionTypeKey": "time",
                                    },
                                    "endConditionValue": duration_minutes * 60,
                                    "targetType": {
                                        "workoutTargetTypeId": 4,
                                        "workoutTargetTypeKey": "power.zone",
                                    },
                                    "targetValueOne": power_min,
                                    "targetValueTwo": power_max,
                                },
                                {
                                    "type": "executableStep",
                                    "stepOrder": 2,
                                    "description": "Recupero",
                                    "endCondition": {
                                        "conditionTypeId": 1,
                                        "conditionTypeKey": "lap.button",
                                    },
                                    "targetType": {
                                        "workoutTargetTypeId": 1,
                                        "workoutTargetTypeKey": "no.target",
                                    },
                                },
                            ],
                        },
                    ],
                }
            ],
        }

        # Invio dei dati a Garmin usando il metodo corretto della libreria
        response = client.upload_workout(workout_data)

        # Estrazione dell'ID e pianificazione nel calendario
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
