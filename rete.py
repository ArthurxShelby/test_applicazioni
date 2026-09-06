import ipaddress
import pandas as pd
import streamlit as st

st.subheader("Gestione Reti e Hardware per Sede")

sedi_config = [
    {
        "id": 1,
        "nome": "Trieste",
        "blocco": "38.0",
        "subnet": "254.0",
        "gruppo": "",
    },
    {
        "id": 2,
        "nome": "trieste",
        "blocco": "39.0",
        "subnet": "254.0",
        "gruppo": "Blocco 2",
    },
    {
        "id": 3,
        "nome": "Sede 2",
        "blocco": "3.0",
        "subnet": "255.0",
        "gruppo": "Blocco Unico",
    },
    {
        "id": 4,
        "nome": "Sede 3",
        "blocco": "4.0",
        "subnet": "255.0",
        "gruppo": "Blocco Unico",
    },
    {
        "id": 5,
        "nome": "Sede 4",
        "blocco": "5.0",
        "subnet": "255.0",
        "gruppo": "Blocco Unico",
    },
    {
        "id": 6,
        "nome": "Sede 5",
        "blocco": "6.0",
        "subnet": "255.0",
        "gruppo": "Blocco Unico",
    },
    {
        "id": 7,
        "nome": "Sede 6",
        "blocco": "7.0",
        "subnet": "255.0",
        "gruppo": "Blocco Unico",
    },
    {
        "id": 8,
        "nome": "Sede 7",
        "blocco": "8.0",
        "subnet": "255.0",
        "gruppo": "Blocco Unico",
    },
]

if "dataframes_rete" not in st.session_state:
  st.session_state.dataframes_rete = {}
  for idx, item in enumerate(sedi_config):
    righe_ip = []
    if idx == 0:
      base_ip = "38"
      range_ip = range(1, 256)
    elif idx == 1:
      base_ip = "39"
      range_ip = range(1, 256)
    else:
      third_oct = item["blocco"].split(".")[0]
      base_ip = f"192.168.{third_oct}"
      range_ip = range(256)

    for i in range_ip:
      ip_completo = f"{base_ip}.{i}"
      parti = ip_completo.split(".")
      ultimi_due_ip = f"{parti[-2]}.{parti[-1]}"
      righe_ip.append({
          "Indirizzo IP": ultimi_due_ip,
          "_ip_completo": ip_completo,
          "Nome Macchina": "",
          "Stato": "🟢 Libero",
      })
    st.session_state.dataframes_rete[idx] = pd.DataFrame(righe_ip)
else:
  for idx, item in enumerate(sedi_config):
    if idx in st.session_state.dataframes_rete:
      df = st.session_state.dataframes_rete[idx]
      if idx == 0:
        base_ip = "38"
      elif idx == 1:
        base_ip = "39"
      else:
        third_oct = item["blocco"].split(".")[0]
        base_ip = f"192.168.{third_oct}"

      righe_ip = []
      for i, row in df.iterrows():
        if idx == 0:
          ip_num = i + 1
          ip_completo = f"38.{ip_num}"
          ultimi_due_ip = f"38.{ip_num}"
        elif idx == 1:
          ip_num = i + 1
          ip_completo = f"39.{ip_num}"
          ultimi_due_ip = f"39.{ip_num}"
        else:
          ip_parz = str(row.get("Indirizzo IP", f"1.{i}"))
          if ip_parz.count(".") == 1:
            ultimi_due_ip = ip_parz
            ip_completo = f"{base_ip}.{ip_parz.split('.')[-1]}"
          else:
            ip_completo = f"{base_ip}.{i}"
            parti = ip_completo.split(".")
            ultimi_due_ip = f"{parti[-2]}.{parti[-1]}"

        righe_ip.append({
            "Indirizzo IP": ultimi_due_ip,
            "_ip_completo": ip_completo,
            "Nome Macchina": row.get("Nome Macchina", ""),
            "Stato": row.get("Stato", "🟢 Libero"),
        })
      st.session_state.dataframes_rete[idx] = pd.DataFrame(righe_ip)

if "hardware_dettagli" not in st.session_state:
  st.session_state.hardware_dettagli = {}

idx_selezionato = st.selectbox(
    "📍 Seleziona la Sede da Gestire",
    options=range(len(sedi_config)),
    format_func=lambda i: (
        f"{sedi_config[i]['nome']} ({sedi_config[i]['gruppo']}) — Rete:"
        f" {sedi_config[i]['blocco']} / {sedi_config[i]['subnet']}"
    ),
)

sede_scelta = sedi_config[idx_selezionato]
if idx_selezionato == 0:
  blocco_completo_ip = "38"
elif idx_selezionato == 1:
  blocco_completo_ip = "39"
else:
  third_oct_scelto = sede_scelta["blocco"].split(".")[0]
  blocco_completo_ip = f"192.168.{third_oct_scelto}"

subnet_ultimi_due = sede_scelta["subnet"]

tab_rete, tab_hardware = st.tabs(
    ["🌐 Blocco IP & Occupazione", "💻 Inventario Hardware Dettagliato"]
)

with tab_rete:
  st.markdown(
      f"### 🌐 Gestione IP: {sede_scelta['nome']} - {sede_scelta['gruppo']}"
  )
  st.info(
      f"Subnet Mask associata: {subnet_ultimi_due} | Digita il nome macchina"
      " per occupare l'IP."
  )

  df_corrente = st.session_state.dataframes_rete[idx_selezionato]

  df_per_editor = df_corrente.drop(columns=["_ip_completo"], errors="ignore")

  df_modificato = st.data_editor(
      df_per_editor,
      column_config={
          "Indirizzo IP": st.column_config.TextColumn(
              "Indirizzo IP", disabled=True
          ),
          "Nome Macchina": st.column_config.TextColumn(
              "Nome Macchina (Digita e premi Invio)"
          ),
          "Stato": st.column_config.SelectboxColumn(
              "Stato", options=["🟢 Libero", "🔴 Occupato"], required=True
          ),
      },
      key=f"editor_sede_{idx_selezionato}",
      use_container_width=True,
      hide_index=True,
  )

  modificato = False
  for i in range(len(df_modificato)):
    ip_corr = df_corrente.loc[i, "_ip_completo"]
    val_grezzo = df_modificato.loc[i, "Nome Macchina"]

    if (
        val_grezzo is None
        or pd.isna(val_grezzo)
        or str(val_grezzo).strip().lower() in ["none", "nan", ""]
    ):
      nome_mac = ""
      df_modificato.loc[i, "Nome Macchina"] = ""
    else:
      nome_mac = str(val_grezzo).strip()

    stato_attuale = df_modificato.loc[i, "Stato"]

    if nome_mac and stato_attuale != "🔴 Occupato":
      df_modificato.loc[i, "Stato"] = "🔴 Occupato"
      modificato = True
    elif not nome_mac and stato_attuale == "🔴 Occupato":
      df_modificato.loc[i, "Stato"] = "🟢 Libero"
      if ip_corr in st.session_state.hardware_dettagli:
        del st.session_state.hardware_dettagli[ip_corr]
      modificato = True

    df_corrente.loc[i, "Nome Macchina"] = df_modificato.loc[i, "Nome Macchina"]
    df_corrente.loc[i, "Stato"] = df_modificato.loc[i, "Stato"]

  st.session_state.dataframes_rete[idx_selezionato] = df_corrente

  if modificato:
    st.rerun()

with tab_hardware:
  st.markdown(
      f"### 💻 Specifiche Hardware: {sede_scelta['nome']} -"
      f" {sede_scelta['gruppo']}"
  )

  df_rete_sede = st.session_state.dataframes_rete[idx_selezionato]

  with st.expander(
      "🛠️ Aggiungi dettagli tecnici avanzati (Manuale)", expanded=False
  ):
    macchine_occupate = df_rete_sede[
        df_rete_sede["Stato"] == "🔴 Occupato"
    ].to_dict("records")
    with st.form(key=f"form_hw_{idx_selezionato}"):
      ip_disponibili_mostrati = [
          m["Indirizzo IP"] for m in macchine_occupate if m["Nome Macchina"].strip()
      ]

      if ip_disponibili_mostrati:
        scelta_mostrata = st.selectbox("Seleziona IP Macchina", ip_disponibili_mostrati)
        ip_scelto = [
            m["_ip_completo"]
            for m in macchine_occupate
            if m["Indirizzo IP"] == scelta_mostrata
        ][0]

        col1, col2 = st.columns(2)
        with col1:
          hw_marca = st.text_input("Marca (es. Dell, HP)")
          hw_modello = st.text_input("Modello")
          hw_cpu = st.text_input("Processore")
        with col2:
          hw_ram = st.number_input("RAM (GB)", min_value=2, max_value=256, value=16)
          hw_tipo_hd = st.selectbox("Tipo HD", ["SSD", "HDD", "NVMe"])
          hw_cap_hd = st.text_input("Capienza HD")
          hw_garanzia = st.date_input("Scadenza Garanzia")

        btn_salva = st.form_submit_button("Salva Specifiche Tecniche")
        if btn_salva:
          st.session_state.hardware_dettagli[ip_scelto] = {
              "Marca": hw_marca,
              "Modello": hw_modello,
              "Processore": hw_cpu,
              "RAM": f"{hw_ram} GB",
              "Tipo HD": hw_tipo_hd,
              "Capienza HD": hw_cap_hd,
              "Garanzia": str(hw_garanzia),
          }
          st.success(f"Specifiche salvate con successo per l'IP {scelta_mostrata}!")
          st.rerun()
      else:
        st.info(
            "Prima inserisci almeno un nome macchina nella tab 'Blocco IP &"
            " Occupazione' per associargli i componenti hardware."
        )

  with st.expander("📁 Importa inventario da file (CSV o Excel)"):
    st.info(
        "Il file deve contenere almeno una colonna 'Indirizzo IP' e, se"
        " desideri, le colonne: 'Nome Macchina', 'Marca', 'Modello',"
        " 'Processore', 'RAM', 'Tipo HD', 'Capienza HD', 'Garanzia'."
    )
    uploaded_file = st.file_uploader(
        "Carica file CSV o XLSX", type=["csv", "xlsx"]
    )

    if uploaded_file is not None:
      try:
        if uploaded_file.name.endswith(".csv"):
          df_import = pd.read_csv(uploaded_file)
        else:
          df_import = pd.read_excel(uploaded_file)

        if "Indirizzo IP" not in df_import.columns:
          st.error(
              "Il file caricato deve contenere una colonna denominata"
              " 'Indirizzo IP'."
          )
        else:
          if st.button("Conferma e Importa Dati"):
            count_importati = 0
            base_ip_sede = blocco_completo_ip
            for _, row in df_import.iterrows():
              ip_file = str(row.get("Indirizzo IP", "")).strip()

              if idx_selezionato == 0:
                if not ip_file.startswith("38."):
                  ip_file_completo = f"38.{ip_file}"
                else:
                  ip_file_completo = ip_file
              elif idx_selezionato == 1:
                if not ip_file.startswith("39."):
                  ip_file_completo = f"39.{ip_file}"
                else:
                  ip_file_completo = ip_file
              else:
                if ip_file.count(".") == 1:
                  ip_file_completo = f"{base_ip_sede}.{ip_file.split('.')[-1]}"
                else:
                  ip_file_completo = ip_file

              if ip_file_completo.startswith(base_ip_sede):
                nome_mac_file = str(row.get("Nome Macchina", "")).strip()
                if (
                    nome_mac_file
                    and nome_mac_file != "nan"
                    and nome_mac_file != "None"
                ):
                  idx_r = df_rete_sede[
                      df_rete_sede["_ip_completo"] == ip_file_completo
                  ].index
                  if not idx_r.empty:
                    df_rete_sede.loc[idx_r, "Nome Macchina"] = nome_mac_file
                    df_rete_sede.loc[idx_r, "Stato"] = "🔴 Occupato"

                st.session_state.hardware_dettagli[ip_file_completo] = {
                    "Marca": str(row.get("Marca", "-")),
                    "Modello": str(row.get("Modello", "-")),
                    "Processore": str(row.get("Processore", "-")),
                    "RAM": str(row.get("RAM", "-")),
                    "Tipo HD": str(row.get("Tipo HD", "-")),
                    "Capienza HD": str(row.get("Capienza HD", "-")),
                    "Garanzia": str(row.get("Garanzia", "-")),
                }
                count_importati += 1

            st.session_state.dataframes_rete[idx_selezionato] = df_rete_sede
            st.success(
                f"Importati con successo {count_importati} dispositivi!"
            )
            st.rerun()
      except Exception as e:
        st.error(f"Errore nella lettura del file: {e}")

  st.markdown("---")
  st.write("📋 **Inventario Completo della Sede (Modificabile):**")

  macchine_occupate_aggiornate = df_rete_sede[
      df_rete_sede["Stato"] == "🔴 Occupato"
  ].to_dict("records")

  if macchine_occupate_aggiornate:
    lista_completa = []
    for m in macchine_occupate_aggiornate:
      ip_comp = m["_ip_completo"]
      dettagli = st.session_state.hardware_dettagli.get(ip_comp, {})

      lista_completa.append({
          "Indirizzo IP": m["Indirizzo IP"],
          "_ip_completo": ip_comp,
          "Nome Macchina": m["Nome Macchina"],
          "Marca": dettagli.get("Marca", "-"),
          "Modello": dettagli.get("Modello", "-"),
          "Processore": dettagli.get("Processore", "-"),
          "RAM": dettagli.get("RAM", "-"),
          "Tipo HD": dettagli.get("Tipo HD", "-"),
          "Capienza HD": dettagli.get("Capienza HD", "-"),
          "Garanzia": dettagli.get("Garanzia", "-"),
      })

    df_inventario_corrente = pd.DataFrame(lista_completa)
    df_inv_per_editor = df_inventario_corrente.drop(
        columns=["_ip_completo"], errors="ignore"
    )

    df_inventario_modificato = st.data_editor(
        df_inv_per_editor,
        column_config={
            "Indirizzo IP": st.column_config.TextColumn(
                "Indirizzo IP", disabled=True
            ),
            "Nome Macchina": st.column_config.TextColumn("Nome Macchina"),
            "Marca": st.column_config.TextColumn("Marca"),
            "Modello": st.column_config.TextColumn("Modello"),
            "Processore": st.column_config.TextColumn("Processore"),
            "RAM": st.column_config.TextColumn("RAM"),
            "Tipo HD": st.column_config.TextColumn("Tipo HD"),
            "Capienza HD": st.column_config.TextColumn("Capienza HD"),
            "Garanzia": st.column_config.TextColumn("Garanzia"),
        },
        key=f"editor_inventario_{idx_selezionato}",
        use_container_width=True,
        hide_index=True,
    )

    inv_modificato = False
    for i in range(len(df_inventario_modificato)):
      ip_comp = df_inventario_corrente.loc[i, "_ip_completo"]
      nuovo_nome = str(
          df_inventario_modificato.loc[i, "Nome Macchina"]
      ).strip()

      if (
          nuovo_nome == "None"
          or nuovo_nome == "nan"
          or nuovo_nome == ""
          or nuovo_nome is None
      ):
        nuovo_nome = ""
        df_inventario_modificato.loc[i, "Nome Macchina"] = ""

      st.session_state.hardware_dettagli[ip_comp] = {
          "Marca": str(df_inventario_modificato.loc[i, "Marca"]),
          "Modello": str(df_inventario_modificato.loc[i, "Modello"]),
          "Processore": str(df_inventario_modificato.loc[i, "Processore"]),
          "RAM": str(df_inventario_modificato.loc[i, "RAM"]),
          "Tipo HD": str(df_inventario_modificato.loc[i, "Tipo HD"]),
          "Capienza HD": str(df_inventario_modificato.loc[i, "Capienza HD"]),
          "Garanzia": str(df_inventario_modificato.loc[i, "Garanzia"]),
      }

      idx_r = df_rete_sede[df_rete_sede["_ip_completo"] == ip_comp].index
      if not idx_r.empty:
        vecchio_nome = str(df_rete_sede.loc[idx_r[0], "Nome Macchina"])
        if vecchio_nome != nuovo_nome:
          df_rete_sede.loc[idx_r, "Nome Macchina"] = nuovo_nome
          if nuovo_nome:
            df_rete_sede.loc[idx_r, "Stato"] = "🔴 Occupato"
          else:
            df_rete_sede.loc[idx_r, "Stato"] = "🟢 Libero"
            if ip_comp in st.session_state.hardware_dettagli:
              del st.session_state.hardware_dettagli[ip_comp]
          inv_modificato = True

    st.session_state.dataframes_rete[idx_selezionato] = df_rete_sede
    if inv_modificato:
      st.rerun()

  else:
    st.warning("Nessun dispositivo registrato in questa sede.")
