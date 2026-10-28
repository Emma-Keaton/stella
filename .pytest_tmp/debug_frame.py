from core.radio.adsb import decode_frame


def num_to_bits(value, width):
    return [(value >> (width - 1 - i)) & 1 for i in range(width)]


def bits_to_hex(bits):
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return f"{value:0{(len(bits) + 3) // 4}x}"


def adsb_frame(type_code, rest_bits):
    bits = [0, 1, 0, 0, 1] + [0, 0, 0] + num_to_bits(0x4840D6, 24)
    bits += num_to_bits(type_code, 5) + rest_bits + [0] * 24
    assert len(bits) == 112, len(bits)
    return bits_to_hex(bits)


subtype, intent_change, reserved = 1, 0, 0
ew, ns = 481, 41
vrate_source, vrate = 0, 300
rest = num_to_bits(subtype, 3) + num_to_bits(intent_change, 1) + num_to_bits(reserved, 6)
rest += num_to_bits(ew, 10) + num_to_bits(ns, 10)
rest += num_to_bits(vrate_source, 1) + num_to_bits(vrate, 9)
rest += [0] * 11
frame = adsb_frame(19, rest)
print("hex bytes:", len(frame) // 2)
print("record:", decode_frame(frame))
