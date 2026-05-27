#gałąź testowa
import customtkinter as ctk
import protocols
import threading
import struct
import os
import time

from datetime import datetime

class MainFrame(ctk.CTkFrame):
    def __init__(self, parent, client_socket, username):
        super().__init__(parent)
        self.client_socket = client_socket

        # Pełny JID zalogowanego użytkownika 
        username_clean = username.strip()
        if "@" not in username_clean:
            self.my_username = f"{username_clean}@{protocols.SERVER_DOMAIN}"
        else:
            self.my_username = username_clean
            
        print(f"--- [DEBUG START] Zalogowany jako pełny JID: {self.my_username} ---")

        self.current_recipient = "" 
        self.channel_buttons_refs = [] # Referencje do przycisków kanałów i użytkowników (adres, przycisk)

        # --- Konfiguracja siatki głównej (ułożenie)------------------------------

        # Kolumna 0: Panel boczny (stały, po lewej), Kolumna 1: Czat (rozszerzalny, po prawej)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1) 
        self.grid_rowconfigure(0, weight=1)

        # LEWA STRONA: PANEL BOCZNY (Sidebar) ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
        self.sidebar = ctk.CTkFrame(self, width=250)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Nagłówek panelu bocznego
        self.channels_label = ctk.CTkLabel(self.sidebar, text="KANAŁY I USERZY", font=("Arial", 16, "bold"))
        self.channels_label.pack(pady=10)

        # Przewijana lista przycisków
        self.scroll_list = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.scroll_list.pack(fill="both", expand=True, padx=5, pady=5)

        # Przycisk "+" na dole sidebaru do dodawania kanałów lub użytkowników
        self.add_channel_btn = ctk.CTkButton(self.sidebar, text="+ Dodaj Rozmówcę/Kanał", fg_color="#28a745", hover_color="#218838", command=self.ask_for_target)
        self.add_channel_btn.pack(pady=5, padx=10, fill="x")

        # Profil użytkownika na dole sidebaru
        self.profile_frame = ctk.CTkFrame(self.sidebar, fg_color="#2b2b2b", height=40, corner_radius=6)
        self.profile_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        self.profile_frame.pack_propagate(False) # Blokuje zmianę wymiarów ramki

        # Czystki login bez domeny do wyświetlenia w profilu
        my_clean_nick = self.my_username.split('@')[0].strip()

        # Etykieta wyświetlająca informację o zalogowanym userze
        self.user_label = ctk.CTkLabel(
            self.profile_frame, 
            text=f"👤 Zalogowany: {my_clean_nick}", 
            font=("Arial", 12, "bold"), 
            anchor="w", 
            text_color="#28a745" # Zielony kolor tekstu dla ładnego wyglądu
        )
        self.user_label.pack(side="left", padx=10, fill="both", expand=True)
        


        # PRAWA STRONA: CZAT ------------------------------------------------------------------------------------------------------------------------------------------------------------------
        
        # Kontener na okno czatu i pole wpisywania wiadomości
        self.chat_container = ctk.CTkFrame(self, fg_color="transparent")
        self.chat_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.chat_container.grid_columnconfigure(0, weight=1)
        self.chat_container.grid_rowconfigure(0, weight=1)

        # Okno czatu (tylko do odczytu, wpisywanie poniżej)
        self.chat_display = ctk.CTkTextbox(self.chat_container, font=("Arial", 20))
        self.chat_display.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        self.chat_display.configure(state="disabled")

        # Pole wpisywania wiadomości 
        self.msg_entry = ctk.CTkEntry(self.chat_container, placeholder_text="Wpisz wiadomość...", height=40, font=("Arial", 20))
        self.msg_entry.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        self.msg_entry.bind("<Return>", lambda e: self.send_message())

        # Przycisk wysyłania wiadomości
        self.send_btn = ctk.CTkButton(self.chat_container, text="Wyślij", width=100, height=40, font=("Arial", 20), command=self.send_message)
        self.send_btn.grid(row=1, column=1, sticky="e")



        # LOGIKA POŁĄCZENIA I PROTOKOŁÓW ------------------------------------------------------------------------------------------------------------------------------------------------------------------

        domain = protocols.SERVER_DOMAIN

        # Wyciąganie czystego loginu aktualnie zalogowanego użytkownika (np. "damian")
        my_clean_username = self.my_username.split('@')[0].strip().lower()

        # Inicjalizacja nowej listy kanałów i użytkowników ---
        # Dodawanie kanału #tel na samą górę listy
        self.add_item_to_list(f"#tel@{domain}", is_channel=True)

        # Pełna lista użytkowników (może kiedys da nam mozliwosc pobrania userow :I )
        all_test_users = ["damian", "kacper", "kuba", "bt", "d2"]
        
        # Dodawanie użytkowników do listy (z pominięciem siebie samego)
        for user in all_test_users:
            if user.lower() != my_clean_username:
                self.add_item_to_list(f"{user}@{domain}", is_channel=False)

        # Wybór domyślny ustawiamy na pierwszy kanał z góry (#tel)
        self.select_target(f"#tel@{domain}")

        # Start wątku odbierania
        self.listen_thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.listen_thread.start()

    # Funkcja dodająca kanał lub użytkownika do listy po lewej stronie. Tworzy przycisk z nazwą i "X" do usuwania.
    def add_item_to_list(self, address, is_channel=False):
        clean_address = address.strip().lower()
        
        # Wyswietla krotka nazwe: #tel lub damian
        if clean_address.startswith('#'):
            display_name = clean_address.split('@')[0]
        else:
            display_name = clean_address.split('@')[0]
        
        # Tworzy ramkę-kontener dla przycisku i "X"
        item_frame = ctk.CTkFrame(self.scroll_list, fg_color="transparent")
        item_frame.pack(pady=2, padx=5, fill="x")

        # Główny przycisk (z nazwą)
        btn = ctk.CTkButton(
            item_frame, 
            text=display_name,
            anchor="w",
            command=lambda: self.select_target(clean_address),
            fg_color="#3b3b3b",
            height=32
        )
        btn.pack(side="left", fill="x", expand=True, padx=(0, 2))
        
        # Przycisk "X" do usuwania
        delete_btn = ctk.CTkButton(
            item_frame,
            text="X",
            width=30,
            height=32,
            fg_color="#c82333", # Czerwony
            hover_color="#a71d2a",
            command=lambda: self.leave_channel(clean_address, item_frame)
        )
        delete_btn.pack(side="right")
        
        # Zapisuje referencję do głównego przycisku (do zmiany kolorów w select_target)
        self.channel_buttons_refs.append((clean_address, btn))

    # Funkcja wyświetlająca dialog do wpisania nazwy kanału lub użytkownika, a następnie dodająca go do listy i wysyłająca odpowiedni pakiet do serwera (JOIN dla kanału, brak protokołu dla użytkownika)
    def ask_for_target(self):
        dialog = ctk.CTkInputDialog(text="Wpisz nazwę użytkownika (np. damian) lub kanału (np. #tem):", title="Dodaj")
        input_val = dialog.get_input()
        
        # Podstawowa walidacja, czy coś zostało wpisane
        if input_val:
            input_val = input_val.strip()
            domain = protocols.SERVER_DOMAIN
            
            # Jeśli zaczyna się od '#', traktujemy to jako kanał, w przeciwnym razie jako użytkownika. W obu przypadkach dodajemy domenę, jeśli jej nie ma.
            if input_val.startswith('#'):
                # LOGIKA KANAŁU 
                clean_name = input_val.lstrip('#').split('@')[0]
                full_address = f"#{clean_name}@{domain}"
                self.join_channel(full_address) 
            else:
                # LOGIKA UŻYTKOWNIKA
                clean_name = input_val.split('@')[0]
                full_address = f"{clean_name}@{domain}"
                
                # Dodajemy do listy i zaznaczamy
                self.add_item_to_list(full_address, is_channel=False)
                self.select_target(full_address)

    # Protokół dołączania do kanału
    def join_channel(self, address): 
        packet = protocols.get_join_channel(self.my_username, address)
        try:
            self.client_socket.sendall(packet)
            self.add_item_to_list(address, is_channel=True)
            self.select_target(address)
            print(f"DEBUG: Wysłano prośbę JOIN dla {address}")
        except Exception as e:
            print(f"Błąd JOIN: {e}")

    # Protokół opuszczania kanału i usuwania z listy
    def leave_channel(self, full_address, btn_frame):
        # Protokół sieciowy (tylko dla kanałów)
        if full_address.startswith('#'):
            packet = protocols.get_leave_channel(self.my_username, full_address)
            try:
                self.client_socket.sendall(packet)
            except Exception as e:
                print(f"Błąd sieci: {e}")

        # Usuwanie z listy referencji
        self.channel_buttons_refs = [(addr, btn) for addr, btn in self.channel_buttons_refs if addr != full_address]

        # Usuwanie z GUI
        btn_frame.destroy()
        
        # Jeśli aktualnie oglądany czat to ten, który właśnie usunęliśmy, to czyścimy okno czatu i resetujemy current_recipient
        if self.current_recipient == full_address:
            self.current_recipient = ""
            self.chat_display.configure(state="normal")
            self.chat_display.delete("1.0", "end")
            self.chat_display.insert("end", "Wybierz rozmówcę...")
            self.chat_display.configure(state="disabled")

    # Funkcja wyboru aktywnego okna czatu (kanał lub użytkownik) i synchronizacji historii
    def select_target(self, address):
        if self.current_recipient == address: return
        self.current_recipient = address

        # Wizualne zaznaczenie przycisku na liście bocznej
        for addr, btn in self.channel_buttons_refs:
            if addr == address:
                btn.configure(fg_color="#28a745")
            else:
                btn.configure(fg_color="#3b3b3b")

        # Pobiera czas ostatniej wiadomości z lokalnego pliku, żeby nie ciągnąć wszystkiego od zera
        since_time = self.get_last_timestamp_from_file(address)

        # AUTOMATYCZNY JOIN (Tylko dla kanałów z #)
        if address.startswith('#'):
            try:
                print(f"DEBUG SYNC: Wysyłam automatyczny JOIN dla kanału {address}")
                join_packet = protocols.get_join_channel(self.my_username, address)
                self.client_socket.sendall(join_packet)
                
                # Prośba o historię kanału
                print(f"DEBUG SYNC: Proszę o historię kanału {address} od timestampu: {since_time}")
                packet = protocols.get_history_packet(address, since_timestamp=since_time, count=100, offset=0)
                self.client_socket.sendall(packet)
            except Exception as e:
                print(f"Błąd auto-join lub historii kanału: {e}")

        # SYNCHRONIZACJA DLA UŻYTKOWNIKÓW (Rozmowy prywatne)
        else:
            try:
                print(f"DEBUG SYNC: Proszę o historię rozmowy prywatnej z {address} od timestampu: {since_time}")
                # Wysyłamy prośbę o historię z danym użytkownikiem (address to np. kacper@rctt.net)
                packet = protocols.get_history_packet(address, since_timestamp=since_time, count=100, offset=0)
                self.client_socket.sendall(packet)
            except Exception as e:
                print(f"Błąd wysyłania prośby o historię użytkownika: {e}")

        # Odświeżenie okna czatu z lokalnego pliku (wciąga to co już mamy, resztę dociągnie receive_loop)
        self.load_history(address)

    # Funkcja generująca unikalną nazwę pliku historii dla danego adresu (kanał lub użytkownik) w formacie: history_serwer_ktoZalogowany_doKogoLubJakiKanal.txt
    def get_history_filename(self, address):
        domain = protocols.SERVER_DOMAIN.strip().lower()
        
        # Wyciąga czysty login zalogowanego użytkownika (ja)
        me = self.my_username.split('@')[0].strip().lower()
        
        # Wyciąga czysty identyfikator celu (kanał np. #tel lub user np. kacper)
        target = address.split('@')[0].strip().lower()

        # Generuje spójny format dla wszystkiego: serwer_ja_cel
        safe_name = f"history_{domain}_{me}_{target}"
            
        # Zastępuje kropki w nazwie domeny na podkreślenia (rctt.net -> rctt_net)
        safe_name = safe_name.replace('.', '_')
        
        return f"{safe_name}.txt"

    # Funkcja odczytująca ostatni timestamp z lokalnego pliku historii, żeby wiedzieć od kiedy prosić o wiadomości z serwera (jeśli plik nie istnieje, zwraca 0)
    def load_history(self, address):
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        
        # Pobiera nazwę pliku wygenerowaną według formatu
        filename = self.get_history_filename(address)
        print(f"DEBUG HISTORIA: Próbuję wczytać plik: {filename}")

        # Sprawdza, czy plik istnieje, i jeśli tak, to wczytuje jego zawartość do okna czatu. Jeśli plik nie istnieje, to znaczy, że to nowa rozmowa i po prostu zostawia okno puste.
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    content = f.read()
                    self.chat_display.insert("1.0", content)
            except Exception as e:
                print(f"Błąd czytania pliku historii: {e}")
        else:
            print(f"DEBUG HISTORIA: Plik {filename} jeszcze nie istnieje (nowa rozmowa).")
        
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    # Funkcja pobierająca ostatni timestamp z lokalnego pliku historii, żeby wiedzieć od kiedy prosić o wiadomości z serwera (jeśli plik nie istnieje, zwraca 0)
    def send_message(self):
        content = self.msg_entry.get().strip()
        if not content:
            return

        try:
            # WYŚWIETLA I ZAPISUJE LOKALNIE OD RAZU 
            # ZAPIS Z DATĄ I MILISEKUNDAMI ---
            now = datetime.now()
            base_time = now.strftime('%Y-%m-%d %H:%M:%S')
            ms_str = now.strftime('%f')[:3]  # Pierwsze 3 cyfry milisekund
            time_str = f"{base_time}.{ms_str}"
            
            my_clean_nick = self.my_username.split('@')[0].strip().lower()
            formatted_msg = f"[{time_str}] {my_clean_nick}: {content}"
            
            # Pobiera plik historii dla AKTUALNEGO okna
            filename = self.get_history_filename(self.current_recipient)
            
            # Zapisuje od razu na dysk
            try:
                with open(filename, "a", encoding="utf-8") as f:
                    f.write(formatted_msg + "\n")
            except Exception as e:
                print(f"Błąd natychmiastowego zapisu: {e}")

            # Wpycha tekst na ekran na żywo
            self.chat_display.configure(state="normal")
            self.chat_display.insert("end", formatted_msg + "\n")
            self.chat_display.configure(state="disabled")
            self.chat_display.see("end")

            # DALSZA LOGIKA: WYSYŁKA DO SERWERA
            packet = protocols.get_message_packet(self.my_username, self.current_recipient, content)
            self.client_socket.sendall(packet)
            
            # Czyści pole wpisywania
            self.msg_entry.delete(0, "end")
            
        except Exception as e:
            print(f"Błąd podczas wysyłania wiadomości: {e}")
    
    # Funkcja wyświetlająca wiadomość w oknie czatu i zapisująca ją do lokalnego pliku historii. Wyświetla tylko, jeśli wiadomość jest dla aktualnie otwartego rozmówcy, ale zapisuje do pliku zawsze (żeby mieć pełną historię).
    def display_text(self, text, target):
        filename = self.get_history_filename(target)
        
        # Zapisuje wiadomość do lokalnego pliku historii (tworzy plik jeśli nie istnieje, dopisuje jeśli istnieje). Każda wiadomość jest zapisywana w formacie: [HH:MM:SS.mmm] nadawca: treść
        try:
            with open(filename, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception as e: 
            print(f"DEBUG BŁĄD ZAPISU HISTORII: {e}")

        # Wyświetl tylko jeśli okno pasuje
        inc_id = target.split('@')[0].strip().lower()
        curr_id = self.current_recipient.split('@')[0].strip().lower()
        
        # Jeśli wiadomość jest dla aktualnie otwartego rozmówcy, to wyświetla ją od razu w oknie czatu. Jeśli nie, to tylko zapisuje do pliku, ale nie wyświetla (żeby nie mieszać okna czatu, które jest otwarte na innym rozmówcy). Dzięki temu mamy pełną historię w plikach, ale okno czatu pokazuje tylko aktualne rozmowy.
        if inc_id == curr_id:
            self.chat_display.configure(state="normal")
            self.chat_display.insert("end", text + "\n")
            self.chat_display.configure(state="disabled")
            self.chat_display.see("end")
        else:
            print(f"DEBUG UI: Wiadomość dla {inc_id} zapisała się w pliku {filename}. Masz otwarte: {curr_id}")

    # Funkcja do odbierania dokładnie n bajtów z socketu. Zwraca None jeśli połączenie zostało zamknięte lub wystąpił błąd.
    def receive_exact(self, n):
        data = b''
        try:
            self.client_socket.settimeout(None) 
            while len(data) < n:
                chunk = self.client_socket.recv(n - len(data))
                if not chunk:
                    return None 
                data += chunk
            return data
        except Exception as e:
            print(f"--- [DEBUG] Błąd recv: {e} ---")
            return None
    
    # Główny loop odbierający wiadomości z serwera. Odczytuje nagłówek (3 bajty), potem dokładnie tyle bajtów ile mówi nagłówek, i w zależności od typu wiadomości (TYPE_MESSAGE, TYPE_ERROR, TYPE_HISTORY) odpowiednio je przetwarza. Błędy serwera (TYPE_ERROR) są logowane do konsoli programisty, ale nie wyświetlane w oknie czatu (żeby nie mieszać interfejsu). Wiadomości (TYPE_MESSAGE) są wyświetlane tylko jeśli są dla aktualnie otwartego rozmówcy, ale zawsze zapisywane do pliku historii.
    def receive_loop(self):
        while True:
            header = self.receive_exact(3)
            if not header: break
            
            m_type, m_len = struct.unpack("!BH", header)
            payload = self.receive_exact(m_len)
            
            # Obsługa błędów serwera (TYPE_ERROR) ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            if m_type == protocols.TYPE_ERROR:
                if payload and len(payload) >= 2:
                    try:
                        err_msg, _ = protocols.decode_string(payload, 0)
                    except Exception:
                        err_msg = f"Nieznany kod błędu (Surowe bajty: {payload.hex()})"
                elif payload:
                    err_msg = f"Kod błędu: {payload[0]} (0x{payload.hex()})"
                else:
                    err_msg = "Pusty błąd serwera (Brak autoryzacji)"
                
                # błąd TYLKO do konsoli 
                print(f"!!! SERWER ZGŁOSIŁ BŁĄD: {err_msg} | Aktywne okno: {self.current_recipient} | Mój JID: {self.my_username}")
                
                # formatted_err = f"⚠️ [BŁĄD AUTORYZACJI]: {err_msg}"
                # self.after(0, lambda t=formatted_err: self.display_text(t, self.current_recipient))
                continue 
            
            # Obsługa wiadomości (TYPE_MESSAGE) ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            elif m_type == protocols.TYPE_MESSAGE:
                data = protocols.parse_message(payload)
                
                if data:
                    s_clean = data['source'].split('@')[0].strip().lower()
                    t_clean = data['target'].split('@')[0].strip().lower()
                    my_nick = self.my_username.split('@')[0].strip().lower()
                    curr_id = self.current_recipient.split('@')[0].strip().lower()
                    
                    # Jak # to kanał, jak nie to prywatna rozmowa
                    if t_clean.startswith('#'):
                        chat_id = t_clean
                    else:
                        if s_clean == my_nick:
                            chat_id = t_clean
                        else:
                            chat_id = s_clean

                    # Formatowanie wiadomości z timestampem i nadawcą. Timestamp jest konwertowany na czytelny format HH:MM:SS.mmm
                    now = datetime.now()
                    base_time = datetime.fromtimestamp(data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Dla spójności formatu  .000 (lub now.strftime('%f')[:3] dla aktualnego czasu)
                    time_str = f"{base_time}.000"
                    
                    msg_signature = f"{s_clean}: {data['content']}"
                    formatted_msg = f"[{time_str}] {msg_signature}"
                    
                    # Plik historii dla tego czatu (kanał lub użytkownik)
                    filename = self.get_history_filename(chat_id)
                    
                    # Sprawdza, czy okno, do którego przyszła wiadomość, jest aktualnie otwarte
                    is_current_chat_open = (chat_id == curr_id)

                    # WARUNEK 1: OKNO CZATU JEST OTWARTE - wiadomość jest dla aktualnie oglądanego rozmówcy, więc wyświetla ją od razu i zapisuje do pliku
                    if is_current_chat_open:
                        # Zapisuje do pliku bez zbędnego sprawdzania (czat na żywo)
                        try:
                            with open(filename, "a", encoding="utf-8") as f:
                                f.write(formatted_msg + "\n")
                        except Exception as e:
                            print(f"Błąd zapisu wiadomości na żywo: {e}")

                        # Płynnie wpychamy JEDNĄ linijkę na koniec ekranu czatu (bez przeładowywania load_history)
                        self.after(0, lambda t=formatted_msg: self.chat_display.configure(state="normal") or 
                                                             self.chat_display.insert("end", t + "\n") or 
                                                             self.chat_display.configure(state="disabled") or 
                                                             self.chat_display.see("end"))

                    
                    # WARUNEK 2: WIADOMOŚĆ W TLE / SYNCHRONIZACJA HISTORII PO LOGOWANIU
                    else:
                        # Okno jest zamknięte, więc paczka może pochodzić z historii serwera.
                        # Tutaj rygorystycznie pilnujemy duplikatów.
                        try:
                            with open(filename, "r", encoding="utf-8") as f:
                                already_in_file = formatted_msg in f.read()
                        except Exception:
                            already_in_file = False

                        if not already_in_file:
                            try:
                                with open(filename, "a", encoding="utf-8") as f:
                                    f.write(formatted_msg + "\n")
                            except Exception as e:
                                print(f"Błąd zapisu historii w tle: {e}")
    
    # Funkcja pobierająca ostatni timestamp z lokalnego pliku historii, żeby wiedzieć od kiedy prosić o wiadomości z serwera (jeśli plik nie istnieje, zwraca 0)
    def get_last_timestamp_from_file(self, address):
        filename = self.get_history_filename(address)
        
        if not os.path.exists(filename):
            return 0
            
        try:
            with open(filename, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if not lines:
                    return 0
                
                last_line = lines[-1].strip()
                if not last_line.startswith("["):
                    return 0
                
                # Wycina dokładnie "YYYY-MM-DD HH:MM:SS" (pierwsze 19 znaków po nawiasie)
                # Ignoruje kropkę i milisekundy (.mmm)
                time_str = last_line[1:20] 
                
                from datetime import datetime
                dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                return int(dt.timestamp())
        except Exception as e:
            print(f"DEBUG HISTORIA: Nie udało się odczytać timestampu ({e})")
            return 0