import ipaddress
import streamlit as st

st.title("Gestione Rete Aziendale")


class GestioneReteAziendale:

  def __init__(self):
    if "sedi" not in st.session_state:
      st.session_state.sedi = {}
      st.session_state.dispositivi = {}
      self._configura_infrastruttura()

  def _configura_infrastruttura(self):
    st.session_state.sedi["Sede_Centrale"] = [
        ipaddress.ip_network("192.168.1.0/24"),
        ipaddress.ip_network("192.168.2.0/24"),
    ]
    for i in range(2, 8):
      st.session_state.sedi[f"Sede_{i}"] = [
          ipaddress.ip_network(f"192.168.{i+1}.0/24")
      ]

  def assegna_ip(self, nome_macchina, indirizzo_ip):
    try:
      ip = ipaddress.ip_address(indirizzo_ip)
    except ValueError:
      return f"Errore: '{indirizzo_ip}' non è un indirizzo IP valido."

    for sede, reti in st.session_state.sedi.items():
      for rete in reti:
        if ip in rete:
          if ip in (rete.network_address, rete.broadcast_address):
            return f"Errore: {ip} è un indirizzo di rete o broadcast."
          st.session_state.dispositivi[str(ip)] = {
              "nome": nome_macchina,
              "sede": sede,
              "subnet": str(rete),
          }
          return (
              f"Registrato: {nome_macchina} ({ip}) associato correttamente alla"
              f" {sede}."
          )
    return "Errore: Indirizzo IP non appartenente ad alcuna sede configurata."


rete = GestioneReteAziendale()

# Interfaccia utente web
nome_pc = st.text_input("Nome Dispositivo", "PC-Ufficio-01")
ip_pc = st.text_input("Indirizzo IP", "192.168.1.15")

if st.button("Registra IP"):
  risultato = rete.assegna_ip(nome_pc, ip_pc)
  if "Errore" in risultato:
    st.error(risultato)
  else:
    st.success(risultato)

st.subheader("Dispositivi Registrati")
if st.session_state.dispositivi:
  st.json(st.session_state.dispositivi)
else:
  st.info("Nessun dispositivo registrato.")
  
