#gałąź main
import customtkinter as ctk
import socket
import struct
import ssl
import protocols 

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
        #chwilowo na testy
        self.user_entry.insert(0, "damian")

        # --- Pole Hasło ---
        self.pass_entry = ctk.CTkEntry(self, placeholder_text="Hasło", width=300, height=40, show="*", font=("Arial", 20))
        self.pass_entry.place(relx=0.5, rely=0.4, anchor="center")
        #chwilowo na testy
        self.pass_entry.insert(0, "pgcBJ8qY78JM")

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
        # Pobranie, co użytkownik wpisał w okienka
        username = self.user_entry.get().strip()
        password = self.pass_entry.get()

        # Podstawowa walidacja, czy pola nie są puste
        if not username or not password:
            self.status_label.configure(text="Wypełnij wszystkie pola!", text_color="orange")
            return

        try:
            # Konfiguracja kontekstu TLS (Szyfrowanie)
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE  # Ignorownie certyfikatow self-signed

            # Tworzenie surowego socketu TCP
            raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_socket.settimeout(5.0) # timeout na czas negocjacji TLS 

            # OPAKOWANIE W TLS przed fizycznym połączeniem
            self.sock = context.wrap_socket(raw_socket, server_hostname=protocols.SERVER_DOMAIN)
            
            print(f"Rozpoczynanie bezpiecznego połączenia TLS z {protocols.SERVER_DOMAIN}...")
            self.sock.connect((protocols.SERVER_DOMAIN, 9999))
            print("[TLS] Połączenie zaszyfrowane pomyślnie!")
            
            # timeout na oczekiwanie na odpowiedź serwera po zalogowaniu 
            self.sock.settimeout(3.0) 

            # Powitanie , niby go nie ma so far
            try:
                self.sock.recv(1024) 
            except:
                pass

            # Protokół SOLEC 
            self.sock.sendall(protocols.get_handshake())
            self.sock.sendall(protocols.get_auth(f"{username}@{protocols.SERVER_DOMAIN}", password))     

            # Próba odebrania Success
            try:
                header = self.sock.recv(3)

                if not header:
                    self.status_label.configure(text="Serwer rozłączył się", text_color="red")
                    return

                m_type, m_len = struct.unpack("!BH", header)
                
                # Udane logowanie
                if m_type == protocols.TYPE_SUCCESS:
                    print("Zalogowano pomyślnie przez TLS!")
                    self.status_label.configure(text="Zalogowano!", text_color="green")
                    
                    username = self.user_entry.get().strip()
                    # Przekazanie socketu TLS dalej do aplikacji
                    self.login_callback(self.sock, username)
                else:
                    # Nieudane logowanie
                    self.status_label.configure(text="Błędny login lub hasło", text_color="red")
                    self.sock.close()

            except socket.timeout:
                self.status_label.configure(text="Błąd: Serwer nie odpowiedział (Timeout)", text_color="orange")
                self.sock.close()

        except Exception as e:
            self.status_label.configure(text=f"Błąd połączenia TLS: {e}", text_color="red")
            print(f"Szczegóły błędu TLS: {e}")