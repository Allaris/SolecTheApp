# EKRAN POWITALNY: MASZTY RADIOWE W SOLCU KUJAWSKIM (ASCII ART)
SOLEC_WELCOME_ART = """




                                            ||        
                                            ||        
                                           ]||[       ||
                                            ||        ||
                                            ||        ||
                                            ||        ||
                                           ]||[      ]||[
                                            ||        ||
                                            ||        ||
                                        ___]||[______]||[____
                                        |   Witaj w SOLEC   | 
                                        
                                        
                                „Transfer.  Skan. Wirtualizacja.”

"""

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

        domain = protocols.SERVER_DOMAIN
        # Pełny JID zalogowanego użytkownika 
        username_clean = username.strip()
        if "@" not in username_clean:
            self.my_username = f"{username_clean}@{domain}"
        else:
            self.my_username = username_clean
            
        # print(f"--- [DEBUG START] Zalogowany jako pełny JID: {self.my_username} ---")

        # Bo duzo historii
        self.current_history_offset = 0
        self.messages_received_in_batch = 0

        self.current_recipient = "" 
        self.channel_buttons_refs = [] # Referencje do przycisków kanałów i użytkowników (adres, przycisk)
        self.loaded_addresses = set()  # Zbiór do unikania duplikatów przy dynamicznym ładowaniu

        # --- Konfiguracja siatki głównej (ułożenie)------------------------------
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
        self.profile_frame.pack_propagate(False) 

        # Czystki login bez domeny do wyświetlenia w profilu
        my_clean_nick = self.my_username.split('@')[0].strip()

        # Etykieta wyświetlająca informację o zalogowanym userze
        self.user_label = ctk.CTkLabel(
            self.profile_frame, 
            text=f"👤 Zalogowany: {my_clean_nick}", 
            font=("Arial", 12, "bold"), 
            anchor="w", 
            text_color="#28a745" 
        )
        self.user_label.pack(side="left", padx=10, fill="both", expand=True)

        # PRAWA STRONA: CZAT ------------------------------------------------------------------------------------------------------------------------------------------------------------------
        self.chat_container = ctk.CTkFrame(self, fg_color="transparent")
        self.chat_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.chat_container.grid_columnconfigure(0, weight=1)
        self.chat_container.grid_rowconfigure(0, weight=1)

        # Okno czatu
        self.chat_display = ctk.CTkTextbox(self.chat_container, font=("Courier New", 16)) # Zmiana czcionki na stałą szerokość (Courier New) dla idealnego ASCII Artu
        self.chat_display.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        
        # Wrzucam rysunek anten na start 
        self.chat_display.configure(state="normal")
        self.chat_display.insert("1.0", SOLEC_WELCOME_ART)
        self.chat_display.configure(state="disabled")

        # Pole wpisywania wiadomości 
        self.msg_entry = ctk.CTkEntry(self.chat_container, placeholder_text="Wpisz wiadomość...", height=40, font=("Arial", 20))
        self.msg_entry.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        self.msg_entry.bind("<Return>", lambda e: self.send_message())

        # Przycisk wysyłania wiadomości
        self.send_btn = ctk.CTkButton(self.chat_container, text="Wyślij", width=100, height=40, font=("Arial", 20), command=self.send_message)
        self.send_btn.grid(row=1, column=1, sticky="e")

        # LOGIKA POŁĄCZENIA I PROTOKOŁÓW ------------------------------------------------------------------------------------------------------------------------------------------------------------------

        self.request_user_and_channel_list()

        # Start wątku odbierania
        self.listen_thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.listen_thread.start()

    # Wysyła żądanie o listę obiektów z bazy danych serwera
    def request_user_and_channel_list(self):
        try:
            # print("DEBUG LIST: Wysyłam żądanie TYPE_LIST (0x09) do serwera...")
            packet = protocols.get_list_packet(count=100, offset=0)
            self.client_socket.sendall(packet)
        except Exception as e:
            print(f"!!! Błąd podczas wysyłania prośby o listę: {e}")

    # Dodaje przycisk do listy po lewej stronie.
    def add_item_to_list(self, address, is_channel=False):
        clean_address = address.strip().lower()
        
        # Jeśli ten adres już został dodany w tej sesji, ignorujemy go
        if clean_address in self.loaded_addresses:
            return
        self.loaded_addresses.add(clean_address)

        # Wyświetla krótką nazwę: #tel lub damian
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
            fg_color="#c82333", 
            hover_color="#a71d2a",
            command=lambda: self.leave_channel(clean_address, item_frame)
        )
        delete_btn.pack(side="right")
        
        self.channel_buttons_refs.append((clean_address, btn))

        # Jeśli aplikacja jeszcze nie ma wybranego celu rozmowy, ustawiam ten pierwszy pobrany jako domyślny
        # if not self.current_recipient:
        #     self.select_target(clean_address)

    def ask_for_target(self):
        dialog = ctk.CTkInputDialog(text="Wpisz nazwę użytkownika (np. damian) lub kanału (np. #tem):", title="Dodaj")
        input_val = dialog.get_input()
        domain = protocols.SERVER_DOMAIN
        if input_val:
            input_val = input_val.strip()
            
            if input_val.startswith('#'):
                clean_name = input_val.lstrip('#').split('@')[0]
                full_address = f"#{clean_name}@{domain}"
                self.join_channel(full_address) 
            else:
                clean_name = input_val.split('@')[0]
                full_address = f"{clean_name}@{domain}"
                
                self.add_item_to_list(full_address, is_channel=False)
                self.select_target(full_address)

    def join_channel(self, address): 
        packet = protocols.get_join_channel(self.my_username, address)
        try:
            self.client_socket.sendall(packet)
            self.add_item_to_list(address, is_channel=True)
            self.select_target(address)
            # print(f"DEBUG: Wysłano prośbę JOIN dla {address}")
        except Exception as e:
            print(f"Błąd JOIN: {e}")

    def leave_channel(self, full_address, btn_frame):
        if full_address.startswith('#'):
            packet = protocols.get_leave_channel(self.my_username, full_address)
            try:
                self.client_socket.sendall(packet)
            except Exception as e:
                print(f"Błąd sieci: {e}")

        self.channel_buttons_refs = [(addr, btn) for addr, btn in self.channel_buttons_refs if addr != full_address]
        if full_address in self.loaded_addresses:
            self.loaded_addresses.remove(full_address)

        btn_frame.destroy()
        
        if self.current_recipient == full_address:
            self.current_recipient = ""
            self.chat_display.configure(state="normal")
            self.chat_display.delete("1.0", "end")
            self.chat_display.insert("end", "Wybierz rozmówcę...")
            self.chat_display.configure(state="disabled")

    def select_target(self, address):
        if self.current_recipient == address: return
        self.current_recipient = address

        # Wizualne zaznaczenie przycisku na liście bocznej
        for addr, btn in self.channel_buttons_refs:
            if addr == address:
                btn.configure(fg_color="#28a745")
            else:
                btn.configure(fg_color="#3b3b3b")

        # Zapewnienie, że plik istnieje
        filename = self.get_history_filename(address)
        if not os.path.exists(filename):
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception as e:
                print(f"Błąd tworzenia pliku: {e}")

        # Odświeżenie okna czatu z tego co już mamy lokalnie
        self.load_history(address)

        # Jeśli to kanał, musimy najpierw wysłać JOIN (to robimy od razu w głównym wątku)
        if address.startswith('#'):
            try:
                join_packet = protocols.get_join_channel(self.my_username, address)
                self.client_socket.sendall(join_packet)
            except Exception as e:
                print(f"Błąd auto-join: {e}")

        # URUCHOMIENIE PĘTLI POBIERANIA W TLE
        #  osobny wątek, który będzie pytał o historię dotąd, aż pobierze całą.
        downloader_thread = threading.Thread(
            target=self._paged_history_downloader_loop, 
            args=(address,), 
            daemon=True
        )
        downloader_thread.start()

    # Pętla, która w tle pyta serwer o kolejne strony historii, aż dojdzie do końca (serwer przestanie wysyłać wiadomości).
    def _paged_history_downloader_loop(self, address):

        # print(f"--- [START] Automatyczna pętla pobierania historii dla {address} ---")
        
        current_offset = 0
        filename = self.get_history_filename(address)
        
        # Pobiera timestamp bazowy (z momentu kliknięcia)
        since_time = self.get_last_timestamp_from_file(address)

        while True:
            # Sprawdza rozmiar pliku PRZED wysłaniem zapytania
            try:
                size_before = os.path.getsize(filename)
            except OSError:
                size_before = 0

            # Jeśli użytkownik w międzyczasie przełączył okno na kogoś innego, przerywa pętlę
            if self.current_recipient != address:
                # print(f"DEBUG PAGINATION: Użytkownik zmienił okno. Przerywam pętlę dla {address}")
                break

            # print(f"DEBUG PAGINATION: Proszę o historię {address} (offset: {current_offset}, since: {since_time})")
            
            try:
                packet = protocols.get_history_packet(address, since_timestamp=since_time, count=100, offset=current_offset)
                self.client_socket.sendall(packet)
            except Exception as e:
                print(f"Błąd wysyłania żądania offsetu {current_offset}: {e}")
                break

            time.sleep(0.25)

            # Sprawdza rozmiar pliku PO odebraniu potencjalnej paczki wiadomości
            try:
                size_after = os.path.getsize(filename)
            except OSError:
                size_after = 0

            # JEŻELI PLIK URÓSŁ: oznacza to, że wpadły nowe wiadomości. Zwiększa offset i szuka dalej
            if size_after > size_before:
                # print(f"DEBUG PAGINATION: Plik urósł (z {size_before} do {size_after} bajtów). Przechodzę do następnej strony.")
                current_offset += 100
            else:
                # JEŻELI PLIK NIE URÓSŁ: oznacza to, że serwer nie przysłał już nic nowego dla tego offsetu (koniec historii w bazie)
                # print(f"--- [KONIEC] Brak nowych danych dla {address} na offsecie {current_offset}. Kończę pętlę. ---")
                break

    def get_history_filename(self, address):
        domain = protocols.SERVER_DOMAIN
        me = self.my_username.split('@')[0].strip().lower()
        target = address.split('@')[0].strip().lower()

        safe_name = f"history_{domain}_{me}_{target}"
        safe_name = safe_name.replace('.', '_')
        return f"{safe_name}.txt"

    def load_history(self, address):
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        
        filename = self.get_history_filename(address)
        
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
                if content.strip():
                    self.chat_display.insert("1.0", content)
        except Exception as e:
            print(f"Błąd czytania pliku historii: {e}")
        
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def send_message(self):
        content = self.msg_entry.get().strip()
        if not content: return

        try:
            # Wysyła wiadomość do serwera
            packet = protocols.get_message_packet(self.my_username, self.current_recipient, content)
            self.client_socket.sendall(packet)
            
            # Czyszczenie pola wpisywania
            self.msg_entry.delete(0, "end")
            
            # żąda historię dla bieżącego okna
            address = self.current_recipient
            since_time = self.get_last_timestamp_from_file(address)
            
            # print(f"DEBUG SEND&SYNC: Wysłano wiadomość. Od razu żądam historii dla {address} od ts: {since_time}")
            history_packet = protocols.get_history_packet(address, since_timestamp=since_time, count=100, offset=0)
            self.client_socket.sendall(history_packet)
            
        except Exception as e:
            print(f"Błąd podczas wysyłania lub natychmiastowej synchronizacji: {e}")
    
    def display_text(self, text, target):
        filename = self.get_history_filename(target)
        try:
            with open(filename, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception as e: 
            print(f"DEBUG BŁĄD ZAPISU HISTORII: {e}")

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
                
                print(f"!!! SERWER ZGŁOSIŁ BŁĄD: {err_msg} | Aktywne okno: {self.current_recipient} | Mój JID: {self.my_username}")
                continue 
            
            # Obsługa przychodzących elementów listy użytkowników/kanałów (TYPE_LISTITEM) ---------------------------------------------------------------------------------------------
            elif m_type == protocols.TYPE_LISTITEM:
                address = protocols.parse_list_item(payload)
                if address:
                    # Pomija samego siebie w liście kontaktów
                    if address.lower() == self.my_username.lower():
                        continue
                    
                    is_chan = address.startswith('#')
                    # print(f"DEBUG UI: Otrzymano dynamiczny kontakt z serwera: {address}")
                    
                    # Aktualizacja widoku tkintera z poziomu wątku tła sieciowego
                    self.after(0, lambda addr=address, chan=is_chan: self.add_item_to_list(addr, is_channel=chan))

            # Obsługa wiadomości (TYPE_MESSAGE) ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            elif m_type == protocols.TYPE_MESSAGE:
                data = protocols.parse_message(payload)
                
                if data:
                    s_clean = data['source'].split('@')[0].strip().lower()
                    t_clean = data['target'].split('@')[0].strip().lower()
                    my_nick = self.my_username.split('@')[0].strip().lower()
                    curr_id = self.current_recipient.split('@')[0].strip().lower()
                    
                    if t_clean.startswith('#'):
                        chat_id = t_clean
                    else:
                        if s_clean == my_nick:
                            chat_id = t_clean
                        else:
                            chat_id = s_clean

                    ts = data['timestamp']
                    if ts > 9999999999: ts = ts / 1000.0

                    try:
                        dt_object = datetime.fromtimestamp(ts)
                        base_time = dt_object.strftime('%Y-%m-%d %H:%M:%S')
                        ms_str = dt_object.strftime('%f')[:3]
                        time_str = f"{base_time}.{ms_str}"
                    except Exception:
                        now = datetime.now()
                        base_time = now.strftime('%Y-%m-%d %H:%M:%S')
                        ms_str = now.strftime('%f')[:3]
                        time_str = f"{base_time}.{ms_str}"
                    
                    # Czyszczenie NULLi przy tworzeniu linijki tekstu
                    clean_content = data['content'].replace('\x00', '').strip()
                    formatted_msg = f"[{time_str}] {s_clean}: {clean_content}"
                    
                    filename = self.get_history_filename(chat_id)
                    
                    # Sprawdzanie duplikatów
                    already_in_file = False
                    if os.path.exists(filename):
                        try:
                            with open(filename, "r", encoding="utf-8") as f:
                                already_in_file = formatted_msg in f.read()
                        except Exception:
                            pass

                    if not already_in_file:
                        try:
                            with open(filename, "a", encoding="utf-8") as f:
                                f.write(formatted_msg + "\n")
                        except Exception as e:
                            print(f"Błąd zapisu historii: {e}")

                        # Jeśli okno jest otwarte, dokleja na ekran na bieżąco
                        is_current_chat_open = (chat_id == curr_id)
                        if is_current_chat_open:
                            self.after(0, lambda t=formatted_msg: self.chat_display.configure(state="normal") or 
                                                                                 self.chat_display.insert("end", t + "\n") or 
                                                                                 self.chat_display.configure(state="disabled") or 
                                                                                 self.chat_display.see("end"))
    
    def get_last_timestamp_from_file(self, address):
        filename = self.get_history_filename(address)
        
        if not os.path.exists(filename):
            return 0
            
        try:
            with open(filename, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if not lines:
                    return 0
                
                # Szuka ostatniej niepustej linii od końca pliku
                last_line = ""
                for line in reversed(lines):
                    if line.strip():
                        last_line = line.strip()
                        break
                        
                if not last_line:
                    return 0
                
                # Wyrażenie regularne wyciąga tekst pomiędzy pierwszym napotkanym '[' a ']'
                
                import re
                match = re.search(r'^\[([^\]]+)\]', last_line)
                if not match:
                    return 0
                
                full_time_str = match.group(1) # np "2026-06-04 22:39:36.123"
                
                try:
                    dt = datetime.strptime(full_time_str, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    # Zabezpieczenie na wypadek, gdyby w pliku były jeszcze stare linie bez milisekund (równe sekundy)
                    time_str_fallback = full_time_str.split('.')[0]
                    dt = datetime.strptime(time_str_fallback, "%Y-%m-%d %H:%M:%S")

              
                
                # opcja do testowania (UnixMilli):
                return int(dt.timestamp() * 1000)
        except Exception as e:
            print(f"DEBUG HISTORIA: Nie udało się odczytać timestampu ({e})")
            return 0