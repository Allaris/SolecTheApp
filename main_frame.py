#gałąź testowa
import customtkinter as ctk
import protocols
import threading
import struct
import os

class MainFrame(ctk.CTkFrame):
    def __init__(self, parent, client_socket, username):
        super().__init__(parent)
        self.client_socket = client_socket
        self.my_username = username
        self.current_recipient = "" 
        self.channel_buttons_refs = [] # Przechowujemy referencje do przycisków

        # --- Konfiguracja siatki głównej ---
        # Kolumna 0: Czat (rozszerzalna), Kolumna 1: Panel boczny (stały)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0) 
        self.grid_rowconfigure(0, weight=1)

        # --- 1. LEWA STRONA: CZAT ---
        self.chat_container = ctk.CTkFrame(self, fg_color="transparent")
        self.chat_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
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

        # --- 2. PRAWA STRONA: PANEL BOCZNY (Sidebar) ---
        self.sidebar = ctk.CTkFrame(self, width=250)
        self.sidebar.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        self.channels_label = ctk.CTkLabel(self.sidebar, text="KANAŁY I USERZY", font=("Arial", 16, "bold"))
        self.channels_label.pack(pady=10)

        # Przewijana lista przycisków
        self.scroll_list = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.scroll_list.pack(fill="both", expand=True, padx=5, pady=5)

        # Przycisk "+" na dole sidebaru
        self.add_channel_btn = ctk.CTkButton(self.sidebar, text="+ Dodaj Kanał", fg_color="#28a745", hover_color="#218838", command=self.ask_for_channel)
        self.add_channel_btn.pack(pady=10, padx=10)

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
        
        # Wyświetlana nazwa na przycisku
        display_name = clean_address.split('@')[0]
        
        btn = ctk.CTkButton(
            self.scroll_list, 
            text=display_name,
            anchor="w",
            command=lambda: self.select_target(clean_address),
            fg_color="#3b3b3b"
        )
        btn.pack(pady=2, padx=5, fill="x")
        
        # zapis ref do zmiany koloru przy zaznaczeniu
        self.channel_buttons_refs.append((clean_address, btn))

    def ask_for_channel(self):
        dialog = ctk.CTkInputDialog(text="Nazwa kanału:", title="Nowy Kanał")
        channel_name = dialog.get_input()
        if channel_name:
            clean_name = channel_name.strip().lstrip('#')
            full_address = f"#{clean_name}@localhost"
            
            # dołączenie po dodaniu do listy
            self.join_channel(full_address)

    def join_channel(self, full_address): 
        # full_address np '#test@localhost'
        
        packet = protocols.get_join_channel(self.my_username, full_address)
        
        try:
            self.client_socket.sendall(packet)
            self.add_item_to_list(full_address, is_channel=True)
            self.select_target(full_address)

            print(f"DEBUG: Wysłano prośbę JOIN dla {full_address}")
        except Exception as e:
            print(f"Błąd: {e}")

    def select_target(self, address):
        # przełącza odbiorce i wczysuje historię
        if self.current_recipient == address: return
        self.current_recipient = address

        # Wizualne zaznaczenie przycisku
        for addr, btn in self.channel_buttons_refs:
            if addr == address:
                btn.configure(fg_color="#28a745")
            else:
                btn.configure(fg_color="#3b3b3b")

        # Odświeżenie okna czatu z historii
        self.load_history(address)

    def load_history(self, address):
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        
        # "safe_name" jak przy zapisie do pliku, np. '#test@localhost' -> 'history_ch_test'
        clean_addr = address.split('@')[0].strip().lower()
        safe_name = clean_addr.replace('#', 'ch_')
        filename = f"history_{safe_name}.txt"
        
        print(f"DEBUG: Próbuję wczytać plik: {filename}")

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
            
            self.display_text(f"Ja: {content}", self.current_recipient)
            self.msg_entry.delete(0, 'end')
        except Exception as e:
            print(f"Błąd wysyłania: {e}")

    def display_text(self, text, target):
    
        inc_id = target.split('@')[0].strip().lower()
        curr_id = self.current_recipient.split('@')[0].strip().lower()
        
        # generowanie nazwy pliku na podstawie  '#test' -> 'history_ch_test'
        safe_name = inc_id.replace('#', 'ch_')
        filename = f"history_{safe_name}.txt"
        
        # Zapisz do pliku
        try:
            with open(filename, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except: pass

        # Wyświetl tylko jeśli okno pasuje
        if inc_id == curr_id:
            self.chat_display.configure(state="normal")
            self.chat_display.insert("end", text + "\n")
            self.chat_display.configure(state="disabled")
            self.chat_display.see("end")
        else:
            print(f"DEBUG UI: Wiadomość dla {inc_id} zapisała się w tle. Masz otwarte: {curr_id}")

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

    def receive_loop(self):
        while True:
            header = self.receive_exact(3)
            if not header: break
            
            m_type, m_len = struct.unpack("!BH", header)
            payload = self.receive_exact(m_len)
            
            if m_type == protocols.TYPE_ERROR:
                # jak odrzyciło
                err_msg, _ = protocols.decode_string(payload, 0)
                print(f"!!! SERWER ZGŁOSIŁ BŁĄD: {err_msg}")
            
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

                    formatted_msg = f"{s_clean}: {data['content']}"
                    
                    # Bardzo ważny debug - sprawdzimy co widzi Python
                    print(f"DEBUG RECV: Od={s_clean}, Do={t_clean}, Okno={chat_id}")
                    
                    self.after(0, lambda t=formatted_msg, s=chat_id: self.display_text(t, s))