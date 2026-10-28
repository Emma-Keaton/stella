"""core/security/handshake.py - read a capture and say what it actually holds.

A `.cap`/`.pcap`/`.pcapng` file is only useful if it contains a complete
four-way handshake (or a PMKID), and a crack is a waste of GPU-hours if it does
not. This module answers that question from the capture itself:

* EAPOL frames (ethertype `0x888e`) mark the handshake; their message numbers
  say whether messages 1-4 are present
* a PMKID appears in message 1's RSN parameter as a 16-byte KeyID, and needs no
  client at all
* the AP BSSID and the client MAC are read from the frames, so a crack can
  target one access point instead of everything in the file

Classic pcap is parsed by `core.net.pcap`; the next-generation pcapng is reported
as unsupported by this reader (convert it, or use `tshark` to extract EAPOL),
because a half-parsed capture is worse than a clear "not read".
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

EAPOL_ETHERTYPE = 0x888E
MIN_HANDSHAKE_MESSAGES = 2


def inspects_file(path: str) -> dict:
    """Validate one capture file: what it holds, and whether it can be cracked."""
    from core.security.tools import available as tool_available

    file_path = Path(path).expanduser()
    if not file_path.exists():
        return {"ok": False, "reason": f"{file_path} does not exist on this machine"}
    if not file_path.is_file():
        return {"ok": False, "reason": f"{file_path} is not a file"}

    size = file_path.stat().st_size
    if size <= 24:
        return {"ok": False, "reason": f"{file_path} is too small to be a capture ({size} bytes)"}

    raw = file_path.read_bytes()

    magic = raw[:4]
    if magic in (b"\x0a\x0d\x0d\x0a", b"\x0d\x0a\x0d\x0a"):
        return {"ok": False, "reason": (
            "that is a pcapng capture. This reader handles classic pcap; convert it with "
            "`tshark -r in.pcapng -w out.pcap` or `editcap`, or use a tool that reads pcapng.")}
    if magic[:4] in (b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4", b"\x4d\x3c\xb2\xa1",
                     b"\xa1\xb2\x3c\x4d"):
        pass
    else:
        hccapx = _inspect_hccapx(raw)
        if hccapx is not None:
            return {"ok": True, "format": "hccapx", "kind": hccapx["kind"],
                    "ap_mac": hccapx["ap_mac"], "client_mac": hccapx["client_mac"],
                    "crackable": True, "handshake_messages": hccapx["messages"],
                    "note": hccapx["note"]}
        hc22000 = _inspect_hc22000(raw)
        if hc22000 is not None:
            return {"ok": True, "format": "hc22000", "kind": hc22000["kind"],
                    "crackable": True, "handshake_messages": hc22000["messages"],
                    "note": hc22000["note"],
                    "tools": tool_available(["hashcat", "john"])}
        return {"ok": False, "reason": (
            f"{file_path.name} is not a capture this reader understands (magic "
            f"{magic.hex()}). Expected classic pcap, hccapx, or hc22000.")}

    from core.net.pcap import read_pcap

    parsed = read_pcap(raw)
    if not parsed.get("ok"):
        return {"ok": False, "reason": parsed.get("reason", "the capture could not be parsed")}

    eapol = _collect_eapol(raw)
    pmkid = eapol.get("pmkid")
    messages = sorted(eapol.get("messages") or [])
    ap_mac = eapol.get("ap_mac")
    clients = sorted(eapol.get("clients") or [])

    if pmkid:
        return {
            "ok": True,
            "format": "pcap",
            "kind": "pmkid",
            "ap_mac": ap_mac,
            "client_mac": None,
            "pmkid": pmkid,
            "crackable": True,
            "handshake_messages": [1],
            "note": ("The capture holds a PMKID from the first message, so it can be cracked "
                     "without any client having been connected."),
            "eapol_frame_count": eapol.get("count", 0),
        }

    if len(messages) >= MIN_HANDSHAKE_MESSAGES:
        complete = len(messages) == 4
        return {
            "ok": True,
            "format": "pcap",
            "kind": "wpa-handshake",
            "ap_mac": ap_mac,
            "client_mac": clients[0] if clients else None,
            "client_macs": clients,
            "crackable": True,
            "handshake_messages": messages,
            "handshake_complete": complete,
            "note": ("The capture holds all four handshake messages." if complete else
                     f"The capture holds messages {messages}; a crack may still succeed with a "
                     "partial handshake, but a full four-way capture cracks reliably."),
            "eapol_frame_count": eapol.get("count", 0),
        }

    return {
        "ok": False,
        "format": "pcap",
        "kind": "no-handshake",
        "crackable": False,
        "eapol_frame_count": eapol.get("count", 0),
        "reason": (f"the capture holds {eapol.get('count', 0)} EAPOL frames and messages "
                   f"{messages or 'none'}, which is not enough to crack. Recapture: deauthenticate "
                   "one client and wait for the re-association to land in the file."),
    }


def _collect_eapol(raw: bytes) -> dict:
    """Walk the pcap for EAPOL frames and read their message numbers."""
    messages: set = set()
    clients: set = set()
    ap_mac: Optional[str] = None
    pmkid: Optional[str] = None
    count = 0

    offset = 24
    endian = ">" if raw[:4] in (b"\xa1\xb2\xc3\xd4", b"\x4d\x3c\xb2\xa1") else "<"
    import struct

    while offset + 16 <= len(raw):
        _ts_sec, _ts_usec, cap_length, _original = struct.unpack_from(endian + "IIII",
                                                                      raw, offset)
        offset += 16
        if cap_length <= 0 or offset + cap_length > len(raw):
            break
        frame = raw[offset:offset + cap_length]
        offset += cap_length

        if len(frame) < 14:
            continue
        ethertype = int.from_bytes(frame[12:14], "big")
        if ethertype == 0x8100 and len(frame) >= 18:
            ethertype = int.from_bytes(frame[16:18], "big")
            frame = frame[20:]
        if ethertype != EAPOL_ETHERTYPE:
            continue

        destination = _mac(frame[0:6])
        source = _mac(frame[6:12])
        eapol_payload = frame[14:]
        if len(eapol_payload) < 4:
            continue
        count += 1
        key_type = eapol_payload[1]
        if key_type != 2:                       # 2 = RSN (WPA2/3)
            continue
        key_information = int.from_bytes(eapol_payload[2:4], "big")
        message_number = ((key_information >> 1) & 0x3) + 1
        messages.add(message_number)

        if ap_mac is None:
            ap_mac = destination if destination != destination else destination
        if message_number == 2:
            clients.add(source)
            ap_mac = destination
        elif message_number == 3:
            clients.add(source if source != destination else destination)
            ap_mac = destination if destination != destination else destination
        else:
            clients.add(destination)
            clients.add(source)

        if pmkid is None and message_number == 1:
            found = _pmkid_from_message_1(eapol_payload)
            if found:
                pmkid = found
                ap_mac = source if ap_mac is None else ap_mac

    return {"messages": messages, "clients": clients - {ap_mac or ""},
            "ap_mac": ap_mac, "pmkid": pmkid, "count": count}


def _pmkid_from_message_1(payload: bytes) -> Optional[str]:
    """Read the RSN KeyID (PMKID) from a handshake message 1, if present."""
    if len(payload) < 97:
        return None
    key_data_length = int.from_bytes(payload[93:95], "big")
    if key_data_length == 0:
        return None
    key_data = payload[95:95 + key_data_length]
    cursor = 0
    while cursor + 4 <= len(key_data):
        tag_id = int.from_bytes(key_data[cursor:cursor + 2], "big")
        tag_length = int.from_bytes(key_data[cursor + 2:cursor + 4], "big")
        body = key_data[cursor + 4:cursor + 4 + tag_length]
        if tag_id == 221 and len(body) >= 20 and body[:4] == b"\x00\x0f\xac\x04":
            return body[4:20].hex()
        cursor += 4 + tag_length
    return None


def _mac(raw: bytes) -> str:
    return ":".join(f"{byte:02x}" for byte in raw[:6])


def _inspect_hccapx(raw: bytes) -> Optional[dict]:
    """Read the header of an hccapx file, when it is one."""
    if len(raw) < 393 or not raw.endswith(b"\x00" * 32):
        return None
    signature = int.from_bytes(raw[4:8], "big")
    if signature != 393:
        return None
    ap_mac = _mac(raw[15:21])
    client_mac = _mac(raw[25:31])
    messages = []
    if raw[146] & 0x01:
        messages.append(1)
    if raw[146] & 0x02:
        messages.append(2)
    if raw[146] & 0x80:
        messages.append(3)
    if raw[146] & 0x08:
        messages.append(4)
    return {"kind": "wpa-handshake", "ap_mac": ap_mac, "client_mac": client_mac,
            "messages": messages,
            "note": "An hccapx file holds a single AP/client pair; message availability is read from its message-pair bitmap."}


def _inspect_hc22000(raw: bytes) -> Optional[dict]:
    if b"WPA*" in raw[:64]:
        return {"kind": "hc22000 line", "messages": [1, 2],
                "note": "A hash-line file; each line is one hash in hashcat's WPA format."}
    if b"PMKID*" in raw[:64]:
        return {"kind": "pmkid", "messages": [1],
                "note": "A PMKID hash line."}
    return None


def summarise(validation: dict) -> str:
    """One honest sentence about a capture, for the summary line."""
    if not validation.get("ok"):
        return f"Capture not usable: {validation.get('reason', 'unknown reason')}"
    kind = validation.get("kind")
    if kind == "pmkid":
        return (f"PMKID from AP {validation.get('ap_mac')} - crackable with no client, "
                f"hashcat mode 22000.")
    if kind == "wpa-handshake":
        complete = "all four messages" if validation.get("handshake_complete") else \
            f"messages {validation.get('handshake_messages')}"
        return (f"WPA handshake with {complete} between AP {validation.get('ap_mac')} and "
                f"client {validation.get('client_mac')} - crackable, hashcat mode 22000.")
    return f"Capture holds {kind}."
