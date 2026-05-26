import customtkinter as ctk
import protocols  

class ServerFrame(ctk.CTkFrame):
    def __init__(self, parent, on_connect_callback):
        super().__init__(parent)
        self.on_connect_callback = on_connect_callback

        # --- Nagłówek aplikacji ---
        self.title_label = ctk.CTkLabel(
            self, 
            text="Wybór serwera", 
            font=("Arial", 24, "bold")
        )
        self.title_label.place(relx=0.5, rely=0.2, anchor="center")

        # --- Podpis instrukcji ---
        self.info_label = ctk.CTkLabel(
            self, 
            text="Podaj adres serwera, z którym chcesz się połączyć:", 
            font=("Arial", 14)
        )
        self.info_label.place(relx=0.5, rely=0.32, anchor="center")

        # --- Pole tekstowe z domyślnie wpisanym "rctt.net" ---
        self.server_entry = ctk.CTkEntry(
            self, 
            width=300, 
            height=40, 
            font=("Arial", 20),
            placeholder_text="rctt.net"
        )
        self.server_entry.insert(0, "rctt.net")  # Wpisane domyślnie
        self.server_entry.place(relx=0.5, rely=0.43, anchor="center")

        # --- Przycisk "Połącz" ---
        self.connect_button = ctk.CTkButton(
            self, 
            text="Połącz", 
            width=200, 
            height=40, 
            font=("Arial", 20, "bold"),
            command=self.handle_connect,
            fg_color="#28a745",
            hover_color="#218838"
        )
        self.connect_button.place(relx=0.5, rely=0.55, anchor="center")

    def handle_connect(self):
        domain = self.server_entry.get().strip()
        if not domain:
            return  # Zabezpieczenie przed pustym polem

        # Zapisanie domeny do zmiennej globalnej w protocols.py
        protocols.SERVER_DOMAIN = domain
        print(f"--- [CONFIG] Zmieniono domenę na: {protocols.SERVER_DOMAIN} ---")

        # Callback, który przeniesie nas do ekranu logowania
        self.on_connect_callback()