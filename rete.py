import ipaddress
import pandas as pd
import streamlit as st

st.subheader("Inventario Hardware e Gestione Sedi")

# Recupera le sedi (puoi sostituire questa finta chiamata con la query a Supabase: supabase.table('sedi').select('*').execute())
sedi_list = [
    {"id": 1, "nome": "Sede Centrale (Blocco 1)"},
    {"id": 2, "nome": "Sede Centrale (Blocco 2)"},
    {"id": 3, "nome": "Sede 2"},
    {"id": 4, "nome": "Sede 3"},
    {"id": 5, "nome": "Sede 4"},
    {"id": 6, "nome": "Sede 5"},
    {"id": 7, "nome": "Sede 6"},
    {"id": 8, "nome": "Sede 7"},
]

# Selezione della sede da gestire o visualizzare
sede_selezionata = st.selectbox(
    "Seleziona Sede", sedi_list, format_func=lambda x: x["nome"]
)

# Sezione per registrare o aggiornare una macchina per la sede scelta
with st.expander("➕ Registra / Aggiorna Hardware Macchina"):
  with st.form(key="form_hardware"):
    col1, col2 = st.columns(2)
    with col1:
      nome_macchina = st.text_input("Nome Macchina")
      indirizzo_ip = st.text_input("Indirizzo IP")
      marca = st.text_input("Marca (es. Dell, HP)")
      modello = st.text_input("Modello")
      processore = st.text_input("Processore (es. i7-12700)")
    with col2:
      ram_gb = st.number_input("RAM (GB)", min_value=2, max_value=256, value=16)
      tipo_hd = st.selectbox("Tipo HD", ["SSD", "HDD", "NVMe"])
      capienza_hd = st.text_input("Capienza HD (es. 512GB, 1TB)")
      garanzia = st.date_input("Scadenza Garanzia")

    submit_button = st.form_submit_button(
        label="Salva su Supabase (Simulato)"
    )
    if submit_button:
      st.success(
          f"Macchina {nome_macchina} ({indirizzo_ip}) associata con successo alla"
          f" {sede_selezionata['nome']}!"
      )

# Visualizzazione della tabella delle macchine registrate per la sede selezionata
st.markdown(f"### 💻 Elenco Macchine - {sede_selezionata['nome']}")

# Simulazione dei dati provenienti dalla tabella 'macchine' di Supabase filtrata per sede_id
dati_hardware_finti = [
    {
        "Nome Macchina": "PC-Ufficio-01",
        "IP": "192.168.1.15",
        "Marca": "Dell",
        "Modello": "OptiPlex 7090",
        "CPU": "i5-11500",
        "RAM": "16 GB",
        "HD": "512GB SSD",
        "Garanzia": "2027-05-12",
    }
]

df_macchine = pd.DataFrame(dati_hardware_finti)
st.dataframe(df_macchine, use_container_width=True, hide_index=True)
