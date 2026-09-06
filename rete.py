import ipaddress
import streamlit as st

st.subheader("Panoramica Sedi e Reti")

sedi_config = [
    {
        "nome": "Sede Centrale",
        "blocco": "192.168.1.0/23",
        "subnet_mask": "255.255.254.0",
    },
    {
        "nome": "Sede 2",
        "blocco": "192.168.3.0/24",
        "subnet_mask": "255.255.255.0",
    },
    {
        "nome": "Sede 3",
        "blocco": "192.168.4.0/24",
        "subnet_mask": "255.255.255.0",
    },
    {
        "nome": "Sede 4",
        "blocco": "192.168.5.0/24",
        "subnet_mask": "255.255.255.0",
    },
    {
        "nome": "Sede 5",
        "blocco": "192.168.6.0/24",
        "subnet_mask": "255.255.255.0",
    },
    {
        "nome": "Sede 6",
        "blocco": "192.168.7.0/24",
        "subnet_mask": "255.255.255.0",
    },
    {
        "nome": "Sede 7",
        "blocco": "192.168.8.0/24",
        "subnet_mask": "255.255.255.0",
    },
]

for item in sedi_config:
  nome_sede = item["nome"]
  blocco_cidr = item["blocco"]
  subnet_mask = item["subnet_mask"]

  label = f"📍 Sede: {nome_sede}  |  Rete: {blocco_cidr}  |  Subnet Mask: {subnet_mask}"

  with st.expander(label):
    rete = ipaddress.ip_network(blocco_cidr, strict=False)
    colonne_dati = []
    
    # Genera tutti gli indirizzi IP inclusi nella subnet specificata
    for ip in rete:
      colonne_dati.append(
          {"Indirizzo IP": str(ip), "Stato": "Disponibile / Libero"}
      )

    st.dataframe(colonne_dati, use_container_width=True)
