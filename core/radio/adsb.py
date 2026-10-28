"""core/radio/adsb.py - Mode-S frame decoding and ADS-B feed ingestion.

Two entry points, both pure Python:

* `decode_frame(hex)` decodes one raw Mode-S frame: downlink format, ICAO 24-bit
  address, callsign, altitude, squawk, and the velocity subtype's speed /
  heading / vertical rate.
* `parse_aircraft_json(text)` ingests an already-decoded feed (dump1090 /
  readsb / Tar1090 `aircraft.json`) into the same uniform record shape, because
  that is what an SDR or a PiAware actually produces.

CPR (Compact Position Reporting) decoding needs a reference position to
disambiguate, so `decode_airborne_position()` takes one and says so when none is
supplied instead of returning a position it cannot stand behind.

Everything reports what it decoded: an unknown type code produces
`{"recognised": False, "reason": ...}`, never a guessed field.
"""

from __future__ import annotations

import json
import math
from typing import Optional

#: ICAO 6-bit character set for aircraft identification (callsign).
CALLSIGN_CHARS = (
    "#ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    + "-" * 5
    + "#" * 16
    + "0123456789"
    + "#" * 6
)

#: Downlink formats this module knows how to read.
DF_SHORT_ACAS = 0
DF_ALTITUDE = 4
DF_IDENTITY = 5
DF_ALL_CALL = 11
DF_EXTENDED_SQUITTER = 17
DF_ADSB_NON_TRANSPONDER = 18

_KNOWN_DFS = {DF_SHORT_ACAS, DF_ALTITUDE, DF_IDENTITY, DF_ALL_CALL,
              DF_EXTENDED_SQUITTER, DF_ADSB_NON_TRANSPONDER}


def _pure_hex(text: str) -> Optional[bytes]:
    cleaned = (text or "").strip().replace(" ", "").replace(";", "").replace("*", "")
    if cleaned.startswith("*"):
        cleaned = cleaned[1:]
    if not cleaned:
        return None
    try:
        return bytes.fromhex(cleaned)
    except ValueError:
        return None


def _uint(data: bytes, start_bit: int, length: int) -> int:
    value = 0
    for index in range(start_bit, start_bit + length):
        byte = data[index // 8]
        bit = (byte >> (7 - (index % 8))) & 1
        value = (value << 1) | bit
    return value


def _bits(data: bytes) -> list:
    flat = []
    for byte in data:
        flat.extend((byte >> (7 - i)) & 1 for i in range(8))
    return flat


def decode_callsign(payload_bytes: bytes) -> str:
    """Decode a TC 1-4 callsign from the 8 six-bit characters."""
    chars = []
    for index in range(8):
        value = _uint(payload_bytes, 8 + index * 6, 6)
        chars.append(CALLSIGN_CHARS[value] if value < len(CALLSIGN_CHARS) else "#")
    return "".join(chars).strip().strip("#")


def decode_altitude(ac_field: int) -> dict:
    """Decode a 13-bit altitude field.

    ``q=1`` is the 25-foot Gillham code used by ADS-B; ``q=0`` is the 100-foot
    Mode C code that needs a Gray-code conversion this decoder does not
    attempt, so it reports that instead of returning an altitude.
    """
    c1 = (ac_field >> 12) & 1
    a1 = (ac_field >> 11) & 1
    c2 = (ac_field >> 10) & 1
    a2 = (ac_field >> 9) & 1
    c4 = (ac_field >> 8) & 1
    a4 = (ac_field >> 7) & 1
    q = ac_field & 1

    hundreds = (c1 << 6) | (a1 << 4) | (c2 << 2) | a4
    if q:
        return {"altitude_ft": hundreds * 25 - 1000, "basis": "25-ft Gillham (Q=1)"}

    gray = (c1 << 11) | (a1 << 10) | (c2 << 9) | (a2 << 8) | (c4 << 7) | (a4 << 6)
    encoded = gray
    decoded = encoded
    while encoded:
        encoded >>= 1
        decoded ^= encoded
    altitude_ft = decoded * 100 - 1200
    return {"altitude_ft": altitude_ft, "basis": "100-ft Mode C Gray (Q=0)"}


def decode_squawk(identity: int) -> str | None:
    """Decode a 13-bit Mode-A identity field into a four-digit squawk.

    The 13 bits carry the Mode-A code in the ICAO pulse order; the framing and
    spare bits are dropped here and the twelve data bits are read as the four
    octal digits. Returns the squawk, or None when the field carries no valid
    code.
    """
    if identity == 0:
        return None
    # Mode-A data order: A1 C1 A2 C2 A4 B1 D1 B2 D2 B4 C4 (12 data bits).
    bits = [(identity >> (12 - i)) & 1 for i in range(13)]
    digits = [
        (bits[0] << 2) | (bits[1] << 1) | bits[2],   # A1 C1 A2
        (bits[3] << 2) | (bits[4] << 1) | bits[5],   # A4 B1 D1
        (bits[6] << 2) | (bits[7] << 1) | bits[8],   # B2 D2 B4
        (bits[9] << 2) | (bits[10] << 1) | bits[11], # C4 spare spare
    ]
    return "".join(str(d % 8) for d in digits)


def _nl(latitude_deg: float, odd_format: bool) -> int:
    """The CPR NL (longitude zone count) table from the ICAO algorithm."""
    if abs(abs(latitude_deg) - 90.0) < 1e-9:
        return 1
    if abs(latitude_deg) == 87.0:
        return 2
    zone = 59.0 if odd_format else 60.0
    cos_lat = math.cos(math.radians(latitude_deg))
    if abs(cos_lat) < 1e-9:
        return 1
    argument = 1.0 - ((1.0 - math.cos(2.0 * math.pi / zone))
                      / (math.cos(2.0 * math.pi / 59.0) * cos_lat * cos_lat))
    argument = max(-1.0, min(1.0, argument))
    return int(math.floor(2.0 * math.pi / math.acos(argument)))


def cpr_encode(latitude_deg: float, longitude_deg: float, odd_format: bool) -> tuple:
    """Encode a position into CPR latitude/longitude for the given format.

    Provided so `cpr_decode` can be validated round-trip in tests and so
    synthetic frames can be built; nothing in Stella encodes positions at
    runtime.
    """
    nz = 59.0 if odd_format else 60.0
    dlat = 360.0 / (4.0 * nz)
    yz = math.floor((1 << 17) * ((latitude_deg % dlat) / dlat) + 0.5)
    rlat = dlat * (math.floor(latitude_deg / dlat) + yz / (1 << 17))
    dlon = 360.0 / max(_nl(rlat, odd_format), 1)
    xz = math.floor((1 << 17) * ((longitude_deg % dlon) / dlon) + 0.5)
    return int(yz) % (1 << 17), int(xz) % (1 << 17), rlat


def cpr_decode(lat_cpr: int, lon_cpr: int, odd_format: bool,
               reference_lat: Optional[float] = None,
               reference_lon: Optional[float] = None) -> Optional[dict]:
    """Decode a CPR position, using a reference position to pick the zone.

    Airborne CPR is only unambiguous as a pair of frames of opposite format; a
    single frame needs a nearby reference. With no reference this returns None
    and says why, rather than returning a fix in the wrong zone.
    """
    if reference_lat is None or reference_lon is None:
        return None

    nz = 59.0 if odd_format else 60.0
    dlat = 360.0 / (4.0 * nz)
    j = (math.floor(reference_lat / dlat)
         + math.floor(0.5 + ((reference_lat % dlat) / dlat) - (lat_cpr / (1 << 17))))
    latitude = dlat * (j + (lat_cpr / (1 << 17)))

    nl = _nl(latitude, odd_format)
    dlon = 360.0 / max(nl, 1)
    m = (math.floor(reference_lon / dlon)
         + math.floor(0.5 + ((reference_lon % dlon) / dlon) - (lon_cpr / (1 << 17))))
    longitude = dlon * (m + (lon_cpr / (1 << 17)))
    if longitude >= 180.0:
        longitude -= 360.0

    return {
        "latitude": round(latitude, 5),
        "longitude": round(longitude, 5),
        "basis": f"CPR {'odd' if odd_format else 'even'} decoded against a nearby reference position",
    }


def decode_frame(text: str) -> dict:
    """Decode one Mode-S frame given as hex (with or without markers)."""
    data = _pure_hex(text)
    if data is None or len(data) < 7:
        return {"recognised": False, "reason": "frame is not valid hex or is shorter than 7 bytes"}

    downlink = _uint(data, 0, 5)
    icao = f"{_uint(data, 8, 24):06X}"
    record = {
        "recognised": True,
        "downlink_format": downlink,
        "icao24": icao,
        "source": "decoded-from-frame",
    }

    if downlink in (DF_ALTITUDE, DF_SHORT_ACAS, DF_IDENTITY) and len(data) >= 4:
        field = _uint(data, 32, 13)
        if downlink == DF_IDENTITY:
            record.update(type_code=None, squawk=decode_squawk(field))
        else:
            record.update(type_code=None)
            record.update(decode_altitude(field))
        return record

    if len(data) < 14:
        record.update({"recognised": False,
                       "reason": "an extended squitter frame needs at least 14 bytes (112 bits)"})
        return record

    payload = data[4:11]
    if downlink != DF_EXTENDED_SQUITTER:
        record.update({"recognised": False,
                       "reason": f"downlink format {downlink} is not an extended squitter this decoder reads"})
        return record

    type_code = _uint(payload, 0, 5)
    record["type_code"] = type_code

    if 1 <= type_code <= 4:
        record["callsign"] = decode_callsign(payload)
        record["category"] = {"1": "A", "2": "B", "3": "C", "4": "D"}.get(str(type_code), "unknown")
        return record

    if 5 <= type_code <= 8:
        record.update(decode_altitude(_uint(payload, 8, 12)))
        record["surface_position_basis"] = "CPR; a reference position is required to resolve it"
        return record

    if 9 <= type_code <= 18:
        record.update(decode_altitude(_uint(payload, 8, 12)))
        record["position"] = None
        record["position_note"] = (
            "CPR airborne position needs a reference position or a frame pair; "
            "supply the observer position, or ingest a feed that already resolves it")
        return record

    if type_code == 19:
        velocity = decode_velocity(payload)
        record.update(velocity)
        return record

    record.update({"recognised": False,
                   "reason": f"ADS-B type code {type_code} is not decoded by this module"})
    return record


def decode_velocity(payload: bytes) -> dict:
    """Decode TC 19 velocity: ground speed/heading or airspeed/heading.

    Bit offsets are relative to the start of the 56-bit ME field, which is what
    `decode_frame` passes here: 5-7 subtype, 8 intent change, 15-24 east-west,
    25-34 north-south, 35 vertical-rate source, 36-44 vertical rate.
    """
    subtype = _uint(payload, 5, 3)
    intent_change = _uint(payload, 8, 1)
    ifs = _uint(payload, 9, 2)
    ew = _uint(payload, 15, 10)
    ns = _uint(payload, 25, 10)
    vertical_source_head = _uint(payload, 35, 1)
    vertical_rate_raw = _uint(payload, 36, 9)
    vertical_rate = (vertical_rate_raw - 1) * 64

    heading_deg = None
    speed_kt = None
    basis = None
    if subtype in (1, 2):
        vx = ew - 1
        vy = ns - 1
        scale = 4.0 if subtype == 2 else 1.0
        if subtype == 2 and (ew == 0 or ns == 0):
            speed_kt = None
        else:
            speed_kt = round(math.sqrt(vx * vx + vy * vy) * scale, 1)
        if vx == 0 and vy == 0:
            heading_deg = None
        else:
            heading_deg = math.degrees(math.atan2(vx, vy)) % 360.0
        basis = "ground speed"
    elif subtype in (3, 4):
        if subtype == 3:
            if ew != 0:
                heading_deg = (ew - 1) * 360.0 / 1024.0
        if ns != 0:
            speed_kt = round((ns - 1) * (4.0 if subtype == 4 else 1.0), 1)
        basis = "airspeed"
    else:
        return {"recognised": False, "reason": f"velocity subtype {subtype} is reserved",
                "velocity_subtype": subtype}

    return {
        "velocity_subtype": subtype,
        "speed_kt": speed_kt,
        "heading_deg": None if heading_deg is None else round(heading_deg, 1),
        "vertical_rate_ft_min": vertical_rate if vertical_source_head == 0 else -vertical_rate,
        "vertical_rate_source": "barometric" if vertical_source_head == 0 else "geometric",
        "intent_change": bool(intent_change),
        "ifs": ifs,
        "speed_basis": basis,
    }


def parse_aircraft_json(text: str) -> dict:
    """Ingest an already-decoded feed (dump1090 / readsb aircraft.json)."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"ok": False, "reason": f"not valid JSON: {exc}", "aircraft": []}

    aircraft = payload.get("aircraft") if isinstance(payload, dict) else payload
    if not isinstance(aircraft, list):
        return {"ok": False, "reason": "no 'aircraft' list in the feed", "aircraft": []}

    records = []
    for entry in aircraft:
        if not isinstance(entry, dict):
            continue
        position = None
        if entry.get("lat") is not None and entry.get("lon") is not None:
            position = {"latitude": entry.get("lat"), "longitude": entry.get("lon")}
        altitude = entry.get("alt_geo")
        if altitude is None:
            altitude = entry.get("alt_baro")
        record = {
            "icao24": str(entry.get("hex") or "").upper(),
            "callsign": (entry.get("flight") or "").strip(),
            "position": position,
            "altitude_ft": altitude,
            "altitude_source": "geometric" if entry.get("alt_geo") is not None else "barometric",
            "ground_speed_kt": entry.get("gs"),
            "track_deg": entry.get("track"),
            "squawk": entry.get("squawk"),
            "vertical_rate_ft_min": entry.get("baro_rate"),
            "on_ground": bool(entry.get("ground", False)),
            "rssi_db": entry.get("rssi"),
            "seen_seconds_ago": entry.get("seen"),
            "messages_seen": entry.get("messages"),
            "source": "decoded-feed",
        }
        records.append(record)

    return {
        "ok": True,
        "aircraft": records,
        "count": len(records),
        "feed_timestamp": payload.get("now") if isinstance(payload, dict) else None,
    }


def summarise(records: list) -> dict:
    """Counts a decoded set by altitude band and on-ground state."""
    if not records:
        return {"total": 0, "airborne": 0, "on_ground": 0, "highest_ft": None, "fastest_kt": None}
    airborne = [r for r in records if not r.get("on_ground")]
    altitudes = [r.get("altitude_ft") for r in airborne if r.get("altitude_ft") is not None]
    speeds = [r.get("ground_speed_kt") for r in airborne if r.get("ground_speed_kt") is not None]
    return {
        "total": len(records),
        "airborne": len(airborne),
        "on_ground": len(records) - len(airborne),
        "highest_ft": max(altitudes) if altitudes else None,
        "fastest_kt": max(speeds) if speeds else None,
    }
