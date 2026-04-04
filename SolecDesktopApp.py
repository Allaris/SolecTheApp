#gałąź testowa
import customtkinter as ctk
import socket
import struct

from login_frame import LoginFrame    # Importujemy klasę z pliku login_frame.py
from main_frame import MainFrame    # Importujemy klasę z pliku main_frame.py

# --- KONFIGURACJA PROTOKOŁU ---
from protocols import HANDSHAKE,PING,VERSION   # Importujemy protokoły z osobnego pliku

class SolecApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Solec Desktop App")
        self.geometry("400x300")
        
        # Wspólne zasoby
        self.client_socket = None
        
        # Kontener na widoki
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        
        # Startujemy od ekranu logowania
        self.show_login_screen()

    def show_login_screen(self):
        self.clear_container()
        login_frame = LoginFrame(self.container, self.on_login_success)
        login_frame.pack(fill="both", expand=True)

    def show_main_screen(self):
        self.clear_container()
        main_frame = MainFrame(self.container, self.client_socket)
        main_frame.pack(fill="both", expand=True)

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def on_login_success(self, connected_socket):
        self.client_socket = connected_socket
        self.show_main_screen()



if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    app = SolecApp()
    app.mainloop()