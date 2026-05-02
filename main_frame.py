# gałąź testowa
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
        self.current_recipient = "" # Zaczynamy od pustego, select_user go ustawi
        self.channel_buttons = []

        # --- Konfiguracja siatki ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0) 
        self.grid_rowconfigure(0, weight=1)

        # --- 1. LEWA STRONA: CZAT ---
        self.chat_container = ctk.CTkFrame(self, fg_color="transparent")
        self.chat_container.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=10, pady=10)
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

        # --- 2. PRAWA STRONA: KANAŁY ---
        self.channels_frame = ctk.CTkFrame(self, width=200)
        self.channels_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=10, pady=10)
        
        self.channels_label = ctk.CTkLabel(self.channels_frame, text="Kontakty", font=("Arial", 18, "bold"))
        self.channels_label.pack(pady=10)

        users = ["user1", "user2", "user3"]
        for user in users:
            # Używamy pełnego adresu jako identyfikatora
            full_addr = f"{user}@localhost"
            btn = ctk.CTkButton(
                self.channels_frame, 
                text=user, 
                command=lambda u=full_addr: self.select_user(u),
                fg_color="#3b3b3b",
                hover_color="#4b4b4b"
            )
            btn.pack(pady=5, padx=10, fill="x")
            self.channel_buttons.append((full_addr, btn))

        # Wybór pierwszego użytkownika na start
        self.select_user("user1@localhost")

        self.listen_thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.listen_thread.start()

    def receive_exact(self, n):
        data = b''
        while len(data) < n:
            chunk = self.client_socket.recv(n - len(data))
            if not chunk: return None
            data += chunk
        return data

    def send_message(self):
        content = self.msg_entry.get()
        if not content: return

        try:
            target = self.current_recipient
            packet = protocols.get_message_packet(self.my_username, target, content)
            self.client_socket.sendall(packet)

            # Zapisujemy i wyświetlamy (target to osoba, z którą rozmawiamy)
            my_text = f"Ja: {content}"
            self.display_text(my_text, target)
            self.msg_entry.delete(0, 'end')
        except Exception as e:
            print(f"Błąd wysyłania: {e}")

    def receive_loop(self):
        while True:
            try:
                header = self.receive_exact(3)
                if not header: break
                
                m_type, m_len = struct.unpack("!BH", header)
                payload = self.receive_exact(m_len)
                if payload is None: break
                
                if m_type == protocols.TYPE_MESSAGE:
                    data = protocols.parse_message(payload)
                    if data:
                        sender = data['source'] # Tutaj serwer daje np. 'user1@localhost:9999'
                        content = data['content']
                        
                        # Formatujemy tekst do wyświetlenia
                        display_name = sender.split('@')[0] # Samo 'user1' dla czytelności
                        text = f"{display_name}: {content}"
                        
                        # Przekazujemy pełny sender, display_text sam go wyczyści
                        self.after(0, lambda t=text, s=sender: self.display_text(t, s))

            except Exception as e:
                continue

    def display_text(self, text, target):
        # 1. Usuwamy ewentualny port z adresu (np. user1@localhost:9999 -> user1@localhost)
        clean_target = target.split(':')[0]
        
        # 2. Zapis do pliku (używamy czystej nazwy)
        filename = f"history_{clean_target.replace('@', '_').replace('.', '_')}.txt"
        with open(filename, "a", encoding="utf-8") as f:
            f.write(text + "\n")

        # 3. Wyświetlanie: Porównujemy czysty adres nadawcy z czystym adresem wybranym w GUI
        current_clean = self.current_recipient.split(':')[0]
        
        if clean_target == current_clean:
            self.chat_display.configure(state="normal")
            self.chat_display.insert("end", text + "\n")
            self.chat_display.configure(state="disabled")
            self.chat_display.see("end")
        else:
            print(f"Otrzymano wiadomość od {clean_target}, ale aktualnie piszesz z {current_clean}")

    def select_user(self, full_address):
        """Przełącza widok na innego użytkownika."""
        if self.current_recipient == full_address:
            return

        self.current_recipient = full_address
        
        # 1. Kolory przycisków
        for addr, btn in self.channel_buttons:
            if addr == full_address:
                btn.configure(fg_color="#1a1a1a", border_width=2, border_color="#28a745")
            else:
                btn.configure(fg_color="#3b3b3b", border_width=0)

        # 2. Ładowanie historii z pliku
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        
        filename = f"history_{full_address.replace('@', '_')}.txt"
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                history = f.read()
                self.chat_display.insert("1.0", history)
        
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")