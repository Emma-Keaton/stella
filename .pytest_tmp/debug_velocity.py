from core.radio.adsb import decode_velocity, _uint


def num_to_bits(value, width):
    return [(value >> (width - 1 - i)) & 1 for i in range(width)]


def bits_to_hex(bits):
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return f"{value:0{len(bits) // 4}x}"


rest = num_to_bits(1, 3) + [0] * 12 + num_to_bits(481, 10) + num_to_bits(41, 10) + [0] * 6
me = num_to_bits(19, 5) + rest
print("me bits:", len(me))
hexed = bits_to_hex(me)
print("hex:", hexed, "len:", len(hexed))
payload = bytes.fromhex(hexed.ljust(14, "0"))
print("payload bytes:", len(payload))
print("bit5..7:", _uint(payload, 5, 3), "| bit8:", _uint(payload, 8, 1))
print("ew:", _uint(payload, 15, 10), "ns:", _uint(payload, 25, 10))
print("record:", decode_velocity(payload))
