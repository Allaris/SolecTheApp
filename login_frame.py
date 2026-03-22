import customtkinter as ctk
import socket
import struct

from protocols import HANDSHAKE,PING,VERSION   # Importujemy protokoły z osobnego pliku

class LoginFrame(ctk.CTkFrame):
    def __init__(self, parent, login_callback):
        super().__init__(parent)
        self.login_callback = login_callback

        self.label = ctk.CTkLabel(self, text="Logowanie do serwera", font=("Arial", 20))
        self.label.pack(pady=20)

        self.connect_btn = ctk.CTkButton(
            self, text="Połącz i Handshake", 
            command=self.attempt_login,
            fg_color="#28a745"
        )
        self.connect_btn.pack(pady=10)

        self.status_label = ctk.CTkLabel(self, text="", text_color="gray")
        self.status_label.pack()

    def attempt_login(self):
        try:
            # Tworzenie połączenia
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(('localhost', 9999))
            
            # Handshake
            self.sock.sendall(HANDSHAKE)
            
            # Tutaj możesz dodać recv(), żeby sprawdzić czy serwer zaakceptował handshake
            
            self.status_label.configure(text="Połączono pomyślnie!", text_color="green")
            # Przekazujemy socket do głównej aplikacji
            self.after(1000, lambda: self.login_callback(self.sock))
            
        except Exception as e:
            self.status_label.configure(text=f"Błąd: {e}", text_color="red")
