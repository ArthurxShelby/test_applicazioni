import ipaddress
import io
import re
from fpdf import FPDF
import pandas as pd
import streamlit as st

# Configurazione della pagina Streamlit
st.set_page_config(
    page_title="Gestione Reti e Hardware per Sede", page_icon="💻", layout="wide"
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 3rem;
        padding-right: 3rem;
        max-width: 100% !important;
    }
    div[data-testid="stDataEditor"] {
        width: 100% !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ----------------------------------------------------
# GESTIONE AUTENTICAZIONE TRAMITE st.secrets
# ----------------------------------------------------
if "autenticato" not in st.session_state:
  st.session_state.autenticato = False

if not st.session_state.autenticato:
  st.subheader("🔐 Accesso Protetto")
  password_inserita = st.text_input(
      "Inserisci la password per accedere", type="password"
  )
  if st.button("Accedi"):
    app_password = st.secrets.get("APP_PASSWORD", "")
    if password_inserita == app_password:
      st.session_state.autenticato = True
      st.rerun()
    else:
      st.error("Password errata.")
  st.stop()

# ----------------------------------------------------
# INTEGRAZIONE SUPABASE
# ----------------------------------------------------
try:
  from supabase import create_client

  SUPABASE_DISPONIBILE = True
except ImportError:
  SUPABASE_DISPONIBILE = False


def get_supabase_client():
  if not SUPABASE_DISPONIBILE:
    return None
  try:
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if url and key:
      return create_client(url, key)
  except Exception:
    pass
  return None


supabase = get_supabase_client()

# Rilevamento dispositivo mobile
try:
  from streamlit_javascript import st_javascript

  is_mobile_env = True
except ImportError:
  is_mobile_env = False

tipo_dispositivo = "PC / Desktop"
if is_mobile_env:
  try:
    screen_width = st_javascript("window.innerWidth")
    if screen_width and isinstance(screen_width, (int, float)):
      if screen_width < 768:
        tipo_dispositivo = "Smartphone"
      elif 768 <= screen_width < 1024:
        tipo_dispositivo = "Tablet"
  except:
    pass

st.subheader("Gestione Reti e Hardware per Sede")
st.caption(f"💻 Dispositivo rilevato: **{tipo_dispositivo}**")

# Configurazione delle Sedi
sedi_config = [
    {
        "id": 1,
        "nome": "Trieste",
        "blocco": "38.0",
        "subnet": "254.0",
        "range_custom": range(1, 256),
    },
    {
        "id": 2,
        "nome": "Sede Centrale",
        "blocco": "39.0",
        "subnet": "254.0",
        "range_custom": range(1, 256),
    },
    {
        "id": 3,
        "nome": "Monfalcone",
        "blocco": "86.0",
        "subnet": "255.0",
        "range_custom": range(1, 256),
    },
    {
        "id": 4,
        "nome": "Grado",
        "blocco": "168.0",
        "subnet": "255.0",
        "range_custom": range(1, 256),
    },
    {
        "id": 5,
        "nome": "Nogaro",
        "blocco": "61.0",
        "subnet": "255.0",
        "range_custom": range(1, 256),
    },
    {
        "id": 6,
        "nome": "Lignao",
        "blocco": "26.0",
        "subnet": "255.0",
        "range_custom": range(1, 256),
    },
    {
        "id": 7,
        "nome": "Marano",
        "blocco": "29.0",
        "subnet": "255.0",
        "range_custom": range(1, 256),
    },
    {
        "id": 8,
        "nome": "MMnn",
        "blocco": "66.0",
        "subnet": "255.0",
        "range_custom": range(1, 256),
    },
    {
        "id": 9,
        "nome": "P.nuovo",
        "blocco": "77.0",
        "subnet": "255.192",
        "range_custom": range(65, 127),
    },
]

NOME_TABELLA_SUPABASE = "inventario_hardware"


def carica_dati_da_supabase():
  if not supabase:
    return []
  try:
    response = supabase.table(NOME_TABELLA_SUPABASE).select("*").execute()
    dati = response.data if response.data else []

    # PULIZIA DI SICUREZZA BLOCCO 38:
    # Rimuove l'SSD forzato se nel campo capienza non c'è scritto esplicitamente SSD
    for row in dati:
      ip = str(row.get("ip_completo", ""))
      if ip.startswith("38.") and row.get("tipo_hd") == "SSD":
        cap = str(row.get("capienza_hd", ""))
        if "SSD" not in cap.upper():
          row["tipo_hd"] = ""

    return dati
  except Exception as e:
    st.warning(f"Impossibile connettersi a Supabase: {e}")
  return []


def salva_o_aggiorna_su_supabase(ip_completo, sede_nome, dati_hw, dati_rete):
  if not supabase:
    return
  try:
    payload = {
        "ip_completo": ip_completo,
        "sede": sede_nome,
        "nome_macchina": dati_rete.get("Nome Macchina", ""),
        "tipologia": dati_rete.get("Tipologia", ""),
        "stato": dati_rete.get("Stato", "🟢 Libero"),
        "marca": dati_hw.get("Marca", ""),
        "modello": dati_hw.get("Modello", ""),
        "s_o": dati_hw.get("S.O.", ""),
        "processore": dati_hw.get("Processore", ""),
        "ram": dati_hw.get("RAM", ""),
        "tipo_hd": dati_hw.get("Tipo HD", ""),
        "capienza_hd": dati_hw.get("Capienza HD", ""),
        "garanzia": dati_hw.get("Garanzia", ""),
    }
    supabase.table(NOME_TABELLA_SUPABASE).upsert(
        payload, on_conflict="ip_completo"
    ).execute()
  except Exception as e:
    print("Errore salvataggio Supabase:", e)


def elimina_da_supabase(ip_completo):
  if not supabase:
    return
  try:
    supabase.table(NOME_TABELLA_SUPABASE).delete().eq(
        "ip_completo", ip_completo
    ).execute()
  except Exception as e:
    print("Errore cancellazione Supabase:", e)


dati_supabase = carica_dati_da_supabase()


def pulisci_valore(val):
  if val is None or pd.isna(val):
    return ""
  s = str(val).strip()
  if s.lower() in ["none", "nan", "", "-"]:
    return ""
  return s


def estrai_marca_e_modello(testo_modello):
  testo = pulisci_valore(testo_modello)
  if not testo:
    return "", ""
  parti = testo.split(" ", 1)
  marca = parti[0]
  modello = parti[1] if len(parti) > 1 else ""
  return marca, modello


def estrai_anno(testo):
  if not testo:
    return 9999
  match = re.search(r"\b(19\d{2}|20\d{2})\b", str(testo))
  if match:
    return int(match.group(1))
  return 9999


# FUNZIONE HD CORRETTA (NON FORZA PIÙ "SSD" SUL BLOCCO 38)
def processa_stringa_hd(testo_capienza, tipo_hd_attuale):
  cap_str = pulisci_valore(testo_capienza)
  tipo_str = pulisci_valore(tipo_hd_attuale)

  match_tipo = re.search(r"\b(SSD|HDD|NVMe)\b", cap_str, re.IGNORECASE)
  if match_tipo:
    trovato = match_tipo.group(1).upper()
    if not tipo_str or tipo_str == "-":
      tipo_str = trovato
    cap_str = re.sub(r"\b(SSD|HDD|NVMe)\b", "", cap_str, flags=re.IGNORECASE)
    cap_str = (
        re.sub(r"[,;\s]+", " ", cap_str).strip().strip(",").strip("-").strip()
    )

  return tipo_str, cap_str


if "dataframes_rete" not in st.session_state:
  st.session_state.dataframes_rete = {}
  st.session_state.hardware_dettagli = {}

  for idx, item in enumerate(sedi_config):
    base_ip = item["blocco"].split(".")[0]
    range_ip = item["range_custom"]
    righe_ip = []
    for i in range_ip:
      ip_completo = f"{base_ip}.{i}"
      match_db = next(
          (
              row
              for row in dati_supabase
              if row.get("ip_completo") == ip_completo
          ),
          None,
      )
      if match_db:
        righe_ip.append({
            "Indirizzo IP": ip_completo,
            "_ip_completo": ip_completo,
            "Nome Macchina": pulisci_valore(match_db.get("nome_macchina", "")),
            "Tipologia": pulisci_valore(match_db.get("tipologia", "")),
            "Stato": pulisci_valore(match_db.get("stato", "🔴 Occupato")),
        })
        db_capienza = pulisci_valore(match_db.get("capienza_hd", ""))
        db_tipo_hd = pulisci_valore(match_db.get("tipo_hd", ""))
        tipo_hd_corretto, cap_hd_corretta = processa_stringa_hd(
            db_capienza, db_tipo_hd
        )
        st.session_state.hardware_dettagli[ip_completo] = {
            "Marca": pulisci_valore(match_db.get("marca", "")),
            "Modello": pulisci_valore(match_db.get("modello", "")),
            "S.O.": pulisci_valore(match_db.get("s_o", "")),
            "Processore": pulisci_valore(match_db.get("processore", "")),
            "RAM": pulisci_valore(match_db.get("ram", "")),
            "Tipo HD": tipo_hd_corretto,
            "Capienza HD": cap_hd_corretta,
            "Garanzia": pulisci_valore(match_db.get("garanzia", "")),
        }
      else:
        righe_ip.append({
            "Indirizzo IP": ip_completo,
            "_ip_completo": ip_completo,
            "Nome Macchina": "",
            "Tipologia": "",
            "Stato": "🟢 Libero",
        })
    st.session_state.dataframes_rete[idx] = pd.DataFrame(righe_ip)

idx_selezionato = st.selectbox(
    "📍 Seleziona la Sede da Gestire",
    options=range(len(sedi_config)),
    format_func=lambda i: (
        f"{sedi_config[i]['nome']} — Rete: {sedi_config[i]['blocco']} /"
        f" {sedi_config[i]['subnet']}"
    ),
)

sede_scelta = sedi_config[idx_selezionato]

tab_rete, tab_hardware = st.tabs(
    ["🌐 Blocco IP & Occupazione", "💻 Inventario Hardware Dettagliato"]
)

with tab_rete:
  st.markdown(f"### 🌐 Gestione IP: {sede_scelta['nome']}")
  df_corrente = st.session_state.dataframes_rete[idx_selezionato]

  totale_ip = len(df_corrente)
  occupati = len(
      df_corrente[df_corrente["Stato"].astype(str).str.contains("Occupato")]
  )
  liberi = totale_ip - occupati

  col_m1, col_m2, col_m3 = st.columns(3)
  col_m1.metric("Totale IP", totale_ip)
  col_m2.metric("🟢 Liberi", liberi)
  col_m3.metric("🔴 Occupati", occupati)

  st.markdown("---")

  df_per_editor = df_corrente.drop(columns=["_ip_completo"], errors="ignore").copy()
  opzioni_tipologia = ["PC / Macchina", "Stampante", "Switch"]
  df_per_editor = df_per_editor.fillna("")

  df_modificato = st.data_editor(
      df_per_editor,
      column_config={
          "Indirizzo IP": st.column_config.TextColumn(
              "Indirizzo IP", disabled=True
          ),
          "Nome Macchina": st.column_config.TextColumn("Nome Dispositivo"),
          "Tipologia": st.column_config.SelectboxColumn(
              "Tipologia", options=opzioni_tipologia, required=False
          ),
          "Stato": st.column_config.SelectboxColumn(
              "Stato", options=["🟢 Libero", "🔴 Occupato"], required=True
          ),
      },
      key=f"editor_sede_{idx_selezionato}",
      use_container_width=True,
      hide_index=True,
  )

  if st.button(
      "💾 Salva Modifiche Rete", key=f"btn_salva_rete_{idx_selezionato}"
  ):
    for i in range(len(df_modificato)):
      ip_corr = df_corrente.loc[i, "_ip_completo"]
      nome_mac = pulisci_valore(df_modificato.loc[i, "Nome Macchina"])
      tipo_scelto = pulisci_valore(df_modificato.loc[i, "Tipologia"])
      stato_attuale = df_modificato.loc[i, "Stato"]

      if nome_mac and stato_attuale != "🔴 Occupato":
        stato_attuale = "🔴 Occupato"
      elif not nome_mac and stato_attuale == "🔴 Occupato":
        stato_attuale = "🟢 Libero"
        tipo_scelto = ""
        if ip_corr in st.session_state.hardware_dettagli:
          del st.session_state.hardware_dettagli[ip_corr]
        elimina_da_supabase(ip_corr)

      df_corrente.loc[i, "Nome Macchina"] = nome_mac
      df_corrente.loc[i, "Tipologia"] = tipo_scelto
      df_corrente.loc[i, "Stato"] = stato_attuale

      if nome_mac:
        dettagli_esistenti = st.session_state.hardware_dettagli.get(
            ip_corr, {}
        )
        salva_o_aggiorna_su_supabase(
            ip_corr,
            sede_scelta["nome"],
            dettagli_esistenti,
            df_corrente.loc[i].to_dict(),
        )

    st.session_state.dataframes_rete[idx_selezionato] = df_corrente
    st.success("Modifiche di rete salvate con successo!")

with tab_hardware:
  st.markdown(f"### 💻 Specifiche Hardware: {sede_scelta['nome']}")
  df_rete_sede = st.session_state.dataframes_rete[idx_selezionato]

  with st.expander(
      "🛠️ Aggiungi dettagli tecnici avanzati (Manuale)", expanded=False
  ):
    lista_tutti_ip = df_rete_sede.to_dict("records")
    ip_disponibili_mostrati = [m["Indirizzo IP"] for m in lista_tutti_ip]

    if ip_disponibili_mostrati:
      scelta_mostrata = st.selectbox(
          "Seleziona IP Dispositivo",
          ip_disponibili_mostrati,
          key=f"selettore_ip_{idx_selezionato}",
      )
      ip_scelto = [
          m["_ip_completo"]
          for m in lista_tutti_ip
          if m["Indirizzo IP"] == scelta_mostrata
      ][0]
      riga_corrente_ip = [
          m for m in lista_tutti_ip if m["_ip_completo"] == ip_scelto
      ][0]
      dettagli_esistenti = st.session_state.hardware_dettagli.get(ip_scelto, {})

      with st.form(key=f"form_hw_{idx_selezionato}"):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
          hw_nome_macchina = st.text_input(
              "Nome Dispositivo",
              value=pulisci_valore(riga_corrente_ip.get("Nome Macchina", "")),
          )
        with col_f2:
          tipologia_esistente = pulisci_valore(
              riga_corrente_ip.get("Tipologia", "PC / Macchina")
          )
          if tipologia_esistente not in ["PC / Macchina", "Stampante", "Switch"]:
            tipologia_esistente = "PC / Macchina"
          hw_tipologia = st.selectbox(
              "Tipologia",
              ["PC / Macchina", "Stampante", "Switch"],
              index=["PC / Macchina", "Stampante", "Switch"].index(
                  tipologia_esistente
              ),
          )

        col1, col2 = st.columns(2)
        with col1:
          hw_marca = st.text_input(
              "Marca", value=pulisci_valore(dettagli_esistenti.get("Marca", ""))
          )
          hw_modello = st.text_input(
              "Modello",
              value=pulisci_valore(dettagli_esistenti.get("Modello", "")),
          )
          hw_so = st.text_input(
              "S.O.", value=pulisci_valore(dettagli_esistenti.get("S.O.", ""))
          )
          hw_cpu = st.text_input(
              "Processore e anno",
              value=pulisci_valore(dettagli_esistenti.get("Processore", "")),
          )
        with col2:
          ram_salvata = dettagli_esistenti.get("RAM", "16 GB")
          try:
            ram_val = int(str(ram_salvata).replace(" GB", "").strip())
          except:
            ram_val = 16
          hw_ram = st.number_input(
              "RAM (GB)", min_value=2, max_value=256, value=ram_val
          )

          tipo_hd_esistente = pulisci_valore(
              dettagli_esistenti.get("Tipo HD", "")
          )
          opzioni_hd = ["", "SSD", "HDD", "NVMe"]
          idx_hd = (
              opzioni_hd.index(tipo_hd_esistente)
              if tipo_hd_esistente in opzioni_hd
              else 0
          )
          hw_tipo_hd = st.selectbox("Tipo Memoria", opzioni_hd, index=idx_hd)

          hw_cap_hd = st.text_input(
              "Capienza / Note",
              value=pulisci_valore(dettagli_esistenti.get("Capienza HD", "")),
          )
          hw_garanzia = st.text_input(
              "Scadenza Garanzia",
              value=pulisci_valore(dettagli_esistenti.get("Garanzia", "")),
          )

        btn_salva = st.form_submit_button("Salva Specifiche Tecniche")
        if btn_salva:
          tipo_hd_fin, cap_hd_fin = processa_stringa_hd(hw_cap_hd, hw_tipo_hd)
          dettagli_nuovi = {
              "Marca": hw_marca,
              "Modello": hw_modello,
              "S.O.": hw_so,
              "Processore": hw_cpu,
              "RAM": f"{hw_ram} GB",
              "Tipo HD": tipo_hd_fin,
              "Capienza HD": cap_hd_fin,
              "Garanzia": hw_garanzia,
          }
          st.session_state.hardware_dettagli[ip_scelto] = dettagli_nuovi

          idx_r = df_rete_sede[df_rete_sede["_ip_completo"] == ip_scelto].index
          if not idx_r.empty:
            df_rete_sede.loc[idx_r, "Nome Macchina"] = pulisci_valore(
                hw_nome_macchina
            )
            df_rete_sede.loc[idx_r, "Tipologia"] = (
                hw_tipologia if pulisci_valore(hw_nome_macchina) else ""
            )
            df_rete_sede.loc[idx_r, "Stato"] = (
                "🔴 Occupato" if pulisci_valore(hw_nome_macchina) else "🟢 Libero"
            )
            st.session_state.dataframes_rete[idx_selezionato] = df_rete_sede

          riga_aggiornata = (
              df_rete_sede[df_rete_sede["_ip_completo"] == ip_scelto]
              .iloc[0]
              .to_dict()
          )
          salva_o_aggiorna_su_supabase(
              ip_scelto, sede_scelta["nome"], dettagli_nuovi, riga_aggiornata
          )
          st.success("Dati salvati correttamente!")

  st.markdown("---")
  st.markdown("📋 **Inventario Completo della Sede**")

  lista_completa = []
  for m in df_rete_sede.to_dict("records"):
    ip_comp = m["_ip_completo"]
    dettagli = st.session_state.hardware_dettagli.get(ip_comp, {})
    lista_completa.append({
        "Indirizzo IP": m["Indirizzo IP"],
        "_ip_completo": ip_comp,
        "Nome Macchina": pulisci_valore(m["Nome Macchina"]),
        "Tipologia": pulisci_valore(m["Tipologia"]),
        "Stato": m["Stato"],
        "Marca": pulisci_valore(dettagli.get("Marca", "")),
        "Modello": pulisci_valore(dettagli.get("Modello", "")),
        "S.O.": pulisci_valore(dettagli.get("S.O.", "")),
        "Processore e anno": pulisci_valore(dettagli.get("Processore", "")),
        "RAM": pulisci_valore(dettagli.get("RAM", "-")),
        "Tipo HD": pulisci_valore(dettagli.get("Tipo HD", "")),
        "Capienza HD": pulisci_valore(dettagli.get("Capienza HD", "")),
        "Garanzia": pulisci_valore(dettagli.get("Garanzia", "")),
    })

  df_inventario_corrente = pd.DataFrame(lista_completa)
  df_inv_per_editor = (
      df_inventario_corrente.drop(columns=["_ip_completo"], errors="ignore")
      .fillna("")
  )

  df_inventario_modificato = st.data_editor(
      df_inv_per_editor,
      column_config={
          "Indirizzo IP": st.column_config.TextColumn(
              "Indirizzo IP", disabled=True
          ),
          "Nome Macchina": st.column_config.TextColumn("Nome Dispositivo"),
          "Tipologia": st.column_config.SelectboxColumn(
              "Tipologia", options=opzioni_tipologia, required=False
          ),
          "Stato": st.column_config.SelectboxColumn(
              "Stato", options=["🟢 Libero", "🔴 Occupato"], required=True
          ),
          "Marca": st.column_config.TextColumn("Marca"),
          "Modello": st.column_config.TextColumn("Modello"),
          "S.O.": st.column_config.TextColumn("S.O."),
          "Processore e anno": st.column_config.TextColumn("Processore e anno"),
          "RAM": st.column_config.TextColumn("RAM"),
          "Tipo HD": st.column_config.SelectboxColumn(
              "Tipo HD", options=["", "SSD", "HDD", "NVMe"], required=False
          ),
          "Capienza HD": st.column_config.TextColumn("Capienza HD"),
          "Garanzia": st.column_config.TextColumn("Garanzia"),
      },
      key=f"editor_inventario_{idx_selezionato}",
      use_container_width=True,
      hide_index=True,
  )

  if st.button(
      "💾 Salva Modifiche Inventario", key=f"btn_salva_inv_{idx_selezionato}"
  ):
    for i in range(len(df_inventario_modificato)):
      ip_corr_riga = df_inventario_modificato.loc[i, "Indirizzo IP"]
      riga_orig = df_inventario_corrente[
          df_inventario_corrente["Indirizzo IP"] == ip_corr_riga
      ]
      if not riga_orig.empty:
        ip_comp = riga_orig.iloc[0]["_ip_completo"]
        nuovo_nome = pulisci_valore(
            df_inventario_modificato.loc[i, "Nome Macchina"]
        )
        nuova_tipologia = pulisci_valore(
            df_inventario_modificato.loc[i, "Tipologia"]
        )
        if not nuovo_nome:
          nuova_tipologia = ""

        cap_edit = pulisci_valore(
            df_inventario_modificato.loc[i, "Capienza HD"]
        )
        tipo_edit = pulisci_valore(df_inventario_modificato.loc[i, "Tipo HD"])
        tipo_finale_ed, cap_finale_ed = processa_stringa_hd(cap_edit, tipo_edit)

        dettagli_agg = {
            "Marca": pulisci_valore(df_inventario_modificato.loc[i, "Marca"]),
            "Modello": pulisci_valore(
                df_inventario_modificato.loc[i, "Modello"]
            ),
            "S.O.": pulisci_valore(df_inventario_modificato.loc[i, "S.O."]),
            "Processore": pulisci_valore(
                df_inventario_modificato.loc[i, "Processore e anno"]
            ),
            "RAM": pulisci_valore(df_inventario_modificato.loc[i, "RAM"]),
            "Tipo HD": tipo_finale_ed,
            "Capienza HD": cap_finale_ed,
            "Garanzia": pulisci_valore(
                df_inventario_modificato.loc[i, "Garanzia"]
            ),
        }
        st.session_state.hardware_dettagli[ip_comp] = dettagli_agg

        idx_r = df_rete_sede[df_rete_sede["_ip_completo"] == ip_comp].index
        if not idx_r.empty:
          df_rete_sede.loc[idx_r, "Nome Macchina"] = nuovo_nome
          df_rete_sede.loc[idx_r, "Tipologia"] = nuova_tipologia
          df_rete_sede.loc[idx_r, "Stato"] = (
              "🔴 Occupato" if nuovo_nome else "🟢 Libero"
          )
          riga_inf_att = df_rete_sede.loc[idx_r[0]].to_dict()
          salva_o_aggiorna_su_supabase(
              ip_comp, sede_scelta["nome"], dettagli_agg, riga_inf_att
          )

    st.session_state.dataframes_rete[idx_selezionato] = df_rete_sede
    st.success("Inventario aggiornato e salvato su Supabase!")

    st.session_state.dataframes_rete[idx_selezionato] = df_rete_sede
    st.success("Inventario aggiornato e salvato su Supabase!")
