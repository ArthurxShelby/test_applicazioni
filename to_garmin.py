from datetime import date
from garminconnect import Garmin
import streamlit as st

# Configurazione della pagina Streamlit
st.set_page_config(
    page_title="Integrazione Diretta Garmin", page_icon="🚴", layout="wide"
)
st.title("Generatore e Sincronizzatore Garmin Connect")

st.write(
    "Crea e programma l'allenamento strutturato direttamente nel tuo calendario"
    " Garmin Connect tramite le API."
)

with st.form("garmin_direct_form"):
  st.subheader("Credenziali Garmin Connect")
  col_c1, col_c2 = st.columns(2)
  with col_c1:
    email = st.text_input("Email Garmin", value="")
  with col_c2:
    password = st.text_input("Password Garmin", type="password", value="")

  st.subheader("Dettagli Allenamento")
  workout_name = st.text_input(
      "Nome Allenamento", value="Consolidamento Streamlit"
  )
  workout_date = st.date_input("Data di Programmazione", value=date.today())

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

  submitted = st.form_submit_button("Crea e Programma su Garmin")

  if submitted:
    if not email or not password:
      st.error("Inserisci email e password di Garmin Connect.")
    else:
      try:
        with st.spinner("Connessione a Garmin Connect in corso..."):
          client = Garmin(email, password)
          client.login()

        with st.spinner("Creazione dell'allenamento strutturato..."):
          # Payload strutturato con i tipi di target conformi alle API Garmin
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
                      "sportType": {
                          "sportTypeId": 2,
                          "sportTypeKey": "cycling",
                      },
                      "workoutSteps": [
                          {
                              "type": "executableStep",
                              "stepOrder": 1,
                              "description": "Riscaldamento",
                              "durationValue": 300,  # 5 minuti in secondi
                              "durationUnit": {
                                  "unitId": 2,
                                  "unitKey": "time",
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
                              "smartRepeat": False,
                              "workoutSteps": [
                                  {
                                      "type": "executableStep",
                                      "stepOrder": 1,
                                      "description": "Sforzo",
                                      "durationValue": duration_minutes * 60,
                                      "durationUnit": {
                                          "unitId": 2,
                                          "unitKey": "time",
                                      },
                                      "targetType": {
                                          "workoutTargetTypeId": 3,
                                          "workoutTargetTypeKey": "power",
                                      },
                                      "targetValueOne": power_min,
                                      "targetValueTwo": power_max,
                                      "zoneNumber": None,
                                  },
                                  {
                                      "type": "executableStep",
                                      "stepOrder": 2,
                                      "description": "Recupero",
                                      "durationValue": 180,  # 3 minuti
                                      "durationUnit": {
                                          "unitId": 2,
                                          "unitKey": "time",
                                      },
                                      "targetType": {
                                          "workoutTargetTypeId": 1,
                                          "workoutTargetTypeKey": "no.target",
                                      },
                                  },
                              ],
                          },
                          {
                              "type": "executableStep",
                              "stepOrder": 3,
                              "description": "Defaticamento",
                              "durationValue": 300,
                              "durationUnit": {
                                  "unitId": 2,
                                  "unitKey": "time",
                              },
                              "targetType": {
                                  "workoutTargetTypeId": 1,
                                  "workoutTargetTypeKey": "no.target",
                              },
                          },
                      ],
                  }
              ],
          }

          # Invio dei dati per la creazione dell'allenamento
          response = client.upload_workout(workout_data)
          workout_id = response.get("workoutId")

          if workout_id:
            # Programmazione sul calendario nella data scelta
            date_str = workout_date.strftime("%Y-%m-%d")
            client.schedule_workout(workout_id, date_str)
            st.success(
                f"Allenamento '{workout_name}' creato e pianificato sul"
                f" calendario per il giorno {date_str} con successo!"
            )
          else:
            st.error(
                "Impossibile recuperare il workoutId dalla risposta di Garmin."
            )

      except Exception as e:
        st.error(f"Errore durante la comunicazione con Garmin: {str(e)}")
