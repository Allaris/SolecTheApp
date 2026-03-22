import customtkinter as ctk
import socket
import struct

from protocols import HANDSHAKE,PING,VERSION   # Importujemy protokoły z osobnego pliku

class MainFrame(ctk.CTkFrame):
    def __init__(self, parent, client_socket):
        super().__init__(parent)
        self.sock = client_socket

        self.label = ctk.CTkLabel(self, text="Panel Sterowania", font=("Arial", 20))
        self.label.pack(pady=20)

        self.ping_btn = ctk.CTkButton(
            self, text="Wyślij PING", 
            command=self.send_ping,
            fg_color="#E00808", 
            hover_color="#1C86EE"
        )
        self.ping_btn.pack(pady=20)

    def send_ping(self):
        try:
            self.sock.sendall(PING)
            response = self.sock.recv(12)
            print(f"Otrzymano: {response}")
        except Exception as e:
            print(f"Błąd komunikacji: {e}")