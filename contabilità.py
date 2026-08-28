from decimal import Decimal
import streamlit as st
from supabase import create_client, Client

# Configurazione pagina Streamlit
st.set_page_config(
    page_title="Contabilità Scontrini Bancomat", page_icon="💳", layout="centered"
)

# Inizializzazione client Supabase da st.secrets
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_supabase()

def aggiungi_transazione(data, tipo, importo, esercente, categoria, scontrino_conservato):
    valore = float(Decimal(str(importo)).quantize(Decimal("0.01")))
    
    # Inserimento nella tabella 'transazioni' di Supabase
    response = supabase.table("transazioni").insert({
        "data": data,
        "tipo": tipo.upper(),
        "importo": valore,
        "esercente": esercente,
        "categoria": categoria,
        "scontrino_conservato": 1 if scontrino_conservato else 0
    }).execute()
    
    return response

def ottieni_transazioni():
    # Recupero dati da Supabase ordinati per data
    response = supabase.table("transazioni").select("*").order("data", desc=True).execute()
    return response.data

st.title("💳 Contabilità e Riconciliazione Scontrini (Supabase)")
st.markdown("Gestisci le tue transazioni con carta bancomat salvandole direttamente su Supabase.")

menu = st.sidebar.selectbox("Seleziona Sezione", ["Aggiungi Transazione", "Visualizza e Riconcilia"])

if menu == "Aggiungi Transazione":
    st.subheader("Registra Nuova Transazione")
    
    with st.form("form_transazione"):
        data = st.date_input("Data Transazione")
        tipo = st.selectbox("Tipo", ["Uscita", "Entrata"])
        importo = st.number_input("Importo (€)", min_value=0.01, format="%.2f", step=1.00)
        esercente = st.text_input("Esercente / Beneficiario")
        categoria = st.text_input("Categoria (es. Spesa, Ristorante, Stipendio)")
        
        scontrino = st.checkbox("Scontrino conservato?", value=True if tipo == "Uscita" else False)
        
        submit = st.form_submit_button("Salva Transazione")
        
        if submit:
            if esercente.strip() == "":
                st.warning("Inserisci il nome dell'esercente.")
            else:
                try:
                    aggiungi_transazione(
                        str(data),
                        tipo.upper(),
                        importo,
                        esercente,
                        categoria,
                        1 if scontrino else 0
                    )
                    st.success("Transazione salvata con successo su Supabase!")
                except Exception as e:
                    st.error(f"Errore durante il salvataggio su Supabase: {e}")

elif menu == "Visualizza e Riconcilia":
    st.subheader("Elenco Transazioni e Riconciliazione Mensile")
    
    try:
        transazioni = ottieni_transazioni()
    except Exception as e:
        st.error(f"Errore nel recupero dati da Supabase: {e}")
        transazioni = []
    
    if not transazioni:
        st.info("Nessuna transazione registrata.")
    else:
        anni_disponibili = sorted(list(set([t["data"][:4] for t in transazioni])), reverse=True)
        col1, col2 = st.columns(2)
        with col1:
            anno_sel = st.selectbox("Seleziona Anno", anni_disponibili)
        with col2:
            mese_sel = st.selectbox("Seleziona Mese", range(1, 13), format_func=lambda x: f"{x:02d}")
            
        prefisso_filtro = f"{anno_sel}-{mese_sel:02d}"
        
        totale_entrate = Decimal("0.00")
        totale_uscite = Decimal("0.00")
        mancanti = []
        dati_tabella = []
        
        for t in transazioni:
            data_t = t["data"]
            if data_t.startswith(prefisso_filtro):
                val = Decimal(str(t["importo"]))
                tipo_t = t["tipo"]
                esc_t = t["esercente"]
                cat_t = t["categoria"]
                scontrino_t = t["scontrino_conservato"]
                
                if tipo_t == "ENTRATA":
                    totale_entrate += val
                else:
                    totale_uscite += val
                    if scontrino_t == 0:
                        mancanti.append((esc_t, val, data_t))
                
                dati_tabella.append({
                    "Data": data_t,
                    "Tipo": tipo_t,
                    "Importo (€)": f"{val:.2f}",
                    "Esercente": esc_t,
                    "Categoria": cat_t,
                    "Scontrino": "Sì" if scontrino_t == 1 else "No"
                })
        
        st.markdown(f"### RIEPILOGO MESE: {prefisso_filtro}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Entrate", f"€ {totale_entrate:.2f}")
        m2.metric("Uscite", f"€ {totale_uscite:.2f}")
        m3.metric("Saldo Netto", f"€ {totale_entrate - totale_uscite:.2f}")
        
        if mancanti:
            st.warning(f"⚠️ Attenzione: Ci sono {len(mancanti)} uscite senza scontrino nel periodo selezionato!")
            for esc, imp, dt in mancanti:
                st.write(f"- **{dt}** | {esc}: **€ {imp:.2f}**")
        else:
            st.success("Tutte le uscite di questo mese hanno uno scontrino abbinato!")
            
        st.markdown("### Dettaglio Transazioni del Mese")
        if dati_tabella:
            st.dataframe(dati_tabella, use_container_width=True)
        else:
            st.info("Nessuna transazione per il mese selezionato.")
