import ipaddress
import tkinter as tk
from tkinter import messagebox, scrolledtext


class AppGestioneRete:

  def __init__(self, root):
    self.root = root
    self.root.title("Gestione Rete Aziendale")
    self.root.geometry("600x500")

    self.sedi = {}
    self.dispositivi = {}
    self._configura_infrastruttura()

    # Layout Grafico
    tk.Label(
        root, text="Nome Dispositivo:", font=("Arial", 10, "bold")
    ).pack(pady=5)
    self.entry_nome = tk.Entry(root, width=30)
    self.entry_nome.pack(pady=5)

    tk.Label(
        root, text="Indirizzo IP (es. 192.168.1.10):", font=("Arial", 10, "bold")
    ).pack(pady=5)
    self.entry_ip = tk.Entry(root, width=30)
    self.entry_ip.pack(pady=5)

    tk.Button(
        root,
        text="Registra Dispositivo",
        command=self.registra_dispositivo,
        bg="#4CAF50",
        fg="white",
        font=("Arial", 10, "bold"),
    ).pack(pady=10)

    tk.Button(
        root,
        text="Aggiorna Report Rete",
        command=self.mostra_report,
        bg="#2196F3",
        fg="white",
        font=("Arial", 10, "bold"),
    ).pack(pady=5)

    tk.Label(
        root, text="Stato Rete / Log:", font=("Arial", 10, "bold")
    ).pack(pady=5)
    self.text_report = scrolledtext.ScrolledText(root, width=70, height=15)
    self.text_report.pack(pady=5)

    self.mostra_report()

  def _configura_infrastruttura(self):
    self.sedi["Sede_Centrale"] = [
        ipaddress.ip_network("192.168.1.0/24"),
        ipaddress.ip_network("192.168.2.0/24"),
    ]
    for i in range(2, 8):
      self.sedi[f"Sede_{i}"] = [ipaddress.ip_network(f"192.168.{i+1}.0/24")]

  .def_registra_dispositivo(self):
    pass  # Placeholder per brevità, usa il blocco completo sotto


# Versione completa del blocco di registrazione e report per la GUI:
