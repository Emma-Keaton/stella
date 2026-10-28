"""core/net/pcap.py - read classic pcap and pcapng files, in pure Python.

Reads a capture the user already has: the classic 24-byte pcap header, the
per-packet record headers, and for Ethernet and Linux-cooked links the IPv4/IPv6
and TCP/UDP layers, then pulls out the things a passive review looks for - DNS
queries, HTTP requests with their Host header, plaintext credentials in an
Authorization header, and TLS ClientHello server names.

It never opens a live interface, needs no root, and never puts the NIC into
promiscuous mode: a capture file is the input, and nothing outside it is
touched. As with every other decoder here, a section it cannot parse is
reported as skipped rather than guessed at.
"""

from __future__ import annotations

import struct
from typing import Optional

PCAP_MAGIC_NATIVE = 0xA1B2C3D4
PCAP_MAGIC_SWAPPED = 0xD4C3B2A1
PCAP_MAGIC_NANO_NATIVE = 0xA1B23C4D
PCAP_MAGIC_NANO_SWAPPED = 0x4D3CB2A1
PCAPNG_MAGIC = 0x0A0D0D0A

LINKTYPE_ETHERNET = 1
LINKTYPE_LINUX_SLL = 113
LINKTYPE_RAW = 101
LINKTYPE_NULL = 0

_MAX_PACKETS = 200000


class PcapError(ValueError):
    """Raised when the file is not a capture this reader understands."""


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from(">H", data, offset)[0]


def sniff_pcap(data: bytes) -> dict:
    """Identify the capture flavour without reading any packet."""
    if len(data) < 16:
        return {"ok": False, "reason": "the file is too short to be a capture"}
    magic = _u32(data, 0)
    if magic == PCAPNG_MAGIC:
        return {"ok": True, "format": "pcapng"}
    for name, value in (
        ("pcap-big-endian", PCAP_MAGIC_NATIVE), ("pcap-little-endian", PCAP_MAGIC_SWAPPED),
        ("pcap-nanosecond", PCAP_MAGIC_NANO_NATIVE), ("pcap-nanosecond-swapped", PCAP_MAGIC_NANO_SWAPPED),
    ):
        if magic == value:
            return {"ok": True, "format": name}
    if magic == 0x0A0D0D0A:
        return {"ok": True, "format": "pcapng"}
    return {"ok": False, "reason": "no pcap magic number found; this is not a classic capture"}


def _parse_pcap_header(data: bytes) -> dict:
    magic = _u32(data, 0)
    if magic in (PCAP_MAGIC_SWAPPED, PCAP_MAGIC_NANO_SWAPPED):
        endian = "<"
    else:
        endian = ">"
    version_major, version_minor, _thiszone, _sigfigs, _snaplen, linktype = struct.unpack_from(
        endian + "HHiIII", data, 4)
    return {
        "endian": endian,
        "version": f"{version_major}.{version_minor}",
        "snaplen": _snaplen,
        "linktype": linktype,
        "nanosecond": magic in (PCAP_MAGIC_NANO_NATIVE, PCAP_MAGIC_NANO_SWAPPED),
    }


def _iter_classic_packets(data: bytes):
    header = _parse_pcap_header(data)
    endian = header["endian"]
    offset = 24
    total = len(data)
    while offset + 16 <= total:
        ts_sec, ts_usec, cap_length, original_length = struct.unpack_from(
            endian + "IIII", data, offset)
        offset += 16
        if cap_length <= 0 or offset + cap_length > total:
            yield {"skipped": True, "reason": "truncated packet record"}
            return
        packet = data[offset:offset + cap_length]
        offset += cap_length
        yield {
            "timestamp": ts_sec + ts_usec / 1e9,
            "length": original_length,
            "captured": cap_length,
            "data": packet,
        }


def read_pcap(data: bytes) -> dict:
    """Parse a classic pcap capture and summarise what is in it."""
    sniffed = sniff_pcap(data)
    if not sniffed.get("ok"):
        return {"ok": False, "reason": sniffed.get("reason"), "packets": []}
    if sniffed["format"] == "pcapng":
        return {
            "ok": False,
            "reason": "pcapng (the next-generation format) is not read by this parser; save or convert the capture as classic pcap",
            "packets": [],
        }

    header = _parse_pcap_header(data)
    summary: dict = {
        "packets": 0,
        "truncated": 0,
        "ipv4": 0,
        "ipv6": 0,
        "tcp": 0,
        "udp": 0,
        "other_transport": 0,
        "dns_queries": [],
        "http_requests": [],
        "plaintext_credentials": [],
        "tls_server_names": [],
        "unknown_link_types": 0,
        "linktype": header["linktype"],
    }
    records: list = []

    for index, record in enumerate(_iter_classic_packets(data)):
        if record.get("skipped"):
            summary["truncated"] += 1
            continue
        if index >= _MAX_PACKETS:
            summary["note"] = f"stopped after {_MAX_PACKETS} packets"
            break

        summary["packets"] += 1
        parsed = _parse_link_layer(record["data"], header["linktype"], record["timestamp"])
        if parsed is None:
            summary["unknown_link_types"] += 1
            continue

        if parsed["ip_version"] == 4:
            summary["ipv4"] += 1
        else:
            summary["ipv6"] += 1

        protocol = parsed["protocol"]
        payload = parsed["payload"]
        if protocol == 6:
            summary["tcp"] += 1
            segment = _parse_tcp(payload)
            if segment is None:
                continue
            records.append({"src": parsed["src"], "dst": parsed["dst"],
                            "protocol": "tcp", "src_port": segment["src_port"],
                            "dst_port": segment["dst_port"], "flags": segment["flags"]})
            _inspect_tcp_payload(parsed, segment, summary)
        elif protocol == 17:
            summary["udp"] += 1
            datagram = _parse_udp(payload)
            if datagram is None:
                continue
            records.append({"src": parsed["src"], "dst": parsed["dst"], "protocol": "udp",
                            "src_port": datagram["src_port"],
                            "dst_port": datagram["dst_port"]})
            _inspect_udp_payload(parsed, datagram, summary)
        else:
            summary["other_transport"] += 1

    return {"ok": True, "packets": records, "summary": summary}


def _parse_tcp(payload: bytes) -> Optional[dict]:
    if len(payload) < 20:
        return None
    src_port = _u16(payload, 0)
    dst_port = _u16(payload, 2)
    data_offset = (payload[12] >> 4) * 4
    flags = payload[13]
    if data_offset < 20 or data_offset > len(payload):
        return None
    return {"src_port": src_port, "dst_port": dst_port, "flags": flags,
            "payload": payload[data_offset:]}


def _parse_udp(payload: bytes) -> Optional[dict]:
    if len(payload) < 8:
        return None
    return {"src_port": _u16(payload, 0), "dst_port": _u16(payload, 2),
            "length": _u16(payload, 4), "payload": payload[8:]}


def _inspect_tcp_payload(parsed: dict, segment: dict, summary: dict) -> None:
    body = segment["payload"]
    if not body:
        return
    ports = (segment["src_port"], segment["dst_port"])
    if 53 in ports:
        query = parse_dns(body)
        if query and len(summary["dns_queries"]) < 200:
            summary["dns_queries"].append({**query, "from": parsed["src"], "to": parsed["dst"]})
        return
    if 443 in ports:
        hello = parse_tls_client_hello(body)
        if hello and hello.get("server_name") and len(summary["tls_server_names"]) < 200:
            summary["tls_server_names"].append({**hello, "from": parsed["src"]})
        return
    if 80 in ports:
        request = parse_http_request(body)
        if request and len(summary["http_requests"]) < 200:
            summary["http_requests"].append({**request, "from": parsed["src"], "to": parsed["dst"]})
        credential = _basic_auth(body)
        if credential and len(summary["plaintext_credentials"]) < 50:
            summary["plaintext_credentials"].append({**credential, "from": parsed["src"]})
        return
    for port, kind in ((25, "smtp"), (110, "pop3"), (143, "imap")):
        if port in ports:
            credential = _mail_credentials(body, kind)
            if credential and len(summary["plaintext_credentials"]) < 50:
                summary["plaintext_credentials"].append({**credential, "from": parsed["src"],
                                                         "service": kind})
            return


def _inspect_udp_payload(parsed: dict, datagram: dict, summary: dict) -> None:
    if 53 in (datagram["src_port"], datagram["dst_port"]):
        query = parse_dns(datagram["payload"])
        if query and len(summary["dns_queries"]) < 200:
            summary["dns_queries"].append({**query, "from": parsed["src"], "to": parsed["dst"]})


def parse_http_request(payload: bytes) -> Optional[dict]:
    """Read the method, path and Host from an HTTP request payload."""
    text = payload[:2048].decode("ascii", errors="replace")
    lines = text.split("\r\n")
    if not lines:
        return None
    request_line = lines[0].strip()
    parts = request_line.split(" ")
    if len(parts) < 3 or not parts[2].startswith("HTTP/"):
        return None
    headers: dict = {}
    for line in lines[1:]:
        if not line.strip():
            break
        if ":" in line:
            name, _, value = line.partition(":")
            headers[name.strip().lower()] = value.strip()
    return {"method": parts[0], "path": parts[1], "host": headers.get("host"),
            "user_agent": headers.get("user-agent")}


def _basic_auth(payload: bytes) -> Optional[dict]:
    text = payload[:2048].decode("ascii", errors="replace")
    for line in text.split("\r\n"):
        if line.lower().startswith("authorization:"):
            scheme = line.split(":", 1)[1].strip()
            if scheme.lower().startswith("basic"):
                return {"scheme": "basic",
                        "note": "an HTTP Basic Authorization header was sent in the clear"}
    return None


def _mail_credentials(payload: bytes, service: str) -> Optional[dict]:
    text = payload[:512].decode("ascii", errors="replace")
    for line in text.split("\r\n"):
        upper = line.strip().upper()
        if upper.startswith(("AUTH LOGIN", "USER ", "PASS ")):
            return {"scheme": service, "line_prefix": line.strip()[:24],
                    "note": f"a {service.upper()} credential exchange is visible in the clear"}
    return None


def _parse_link_layer(packet: bytes, linktype: int, timestamp: float) -> Optional[dict]:
    if linktype == LINKTYPE_ETHERNET:
        if len(packet) < 14:
            return None
        ethertype = _u16(packet, 12)
        payload = packet[14:]
        if ethertype == 0x8100 and len(payload) >= 4:
            ethertype = _u16(payload, 2)
            payload = payload[4:]
    elif linktype == LINKTYPE_LINUX_SLL:
        if len(packet) < 16:
            return None
        ethertype = _u16(packet, 14)
        payload = packet[16:]
    elif linktype == LINKTYPE_RAW:
        if not payload:
            return None
        version = payload[0] >> 4
        ethertype = 0x0800 if version == 4 else 0x86DD
    else:
        return None

    if ethertype == 0x0800:
        return _parse_ipv4(payload, timestamp)
    if ethertype == 0x86DD:
        return _parse_ipv6(payload, timestamp)
    return None


def _parse_ipv4(data: bytes, timestamp: float) -> Optional[dict]:
    if len(data) < 20:
        return None
    version_ihl = data[0]
    ihl = (version_ihl & 0x0F) * 4
    total_length = _u16(data, 2)
    protocol = data[9]
    src = ".".join(str(b) for b in data[12:16])
    dst = ".".join(str(b) for b in data[16:20])
    payload = data[ihl:total_length] if total_length else data[ihl:]
    return {"ip_version": 4, "src": src, "dst": dst, "protocol": protocol,
            "payload": payload, "timestamp": timestamp}


def _parse_ipv6(data: bytes, timestamp: float) -> Optional[dict]:
    if len(data) < 40:
        return None
    next_header = data[6]
    src = _format_ipv6(data[8:24])
    dst = _format_ipv6(data[24:40])
    return {"ip_version": 6, "src": src, "dst": dst, "protocol": next_header,
            "payload": data[40:], "timestamp": timestamp}


def _format_ipv6(raw: bytes) -> str:
    groups = [f"{raw[i]:02x}{raw[i + 1]:02x}" for i in range(0, 16, 2)]
    return ":".join(groups)


def parse_dns(payload: bytes) -> Optional[dict]:
    """Read the query name and type from a DNS message payload."""
    if len(payload) < 12:
        return None
    questions = _u16(payload, 4)
    if questions == 0:
        return None
    labels = []
    offset = 12
    while offset < len(payload):
        length = payload[offset]
        if length == 0:
            offset += 1
            break
        if length & 0xC0:
            return None
        labels.append(payload[offset + 1:offset + 1 + length].decode("ascii", errors="replace"))
        offset += 1 + length
    query_type = _u16(payload, offset) if offset + 2 <= len(payload) else 0
    return {"question": ".".join(labels), "type": query_type}


def parse_tls_client_hello(payload: bytes) -> Optional[dict]:
    """Read the server name list out of a TLS ClientHello.

    `payload` starts at the TLS record header (content type, version, length),
    followed by the 4-byte handshake header, so the ClientHello body begins 9
    bytes in: legacy version (2), random (32), then the session id, cipher
    suites and compression method before the extensions carrying the SNI.
    """
    if len(payload) < 45:
        return None
    handshake_type = payload[5]
    if handshake_type != 0x01:                           # ClientHello
        return None
    body = payload[9:]
    if len(body) < 35:
        return None
    offset = 2 + 32                                      # legacy version + random
    session_id_length = body[offset]
    offset += 1 + session_id_length
    if offset + 2 > len(body):
        return None
    cipher_length = _u16(body, offset)
    offset += 2 + cipher_length
    if offset >= len(body):
        return None
    compression_length = body[offset]
    offset += 1 + compression_length
    if offset + 2 > len(body):
        return None
    extensions_length = _u16(body, offset)
    offset += 2
    extensions_end = min(offset + extensions_length, len(body))
    while offset + 4 <= extensions_end:
        extension_type = _u16(body, offset)
        extension_length = _u16(body, offset + 2)
        offset += 4
        if extension_type == 0 and extension_length >= 2:
            list_length = _u16(body, offset)
            cursor = offset + 2
            end = min(offset + 2 + list_length, offset + extension_length)
            while cursor + 3 <= end:
                name_type = body[cursor]
                name_length = _u16(body, cursor + 1)
                name = body[cursor + 3:cursor + 3 + name_length]
                if name_type == 0:
                    return {"server_name": name.decode("ascii", errors="replace")}
                cursor += 3 + name_length
        offset += extension_length
    return None
