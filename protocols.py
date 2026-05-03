#gałąź testowa

# wsl
# cd ~/solec/cmd/daemon
# go run main.go

import struct
import time

# login: cokolwiek
# hasło: valid

# --- KONFIGURACJA TYPÓW (Tabela 1) ---#
TYPE_SUCCESS   = 0x01
TYPE_ERROR     = 0x02
TYPE_HANDSHAKE = 0x03
TYPE_AUTH      = 0x04
TYPE_MESSAGE   = 0x05

TYPE_USERMODE  = 0x07

def encode_string(s):
    """2.3.3. String: 2 bajty długości + dane UTF-8"""
    encoded = s.encode("utf-8")
    return struct.pack("!H", len(encoded)) + encoded

def decode_string(payload, offset):
    """Pomocnicza funkcja do czytania stringów z payloadu"""
    length = struct.unpack_from("!H", payload, offset)[0]
    offset += 2
    text = payload[offset : offset + length].decode("utf-8")
    return text, offset + length

# --- FUNKCJE DO WYSYŁANIA ---

def get_handshake():
    """Tabela 4: Typ 3, Długość 2, Ver 0.1 (zgodnie z Twoim testem)"""
    payload = struct.pack(">BBB", 0, 1, 1)
    return struct.pack("!BH", TYPE_HANDSHAKE, len(payload)) + payload

def get_auth(user, password):
    """Tabela 5: Typ 4, User (string) + Pass (string)"""
    payload = encode_string(user) + encode_string(password)
    return struct.pack("!BH", TYPE_AUTH, len(payload)) + payload

def get_join_channel(my_username, target_channel):
    """
    my_username: "damian" (z GUI)
    target_channel: "#test@localhost"
    """
    # 1. Naprawa Nicku na damian@localhost
    if "@" not in my_username:
        full_user_address = f"{my_username}@localhost"
    
    # 3. dołącz
    JOIN_MODE = 0x01 
    
    payload = (
        encode_string(full_user_address) + 
        encode_string(target_channel) + 
        struct.pack("!B", JOIN_MODE)
    )
    
    # Nagłówek: Typ 0x07 (USERMODE)
    header = struct.pack("!BH", TYPE_USERMODE, len(payload))
    return header + payload


def get_message_packet(source, target, content):
    """Tabela 6: Typ 5, Wiadomość (Source, Target, Timestamp, Content)"""
    timestamp = int(time.time())
    payload = (
        encode_string(source) +
        encode_string(target) +
        struct.pack("!Q", timestamp) + 
        encode_string(content)
    )
    return struct.pack("!BH", TYPE_MESSAGE, len(payload)) + payload

# --- FUNKCJA DO ODBIERANIA ---
def parse_message(payload):
    offset = 0
    try:
        source, offset = decode_string(payload, offset)
        target, offset = decode_string(payload, offset)
        #  timestamp (8 bajtów)
        timestamp = struct.unpack_from("!Q", payload, offset)[0]
        offset += 8
        content, _ = decode_string(payload, offset)
        
        return {
            "source": source,
            "target": target,
            "content": content
        }
    except Exception as e:
        # błądy
        print(f"!!! BŁĄD PROTOKOŁU: {e} | Payload len: {len(payload)}")
        return None
    
# --- DODATKOWE PROTOKOŁY ---
def get_usermode_packet(user_address, channel_name, mode=0x01):
    # ( 'damian@localhost:9999' -> 'damian@localhost')
    clean_user = user_address.split(':')[0]
    clean_channel = channel_name.split(':')[0]

   
    payload = encode_string(clean_user) + encode_string(clean_channel) + struct.pack("!B", mode)
    
    header = struct.pack("!BH", TYPE_USERMODE, len(payload))
    return header + payload