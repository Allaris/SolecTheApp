#gałąź testowa

# wsl
# cd ~/solec/cmd/daemon -test
# go run main.go

# user_set damian@localhost valid

# perm_set damian@localhost user1@localhost 1 1
# perm_set user1@localhost dmaian@localhost 1 1

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
TYPE_HISTORY = 0x08

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
    Tworzy pakiet JOIN (0x07).
    User: damian@localhost (pełny adres bez portu)
    Channel: #test@localhost (pełny adres kanału z płotkiem i domeną)
    """
    # 1. Czyszczenie użytkownika (odcinamy ewentualny port i pilnujemy @localhost)
    clean_user = my_username.split(':')[0].strip()
    if "@" not in clean_user:
        clean_user = f"{clean_user}@localhost"

    # 2. Kanał: Zostawiamy CAŁY adres, dbamy tylko o to, żeby miał '#' na początku
    clean_room = target_channel.strip()
    if not clean_room.startswith('#'):
        clean_room = f"#{clean_room}"
        
    # Pilnujemy, żeby kanał też miał domenę @localhost na końcu
    if "@" not in clean_room:
        clean_room = f"{clean_room}@localhost"
    
    # 3. Tryb: 0x01 (in_channel) zgodnie z Tabelą 10
    mode = 0x01 
    
    # 4. Budowa payloadu
    payload = (
        encode_string(clean_user) + 
        encode_string(clean_room) + 
        struct.pack("!B", mode)
    )
    
    header = struct.pack("!BH", TYPE_USERMODE, len(payload))
    
    print(f"DEBUG JOIN (Pełny): User='{clean_user}', Room='{clean_room}'")
    return header + payload


def get_leave_channel(my_username, target_channel):
    """
    Tworzy pakiet LEAVE (0x07) z pełnymi adresami.
    """
    clean_user = my_username.split(':')[0].strip()
    if "@" not in clean_user:
        clean_user = f"{clean_user}@localhost"

    # Zostawiamy pełny adres kanału
    clean_room = target_channel.strip()
    if not clean_room.startswith('#'):
        clean_room = f"#{clean_room}"
    if "@" not in clean_room:
        clean_room = f"{clean_room}@localhost"
    
    # Mode 0x00 = leave
    mode = 0x00 
    
    payload = (
        encode_string(clean_user) + 
        encode_string(clean_room) + 
        struct.pack("!B", mode)
    )
    
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
            "timestamp": timestamp,
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

# Historia czatu
def get_history_packet(channel_address, since_timestamp, count=100, offset=0):
    #  payload: string (2 bajty długości + dane) + 3x int64 (Q czyli 8 bajtów)
    payload = (
        encode_string(channel_address) +
        struct.pack("!q", since_timestamp) +  # q = int64 (signed)
        struct.pack("!q", count) +
        struct.pack("!q", offset)
    )
    
    header = struct.pack("!BH", TYPE_HISTORY, len(payload))
    return header + payload