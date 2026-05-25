#gałąź testowa
import customtkinter as ctk
import protocols
import threading
import struct
import os

from datetime import datetime

class MainFrame(ctk.CTkFrame):
    def __init__(self, parent, client_socket, username):
        super().__init__(parent)
        self.client_socket = client_socket
        self.my_username = username
        self.current_recipient = "" 
        self.channel_buttons_refs = [] # Przechowujemy referencje do przycisków

        # --- Konfiguracja siatki głównej ---
        # Kolumna 0: Panel boczny (stały, po lewej), Kolumna 1: Czat (rozszerzalny, po prawej)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1) 
        self.grid_rowconfigure(0, weight=1)

        # --- 1. LEWA STRONA: PANEL BOCZNY (Sidebar) ---
        self.sidebar = ctk.CTkFrame(self, width=250)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        self.channels_label = ctk.CTkLabel(self.sidebar, text="KANAŁY I USERZY", font=("Arial", 16, "bold"))
        self.channels_label.pack(pady=10)

        # Przewijana lista przycisków
        self.scroll_list = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.scroll_list.pack(fill="both", expand=True, padx=5, pady=5)

        # Przycisk "+" na dole sidebaru
        self.add_channel_btn = ctk.CTkButton(self.sidebar, text="+ Dodaj Rozmówcę/Kanał", fg_color="#28a745", hover_color="#218838", command=self.ask_for_target)
        self.add_channel_btn.pack(pady=10, padx=10)

        # --- 2. PRAWA STRONA: CZAT ---
        self.chat_container = ctk.CTkFrame(self, fg_color="transparent")
        self.chat_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.chat_container.grid_columnconfigure(0, weight=1)
        self.chat_container.grid_rowconfigure(0, weight=1)

        self.chat_display = ctk.CTkTextbox(self.chat_container, font=("Arial", 20))
        self.chat_display.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        self.chat_display.configure(state="disabled")

        self.msg_entry = ctk.CTkEntry(self.chat_container, placeholder_text="Wpisz wiadomość...", height=40, font=("Arial", 20))
        self.msg_entry.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        self.msg_entry.bind("<Return>", lambda e: self.send_message())

        self.send_btn = ctk.CTkButton(self.chat_container, text="Wyślij", width=100, height=40, font=("Arial", 20), command=self.send_message)
        self.send_btn.grid(row=1, column=1, sticky="e")

        # --- Inicjalizacja listy userów ---
        initial_users = ["user1", "user2", "user3"]
        for user in initial_users:
            self.add_item_to_list(f"{user}@localhost", is_channel=False)

        # Wybór domyślny
        self.select_target("user1@localhost")

        # Start wątku odbierania
        self.listen_thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.listen_thread.start()

    def add_item_to_list(self, address, is_channel=False):
        clean_address = address.strip().lower()
        display_name = clean_address.split('@')[0]
        
        # Tworzymy ramkę-kontener dla przycisku i "X"
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
        
        # Zapisujemy referencję do głównego przycisku (do zmiany kolorów w select_target)
        self.channel_buttons_refs.append((clean_address, btn))

    # Protokół dodowania kanału
    def ask_for_target(self):
        dialog = ctk.CTkInputDialog(text="Wpisz nazwę użytkownika (np. adam) lub kanału (np. #test):", title="Dodaj")
        input_val = dialog.get_input()
        
        if input_val:
            input_val = input_val.strip()
            
            if input_val.startswith('#'):
                # --- LOGIKA KANAŁU ---
                clean_name = input_val.lstrip('#').split('@')[0]
                full_address = f"#{clean_name}@localhost"
                self.join_channel(full_address) 
            else:
                # --- LOGIKA UŻYTKOWNIKA ---
                clean_name = input_val.split('@')[0]
                full_address = f"{clean_name}@localhost"
                
                # Dodajemy do listy i zaznaczamy
                self.add_item_to_list(full_address, is_channel=False)
                self.select_target(full_address)

    # Protokół dołączania do kanału
    def join_channel(self, address): 
        # full_address np 'test
        
        packet = protocols.get_join_channel(self.my_username, address)
        
        try:
            self.client_socket.sendall(packet)
            self.add_item_to_list(address, is_channel=True)
            self.select_target(address)

            print(f"DEBUG: Wysłano prośbę JOIN dla {address}")
        except Exception as e:
            print(f"Błąd: {e}")

    # Protokół opuszczania kanału i usuwania z listy
    def leave_channel(self, full_address, btn_frame):
        # 1. Protokół sieciowy (tylko dla kanałów)
        if full_address.startswith('#'):
            packet = protocols.get_leave_channel(self.my_username, full_address)
            try:
                self.client_socket.sendall(packet)
            except Exception as e:
                print(f"Błąd sieci: {e}")

        # 2. Czyszczenie listy referencji (ważne dla select_target!)
        self.channel_buttons_refs = [(addr, btn) for addr, btn in self.channel_buttons_refs if addr != full_address]

        # 3. Usuwanie z GUI
        btn_frame.destroy()
        
        # 4. Jeśli usunięto aktywne okno
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

        # 1. Wizualne zaznaczenie przycisku
        for addr, btn in self.channel_buttons_refs:
            if addr == address:
                btn.configure(fg_color="#28a745")
            else:
                btn.configure(fg_color="#3b3b3b")

        # 2. AUTOMATYCZNY JOIN (Tylko dla kanałów z #)
        # Serwer MUSI wiedzieć, że jesteśmy w pokoju, zanim da nam historię
        if address.startswith('#'):
            try:
                print(f"DEBUG SYNC: Wysyłam automatyczny JOIN dla {address}, aby odblokować historię")
                join_packet = protocols.get_join_channel(self.my_username, address)
                self.client_socket.sendall(join_packet)
                
                # Krótka przerwa (opcjonalnie, milisekundy), aby serwer przetworzył JOIN przed HISTORY
                time.sleep(0.05) 
            except Exception as e:
                print(f"Błąd auto-join: {e}")

        # 3. SYNCHRONIZACJA HISTORII Z SERWEREM
        since_time = self.get_last_timestamp_from_file(address)
        print(f"DEBUG SYNC: Proszę o historię dla {address} od timestampu: {since_time}")
        
        try:
            packet = protocols.get_history_packet(address, since_timestamp=since_time, count=100, offset=0)
            self.client_socket.sendall(packet)
        except Exception as e:
            print(f"Błąd wysyłania prośby o historię: {e}")

        # 4. Odświeżenie okna czatu z lokalnego pliku
        self.load_history(address)


    def get_history_filename(self, address):
        """Zwraca zawsze spójną nazwę pliku, np. history_ch_test.txt lub history_usr_user1.txt"""
        clean_addr = address.split('@')[0].strip().lower()
        if clean_addr.startswith('#'):
            safe_name = clean_addr.replace('#', 'ch_')
        else:
            safe_name = f"usr_{clean_addr}"
        return f"history_{safe_name}.txt"


    def load_history(self, address):
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        
        filename = self.get_history_filename(address)
        print(f"DEBUG: Próbuję wczytać plik historii: {filename}")

        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    content = f.read()
                    self.chat_display.insert("1.0", content)
            except Exception as e:
                print(f"Błąd czytania pliku: {e}")
        
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def send_message(self):
        content = self.msg_entry.get().strip()
        if not content or not self.current_recipient: return

        try:
            packet = protocols.get_message_packet(self.my_username, self.current_recipient, content)
            self.client_socket.sendall(packet)
            
            # --- NOWA LOGIKA: Pobieranie aktualnego czasu lokalnego dla siebie ---
            from datetime import datetime
            time_str = datetime.now().strftime('%H:%M:%S')
            
            # Wyświetlamy sformatowany tekst: [14:25:01] Ja: treść
            self.display_text(f"[{time_str}] {self.my_username}: {content}", self.current_recipient)
            self.msg_entry.delete(0, 'end')
        except Exception as e:
            print(f"Błąd wysyłania: {e}")

    def display_text(self, text, target):
        # Target może być 'user1' lub 'user1@localhost' lub '#test@localhost'
        filename = self.get_history_filename(target)
        
        # Zapisz do pliku
        try:
            with open(filename, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception as e: 
            print(f"DEBUG BŁĄD ZAPISU HISTORII: {e}")

        # Wyświetl tylko jeśli okno pasuje
        inc_id = target.split('@')[0].strip().lower()
        curr_id = self.current_recipient.split('@')[0].strip().lower()
        
        if inc_id == curr_id:
            self.chat_display.configure(state="normal")
            self.chat_display.insert("end", text + "\n")
            self.chat_display.configure(state="disabled")
            self.chat_display.see("end")
        else:
            print(f"DEBUG UI: Wiadomość dla {inc_id} zapisała się w pliku {filename}. Masz otwarte: {curr_id}")

    def receive_exact(self, n):
        data = b''
        try:
            # Usuwamy timeout na chwilę, aby sprawdzić czy to nie on rozłącza
            self.client_socket.settimeout(None) 
            while len(data) < n:
                chunk = self.client_socket.recv(n - len(data))
                if not chunk:
                    return None # Goodbye World od servera
                data += chunk
            return data
        except Exception as e:
            print(f"--- [DEBUG] Błąd recv: {e} ---")
            return None
    
    # główna funkcja odbierania - cały czas nasłuchuje, a gdy przyjdzie wiadomość, to ją parsuje i wyświetla w odpowiednim oknie
    def receive_loop(self):
        while True:
            header = self.receive_exact(3)
            if not header: break
            
            m_type, m_len = struct.unpack("!BH", header)
            payload = self.receive_exact(m_len)
            
            if m_type == protocols.TYPE_ERROR:
                    # Sprawdzamy, czy payload w ogóle ma sens do dekodowania jako tekst
                    if payload and len(payload) >= 2:
                        try:
                            err_msg, _ = protocols.decode_string(payload, 0)
                        except Exception:
                            err_msg = f"Nieznany kod błędu (Surowe bajty: {payload.hex()})"
                    elif payload:
                        # Jeśli to tylko 1 bajt, to może być surowy kod błędu z serwera
                        err_msg = f"Kod błędu: {payload[0]} (0x{payload.hex()})"
                    else:
                        err_msg = "Pusty błąd serwera (Brak autoryzacji)"
                    
                    print(f"!!! SERWER ZGŁOSIŁ BŁĄD: {err_msg}")
                    
                    # Wyświetlamy błąd użytkownikowi
                    formatted_err = f"⚠️ [BŁĄD AUTORYZACJI]: {err_msg}"
                    self.after(0, lambda t=formatted_err: self.display_text(t, self.current_recipient))
                    
                    continue # PRZECHODZIMY DO KOLEJNEJ WIADOMOŚCI, WĄTEK ŻYJE!
            
            elif m_type == protocols.TYPE_MESSAGE:
                data = protocols.parse_message(payload)
                if data:
                    # 'user1@localhost:9999' -> 'user1'
                    # '#test@localhost' -> '#test'
                    s_clean = data['source'].split('@')[0].strip().lower()
                    t_clean = data['target'].split('@')[0].strip().lower()
                    
                    # USTALANIE OKNA DOCELOWEGO:
                    # Jeśli cel zaczyna się od '#', to jest to wiadomość KANAŁOWA.
                    if t_clean.startswith('#'):
                        chat_id = t_clean
                    else:
                        # W przeciwnym razie to PRIV (okno nadawcy)
                        chat_id = s_clean

                    #  Nie wyświetla wiadomości, które sam wysłałeś
                    my_nick = self.my_username.split('@')[0].strip().lower()
                    if s_clean == my_nick:
                        continue 



                    # --- NOWA LOGIKA: Formatowanie czasu z serwera ---
                    from datetime import datetime
                    # Serwer daje nam sekundy, zamieniamy je na obiekt datetime, a potem na tekst HH:MM:SS
                    time_str = datetime.fromtimestamp(data['timestamp']).strftime('%H:%M:%S')

                    # Łączymy w format: [14:25:01] user: treść wiadomości
                    formatted_msg = f"[{time_str}] {s_clean}: {data['content']}"
                    
                    print(f"DEBUG RECV: Od={s_clean}, Do={t_clean}, Okno={chat_id}")
                    
                    self.after(0, lambda t=formatted_msg, s=chat_id: self.display_text(t, s))
    
    # ostatni timestamp z historii, potrzebny do protokołu history
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
                
                time_str = last_line[1:9] # Wyciąga "HH:MM:SS"
                
                from datetime import datetime
                today_date = datetime.now().strftime("%Y-%m-%d")
                full_time_str = f"{today_date} {time_str}"
                
                dt = datetime.strptime(full_time_str, "%Y-%m-%d %H:%M:%S")
                return int(dt.timestamp())
        except Exception as e:
            print(f"DEBUG HISTORIA: Nie udało się odczytać timestampu ({e})")
            return 0


    