import customtkinter as ctk
import protocols
import threading
import struct

class MainFrame(ctk.CTkFrame):
    def __init__(self, parent, client_socket):
        super().__init__(parent)
        self.sock = client_socket
        self.username = "damiansolec" # Możesz to przekazać z login_frame

        # --- Interfejs ---
        self.label = ctk.CTkLabel(self, text="Czat SOLEC", font=("Arial", 20))
        self.label.pack(pady=10)

        # Pole tekstowe (Historia)
        self.chat_display = ctk.CTkTextbox(self, width=350, height=180)
        self.chat_display.pack(pady=5, padx=10)
        self.chat_display.configure(state="disabled") # Tylko do odczytu

        # Pole do wpisywania
        self.msg_entry = ctk.CTkEntry(self, placeholder_text="Wpisz wiadomość...", width=250)
        self.msg_entry.pack(side="left", padx=(25, 5), pady=10)
        # Bindowanie klawisza Enter
        self.msg_entry.bind("<Return>", lambda e: self.send_message())

        # Przycisk Wyślij
        self.send_btn = ctk.CTkButton(self, text="Wyślij", width=80, command=self.send_message)
        self.send_btn.pack(side="left", padx=5, pady=10)

        # --- Wątek odbierania ---
        self.listen_thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.listen_thread.start()

    def send_message(self):
        content = self.msg_entry.get()
        if content:
            try:
                # Tworzymy pakiet (Nadawca: Twoja nazwa, Odbiorca: *, Treść: content)
                packet = protocols.get_message_packet("damiansolec", "*", content)
                self.sock.sendall(packet)
                
                # Czyścimy pole wpisywania
                self.msg_entry.delete(0, 'end')
            except Exception as e:
                print(f"Błąd wysyłania: {e}")

    def receive_loop(self):
        """Pętla działająca w tle, odbierająca wiadomości"""
        while True:
            try:
                header = self.sock.recv(3)
                if not header: break
                
                m_type, m_len = struct.unpack("!BH", header)
                payload = self.sock.recv(m_len)
                
                if m_type == protocols.TYPE_MESSAGE:
                    data = protocols.parse_message(payload)
                    if data:
                        text = f"{data['source']}: {data['content']}"
                        self.after(0, lambda: self.display_text(text))
            except:
                break

    def display_text(self, text):
        """Bezpieczne dopisywanie tekstu do okna"""
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", text + "\n")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")