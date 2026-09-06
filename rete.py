import ipaddress


class GestioneReteAziendale:

  def __init__(self):
    self.sedi = {}
    self.dispositivi = {}
    self._configura_infrastruttura()

  def _configura_infrastruttura(self):
    # Sede centrale: gestisce 2 blocchi IP da 256 indirizzi ciascuno (/24 -> 0 a 255)
    self.sedi["Sede_Centrale"] = [
        ipaddress.ip_network("192.168.1.0/24"),
        ipaddress.ip_network("192.168.2.0/24"),
    ]

    # Le restanti 6 sedi: gestiscono 1 blocco IP ciascuna da 0 a 255
    for i in range(2, 8):
      self.sedi[f"Sede_{i}"] = [ipaddress.ip_network(f"192.168.{i+1}.0/24")]

  def assegna_ip(self, nome_macchina, indirizzo_ip):
    try:
      ip = ipaddress.ip_address(indirizzo_ip)
    except ValueError:
      return f"Errore: '{indirizzo_ip}' non è un indirizzo IP valido."

    # Verifica la corrispondenza con le reti delle sedi
    for sede, reti in self.sedi.items():
      for rete in reti:
        if ip in rete:
          if ip in (rete.network_address, rete.broadcast_address):
            return f"Errore: {ip} è un indirizzo di rete o broadcast."

          self.dispositivi[str(ip)] = {
              "nome": nome_macchina,
              "sede": sede,
              "subnet": str(rete),
          }
          return (
              f"Registrato: {nome_macchina} ({ip}) associato correttamente alla"
              f" {sede}."
          )

    return "Errore: Indirizzo IP non appartenente ad alcuna sede configurata."

  def report_rete(self):
    report = []
    for sede, reti in self.sedi.items():
      report.append(f"\n--- {sede.upper()} ---")
      for rete in reti:
        attivi = sum(
            1 for d in self.dispositivi.values() if d["subnet"] == str(rete)
        )
        report.append(
            f"  Subnet: {rete} | Dispositivi registrati: {attivi}/254"
        )
    return "\n".join(report)


# Esempio di utilizzo pratico
if __name__ == "__main__":
  rete = GestioneReteAziendale()

  # Test di registrazione macchine (>200 macchine distribuite)
  print(rete.assegna_ip("Server-Database-01", "192.168.1.10"))
  print(rete.assegna_ip("Server-Backup-02", "192.168.2.50"))  # Sempre Sede Centrale
  print(rete.assegna_ip("Workstation-Sede2-PC1", "192.168.4.15"))  # Sede 2
  print(rete.assegna_ip("Workstation-Sede7-PC1", "192.168.9.22"))  # Sede 7

  # Visualizzazione dello stato della rete
  print(rete.report_rete())
