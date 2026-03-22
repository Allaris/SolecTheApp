import struct

VERSION = 2
HANDSHAKE = struct.pack(">BB", 0x01, VERSION)
PING = struct.pack(">B", 0x02)