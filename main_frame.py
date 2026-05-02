#gałąź testowa
import customtkinter as ctk
import protocols
import threading
import struct

class MainFrame(ctk.CTkFrame):
    def __init__(self, parent, client_socket, username):
        super().__init__(parent)

        # socket i nazwę użytkownika
        self.client_socket = client_socket
        self.my_username = username

        # Zmienna przechowująca aktualnego adresata
        self.current_recipient = "user1@localhost" 
        self.channel_buttons = [] # Lista na przyciski, by zmieniać ich kolory

        # --- Konfiguracja siatki wewnątrz MainFrame ---
        # Kolumna 0 (czat) będzie się rozszerzać (weight=1)
        # Kolumna 1 (kanały) będzie miała stałą szerokość
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0) 
        self.grid_rowconfigure(0, weight=1) # Wiersz czatu rośnie
        self.grid_rowconfigure(1, weight=0) # Wiersz wpisywania ma stałą wysokość

        # --- 1. LEWA STRONA: KONTENER CZATU ---
        # Tworzymy osobną ramkę na czat i pole wpisywania, żeby łatwiej nimi zarządzać
        self.chat_container = ctk.CTkFrame(self, fg_color="transparent")
        self.chat_container.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=10, pady=10)
        self.chat_container.grid_columnconfigure(0, weight=1)
        self.chat_container.grid_rowconfigure(0, weight=1)

        # Pole czatu (na górze kontenera)
        self.chat_display = ctk.CTkTextbox(self.chat_container, font=("Arial", 20))
        self.chat_display.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        self.chat_display.configure(state="disabled")

        # Pole wpisywania wiadomości (na dole kontenera)
        self.msg_entry = ctk.CTkEntry(self.chat_container, placeholder_text="Wpisz wiadomość...", height=40, font=("Arial", 20) )
        self.msg_entry.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        self.msg_entry.bind("<Return>", lambda e: self.send_message())

        # Przycisk wysyłania (obok pola wpisywania)
        self.send_btn = ctk.CTkButton(self.chat_container, text="Wyślij", width=100, height=40, font=("Arial", 20), command=self.send_message)
        self.send_btn.grid(row=1, column=1, sticky="e")

        # --- 2. PRAWA STRONA: KANAŁY ---
        # Kanały
        self.channels_frame = ctk.CTkFrame(self, width=200)
        self.channels_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=10, pady=10)

        # Tytuł sekcji kanałów
        self.channels_label = ctk.CTkLabel(self.channels_frame, text="Solec kanały", font=("Arial", 18, "bold"))
        self.channels_label.pack(pady=10)

        # 3 przyciski użytkowników
        users = ["user1", "user2", "user3"]
        for user in users:
            btn = ctk.CTkButton(
                self.channels_frame, 
                text=user, 
                command=lambda u=user: self.select_user(u),
                fg_color="#3b3b3b",  # Domyślny jasny szary
                hover_color="#4b4b4b"
            )
            btn.pack(pady=5, padx=10, fill="x")
            self.channel_buttons.append((user, btn))

        # Domyślnie zaznaczamy pierwszego użytkownika
        self.select_user("user1")

        # TYLKO JEDEN WĄTEK!
        self.listen_thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.listen_thread.start()

    # Funkcja do odbierania dokładnie n bajtów (rozwiązuje problem przerywania)
    def receive_exact(self, n):
        """Pobiera dokładnie n bajtów - rozwiązuje problem przerywania"""
        data = b''
        while len(data) < n:
            chunk = self.client_socket.recv(n - len(data))
            if not chunk: return None
            data += chunk
        return data

    # Funkcja do wysyłania wiadomości (wywoływana po naciśnięciu Enter lub kliknięciu przycisku)
    def send_message(self):
        content = self.msg_entry.get()
        
        # Sprawdzamy czy wiadomość nie jest pusta
        if not content:
            return

        try:
            # 1. Pobieramy dynamiczny cel ze zmiennej, którą ustawiają przyciski
            target = self.current_recipient  
            
            # 2. Tworzymy pakiet zgodnie z Twoim protokołem
            packet = protocols.get_message_packet(self.my_username, target, content)
            
            # 3. Wysyłamy przez socket
            self.client_socket.sendall(packet)

            # 4. Wyświetlamy wiadomość w oknie czatu (z formatem "Ja -> user2: Treść")
            my_text = f"{self.my_username} -> {target}: {content}"
            self.display_text(my_text)
            
            # 5. Czyścimy pole wpisywania
            self.msg_entry.delete(0, 'end')
            
        except Exception as e:
            print(f"Błąd wysyłania: {e}")

            #     self.msg_entry.delete(0, 'end')
            # except Exception as e:
            #     print(f"Błąd wysyłania: {e}")

    # Wątek odbierający wiadomości z serwera
    def receive_loop(self):
        print("Wątek odbioru: AKTYWNY")
        while True:
            try:
                # Odbieramy nagłówek (3 bajty)
                header = self.receive_exact(3)
                if not header: 
                    print("Serwer zamknął połączenie.")
                    break
                
                m_type, m_len = struct.unpack("!BH", header)
                
                # Odbieramy treść (dokładnie m_len bajtów)
                payload = self.receive_exact(m_len)
                if payload is None: break
                
                if m_type == protocols.TYPE_MESSAGE:
                    data = protocols.parse_message(payload)
                    if data:
                        sender = data['source']
                        # Jeśli to my, napisz "Ty", jeśli ktoś inny - nick  chyba juz do usuniecia
                        display_name = self.my_username if sender == self.my_username else sender
                        text = f"{display_name}: {data['content']}"
                        
                        # Przekazujemy tekst do GUI (lambda m=text zamraża treść)
                        self.after(0, lambda m=text: self.display_text(m))
                        print(f"Odebrano: {text}")

            except Exception as e:
                # print(f"Błąd pętli: {e}")
                continue

    # Funkcja do aktualizacji pola czatu (wywoływana z wątku odbioru)              
    def display_text(self, text):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", text + "\n")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    # Funkcja do obsługi wyboru użytkownika z listy kanałów
    def select_user(self, username):
        # 1. Aktualizujemy zmienną adresata (zgodnie z Twoim formatem)
        self.current_recipient = f"{username}@localhost"
        print(f"Aktualny adresat: {self.current_recipient}")

        # 2. Aktualizujemy kolory przycisków
        for name, btn in self.channel_buttons:
            if name == username:
                # Kolor dla wybranego (ciemniejszy/wyróżniony)
                btn.configure(fg_color="#1a1a1a", border_width=2, border_color="#28a745")
            else:
                # Powrót do domyślnego dla reszty
                btn.configure(fg_color="#3b3b3b", border_width=0)