from core.net.pcap import parse_tls_client_hello


def u16(value):
    return value.to_bytes(2, "big")


body = bytearray()
body += b"\x03\x03" + b"\xaa" * 32
body += bytes([0])
body += u16(2) + b"\xc0\x2b"
body += bytes([1, 0])
extension = u16(0) + u16(7) + u16(5) + bytes([0]) + u16(4) + b"a.bc"
body += u16(len(extension)) + extension
record = b"\x01" + len(body).to_bytes(3, "big") + body
payload = b"\x16\x03\x01" + u16(len(record)) + record

print("payload len:", len(payload))
print("body len:", len(body))
parsed = parse_tls_client_hello(payload)
print("parsed:", parsed)

# Walk the parser by hand to find where it stops.
b = payload[5:]
print("version:", b[:2].hex(), "random:", len(b[2:34]))
offset = 2 + 32
print("session id len at", offset, "=", b[offset])
offset += 1 + b[offset]
print("after session id:", offset, "cipher len:", int.from_bytes(b[offset:offset + 2], "big"))
cipher_length = int.from_bytes(b[offset:offset + 2], "big")
offset += 2 + cipher_length
print("after ciphers:", offset, "compression len:", b[offset])
offset += 1 + b[offset]
print("after compression:", offset, "extensions len:", int.from_bytes(b[offset:offset + 2], "big"))
