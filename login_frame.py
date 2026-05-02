#gałąź main
import customtkinter as ctk
import socket
import struct

import protocols  # Importujemy protokoły z osobnego pliku

class LoginFrame(ctk.CTkFrame):
    def __init__(self, parent, login_callback):
        super().__init__(parent)
        self.login_callback = login_callback

        # --- Interfejs Logowania ---
        self.label = ctk.CTkLabel(self, text="Logowanie do serwera", font=("Arial", 24))
        self.label.place(relx=0.5, rely=0.2, anchor="center")

        # --- Pole Login ---
        self.user_entry = ctk.CTkEntry(self, placeholder_text="Nazwa użytkownika", width=300, height=40, font=("Arial", 20))
        self.user_entry.place(relx=0.5, rely=0.3, anchor="center")

        # --- Pole Hasło ---
        self.pass_entry = ctk.CTkEntry(self, placeholder_text="Hasło", width=300, height=40, show="*", font=("Arial", 20))
        self.pass_entry.place(relx=0.5, rely=0.4, anchor="center")

        # --- Przycisk Logowania ---
        self.connect_btn = ctk.CTkButton(
            self, text="Zaloguj", width=200, height=40, font=("Arial", 20),
            command=self.attempt_login,
            fg_color="#28a745"
            
        )
        self.connect_btn.place(relx=0.5, rely=0.5, anchor="center")

        # --- Status Logowania ---
        self.status_label = ctk.CTkLabel(self, text="", text_color="gray")
        self.status_label.place(relx=0.5, rely=0.6, anchor="center")

    def attempt_login(self):
        # Pobieramy to, co użytkownik wpisał w okienka
        username = self.user_entry.get()
        password = self.pass_entry.get()

        # Prosta walidacja "na sucho"
        if not username or not password:
            self.status_label.configure(text="Wypełnij wszystkie pola!", text_color="orange")
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(1.0) # 3 sekundy na odpowiedź
            self.sock.connect(('localhost', 9999))
            
            # 1. (Opcjonalnie) Odbiór powitania, jeśli serwer je wysyła
            try:
                self.sock.recv(1024) 
            except:
                pass

            # 2. Protokół SOLEC
            self.sock.sendall(protocols.get_handshake())
            self.sock.sendall(protocols.get_auth(username, password))
            
            # 3. Próba odebrania Success
            try:
                header = self.sock.recv(3)

                if not header:
                    self.status_label.configure(text="Serwer rozłączył się", text_color="red")
                    return

                m_type, m_len = struct.unpack("!BH", header)
                
                # Udane logowanie
                if m_type == protocols.TYPE_SUCCESS:
                    print("Zalogowano pomyślnie!")
                    self.status_label.configure(text="Zalogowano!", text_color="green")
                    
                    username = self.user_entry.get()
                    # TYLKO TUTAJ PRZECHODZIMY DALEJ:
                    self.login_callback(self.sock, username)
                else:
                    # Serwer przysłał coś innego (np. TYPE_ERROR)
                    self.status_label.configure(text="Błędny login lub hasło", text_color="red")
                    self.sock.close()

            except socket.timeout:
                self.status_label.configure(text="Błąd: Serwer nie odpowiedział (Timeout)", text_color="orange")
                self.sock.close()

        except Exception as e:
            self.status_label.configure(text=f"Błąd połączenia: {e}", text_color="red")