#gałąź testowa

# wsl
# cd ~/solec/cmd/daemon -test
# go run main.go

# user_set damian@localhost valid

# perm_set damian@localhost user1@localhost 1 1
# perm_set user1@localhost dmaian@localhost 1 1

import struct
import time

# login: damian@rctt.net    damian  d2
# hasło: pgcBJ8qY78JM
# połączenie: rctt.net:9999 domyślnie
SERVER_DOMAIN = "rctt.net" # wartość wstepna

# --- KONFIGURACJA TYPÓW  ---#

TYPE_SUCCESS   = 0x01
TYPE_ERROR     = 0x02
TYPE_HANDSHAKE = 0x03
TYPE_AUTH      = 0x04
TYPE_MESSAGE   = 0x05

TYPE_USERMODE  = 0x07
TYPE_HISTORY = 0x08
TYPE_LIST     = 0x09  
TYPE_LISTITEM = 0x10 

# String: 2 bajty długości + dane UTF-8
def encode_string(s):
    
    encoded = s.encode("utf-8")
    return struct.pack("!H", len(encoded)) + encoded

# Czytania stringów z payloadu, zwraca (string, nowy_offset)
def decode_string(payload, offset):
    length = struct.unpack_from("!H", payload, offset)[0]
    offset += 2
    text = payload[offset : offset + length].decode("utf-8")
    return text, offset + length

# --- FUNKCJE DO WYSYŁANIA ---

# Handshake: Typ 3, Długość 2, Ver 0.1 
def get_handshake():
    payload = struct.pack(">BBB", 0, 1, 1)
    return struct.pack("!BH", TYPE_HANDSHAKE, len(payload)) + payload

# Autoryzacja: Typ 4, User (string) + Pass (string)
def get_auth(user, password):
    payload = encode_string(user) + encode_string(password)
    return struct.pack("!BH", TYPE_AUTH, len(payload)) + payload

# Dołączanie do kanału. UserMode: Typ 7, User (string) + Channel (string) + Mode (1 byte)
def get_join_channel(my_username, target_channel):
    # Czyszczenie użytkownika (odcina ewentualny port i sprawdza czy jest @SERVER_DOMAIN)
    clean_user = my_username.split(':')[0].strip()
    if "@" not in clean_user:
        clean_user = f"{clean_user}@{SERVER_DOMAIN}"

    # Kanał: Zostawia CAŁY adres, dba tylko o to, żeby miał '#' na początku
    clean_room = target_channel.strip()
    if not clean_room.startswith('#'):
        clean_room = f"#{clean_room}"
    if "@" not in clean_room:
        clean_room = f"{clean_room}@{SERVER_DOMAIN}"
    
    # Mode 0x01 = join
    mode = 0x01 
    
    # Budowa payloadu
    payload = (
        encode_string(clean_user) + 
        encode_string(clean_room) + 
        struct.pack("!B", mode)
    )
    
    header = struct.pack("!BH", TYPE_USERMODE, len(payload))
    
    # print(f"DEBUG JOIN (Pełny): User='{clean_user}', Room='{clean_room}'")
    return header + payload

# Opuszczanie kanału. UserMode: Typ 7, User (string) + Channel (string) + Mode (1 byte)
def get_leave_channel(my_username, target_channel):
    clean_user = my_username.split(':')[0].strip()
    if "@" not in clean_user:
        clean_user = f"{clean_user}@{SERVER_DOMAIN}"

    clean_room = target_channel.strip()
    if not clean_room.startswith('#'):
        clean_room = f"#{clean_room}"
    if "@" not in clean_room:
        clean_room = f"{clean_room}@{SERVER_DOMAIN}"
    
    # Mode 0x00 = leave
    mode = 0x00 
    
    payload = (
        encode_string(clean_user) + 
        encode_string(clean_room) + 
        struct.pack("!B", mode)
    )
    
    header = struct.pack("!BH", TYPE_USERMODE, len(payload))
    return header + payload
    

# Tworzenie pakietu wiadomości. Message: Typ 5, Source (string) + Target (string) + Timestamp (int64) + Content (string)
def get_message_packet(source, target, content):
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
        # Błędy
        print(f"!!! BŁĄD PROTOKOŁU: {e} | Payload len: {len(payload)}")
        return None
    
# --- DODATKOWE PROTOKOŁY ---

# Tworzenie pakietu trybu użytkownika. UserMode: Typ 7, User (string) + Channel (string) + Mode (1 byte)
def get_usermode_packet(user_address, channel_name, mode=0x01):
    # ( 'damian@localhost:9999' -> 'damian@localhost')
    clean_user = user_address.split(':')[0]
    clean_channel = channel_name.split(':')[0]
    payload = encode_string(clean_user) + encode_string(clean_channel) + struct.pack("!B", mode)
    header = struct.pack("!BH", TYPE_USERMODE, len(payload))
    return header + payload

# Pobieranie historii kanału. History: Typ 8, Channel (string) + Since (int64) + Count (int64) + Offset (int64)
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

def get_list_packet(count=100, offset=0):
    
    payload = (
        struct.pack("!q", count) +
        struct.pack("!q", offset)
    )
    header = struct.pack("!BH", TYPE_LIST, len(payload))
    return header + payload

def parse_list_item(payload):
    
    try:
        address, _ = decode_string(payload, 0)
        return address.strip()
    except Exception as e:
        print(f"!!! BŁĄD DEKODOWANIA LISTITEM: {e}")
        return None