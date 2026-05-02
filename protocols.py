#gałąź main

# wsl
# cd ~/solec/cmd/daemon
# go run main.go

# wsl
# cd ~/solec
# ./tools/run.sh

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
    """Rozpakowuje payload typu Message (Tabela 6)"""
    offset = 0
    try:
        source, offset = decode_string(payload, offset)
        target, offset = decode_string(payload, offset)
        timestamp = struct.unpack_from("!Q", payload, offset)[0]
        offset += 8
        content, _ = decode_string(payload, offset)
        
        return {
            "source": source,
            "target": target,
            # "time": time.ctime(timestamp),
            "content": content
        }
    except Exception as e:
        print(f"Błąd dekodowania: {e}")
        return None
    
    # timestamk wyłączony bo nie działa Unixtimestamp na go ?