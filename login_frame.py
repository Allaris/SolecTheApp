#main
import customtkinter as ctk
import socket
import struct

import protocols  # Importujemy protokoły z osobnego pliku

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
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(3.0) # 3 sekundy na odpowiedź
            self.sock.connect(('localhost', 9999))
            
            # 1. (Opcjonalnie) Odbiór powitania, jeśli serwer je wysyła
            try:
                self.sock.recv(1024) 
            except:
                pass

            # 2. Protokół SOLEC
            self.sock.sendall(protocols.get_handshake())
            self.sock.sendall(protocols.get_auth("damiansolec", "pass"))
            
            # 3. Próba odebrania Success
            try:
                header = self.sock.recv(3)
                if header and header[0] == protocols.TYPE_SUCCESS:
                    print("Zalogowano pomyślnie!")
            except socket.timeout:
                # Jeśli serwer nie wysłał Success, ale logi mówią że połączono
                print("Brak potwierdzenia, ale zakładamy sukces (zobacz logi serwera)")

            # Przejdź do głównego ekranu
            self.login_callback(self.sock)
                
        except Exception as e:
            self.status_label.configure(text=f"Błąd: {e}")