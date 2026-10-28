body = bytearray()
body += b"\x03\x03" + b"\xaa" * 32
body += bytes([0])
body += (2).to_bytes(2, "big") + b"\xc0\x2b"
body += bytes([1, 0])
extension = (0).to_bytes(2, "big") + (7).to_bytes(2, "big") + (5).to_bytes(2, "big") + bytes([0]) + (4).to_bytes(2, "big") + b"a.bc"
body += (len(extension)).to_bytes(2, "big") + extension

print("len:", len(body))
print("hex:", body.hex())
print("byte 34:", body[34], "byte 33:", body[33])
