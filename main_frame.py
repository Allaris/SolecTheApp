#main
import customtkinter as ctk
import protocols
import threading
import struct

class MainFrame(ctk.CTkFrame):
    def __init__(self, parent, client_socket):
        super().__init__(parent)
        self.sock = client_socket
        self.username = "damiansolec" 

        # --- Interfejs ---
        self.label = ctk.CTkLabel(self, text="Czat SOLEC", font=("Arial", 20))
        self.label.pack(pady=10)

        self.chat_display = ctk.CTkTextbox(self, width=350, height=180)
        self.chat_display.pack(pady=5, padx=10)
        self.chat_display.configure(state="disabled")

        self.msg_entry = ctk.CTkEntry(self, placeholder_text="Wpisz wiadomość...", width=250)
        self.msg_entry.pack(side="left", padx=(25, 5), pady=10)
        self.msg_entry.bind("<Return>", lambda e: self.send_message())

        self.send_btn = ctk.CTkButton(self, text="Wyślij", width=80, command=self.send_message)
        self.send_btn.pack(side="left", padx=5, pady=10)

        # TYLKO JEDEN WĄTEK!
        self.listen_thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.listen_thread.start()

    def receive_exact(self, n):
        """Pobiera dokładnie n bajtów - rozwiązuje problem przerywania"""
        data = b''
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk: return None
            data += chunk
        return data

    def send_message(self):
        content = self.msg_entry.get()
        if content:
            try:
                # Wysyłaj zawsze jako self.username
                packet = protocols.get_message_packet(self.username, "*", content)
                self.sock.sendall(packet)
                self.msg_entry.delete(0, 'end')
            except Exception as e:
                print(f"Błąd wysyłania: {e}")

    def receive_loop(self):
        # print("Wątek odbioru: AKTYWNY")
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
                        # Jeśli to my, napisz "Ty", jeśli ktoś inny - nick
                        display_name = "Ty" if sender == self.username else sender
                        text = f"{display_name}: {data['content']}"
                        
                        # Przekazujemy tekst do GUI (lambda m=text zamraża treść)
                        self.after(0, lambda m=text: self.display_text(m))
                        print(f"Odebrano: {text}")

            except Exception as e:
                # print(f"Błąd pętli: {e}")
                # Nie przerywaj pętli, spróbuj odczekać i kontynuować
                continue

    def display_text(self, text):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", text + "\n")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")