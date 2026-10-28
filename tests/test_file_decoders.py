"""Step 3b tests: pcap, APK and document metadata decoders."""

from __future__ import annotations

import pytest

from core.docs.metadata import read as read_metadata
from core.docs.metadata import sniff as sniff_metadata
from core.net.apk import read_manifest
from core.net.apk import DANGEROUS_PERMISSIONS
from core.net.pcap import parse_dns, parse_http_request, parse_tls_client_hello, read_pcap, sniff_pcap


# ------------------------------------------------------------------------------
# pcap fixtures, built by hand so the test states what a capture contains
# ------------------------------------------------------------------------------

def _u32(value: int) -> bytes:
    return value.to_bytes(4, "big")


def _u16(value: int) -> bytes:
    return value.to_bytes(2, "big")


def _ip_checksum(data: bytes) -> int:
    total = 0
    for index in range(0, len(data), 2):
        total += (data[index] << 8) | data[index + 1]
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def _tcp(src_port: int, dst_port: int, payload: bytes, seq: int = 1) -> bytes:
    data_offset_flags = (5 << 12) | 0x018          # data offset 5, PSH + ACK
    header = _u16(src_port) + _u16(dst_port) + _u32(seq) + _u32(1) \
        + _u16(data_offset_flags) + _u16(65535) + _u16(0) + _u16(0)
    return header + payload


def _ipv4(src: str, dst: str, protocol: int, payload: bytes) -> bytes:
    version_ihl = 0x45
    total_length = 20 + len(payload)
    header = bytes([version_ihl, 0x00]) + _u16(total_length) + _u16(0) \
        + _u16(0) + bytes([64, protocol]) + _u16(0) \
        + bytes(int(p) for p in src.split(".")) + bytes(int(p) for p in dst.split("."))
    checksum = _ip_checksum(header)
    header = header[:10] + _u16(checksum) + header[12:]
    return header + payload


def _udp(src_port: int, dst_port: int, payload: bytes) -> bytes:
    length = 8 + len(payload)
    return _u16(src_port) + _u16(dst_port) + _u16(length) + _u16(0) + payload


def _dns_query(name: str) -> bytes:
    header = _u16(0x1234) + _u16(0x0100) + _u16(1) + _u16(0) + _u16(0) + _u16(0)
    question = b"".join(bytes([len(label)]) + label.encode() for label in name.split(".")) + b"\x00"
    return header + question + _u16(1) + _u16(1)


def _http_request() -> bytes:
    return (b"GET /admin HTTP/1.1\r\nHost: example.test\r\n"
            b"Authorization: Basic dXNlcjpwYXNzd29yZA==\r\nUser-Agent: test/1.0\r\n\r\n")


def _ethernet_ipv4(payload: bytes, src_ip: str, dst_ip: str, protocol: int) -> bytes:
    ethernet = b"\x00\x11\x22\x33\x44\x55" + b"\x66\x77\x88\x99\xaa\xbb" + b"\x08\x00"
    return ethernet + _ipv4(src_ip, dst_ip, protocol, payload)


def _pcap_file(frames: list) -> bytes:
    header = _u32(0xA1B2C3D4) + _u16(2) + _u16(4) + _u32(0) + _u32(0) \
        + _u32(65535) + _u32(1)
    body = b""
    for index, frame in enumerate(frames):
        body += _u32(1700000000 + index) + _u32(0) + _u32(len(frame)) + _u32(len(frame)) + frame
    return header + body


# -------------------------------------------------------------------------- pcap

def test_pcap_reads_a_dns_query_and_a_http_request():
    frames = [
        _ethernet_ipv4(_udp(5355, 53, _dns_query("example.test")), "10.0.0.5", "10.0.0.1", 17),
        _ethernet_ipv4(_tcp(40000, 80, _http_request()), "10.0.0.5", "10.0.0.2", 6),
    ]
    result = read_pcap(_pcap_file(frames))
    assert result["ok"] is True
    summary = result["summary"]
    assert summary["packets"] == 2
    assert summary["udp"] == 1
    assert summary["tcp"] == 1
    assert summary["ipv4"] == 2
    assert len(summary["dns_queries"]) == 1
    assert summary["dns_queries"][0]["question"] == "example.test"
    assert len(summary["http_requests"]) == 1
    request = summary["http_requests"][0]
    assert request["method"] == "GET"
    assert request["host"] == "example.test"
    assert len(summary["plaintext_credentials"]) == 1


def test_pcap_rejects_pcapng_and_junk():
    assert read_pcap(b"not a capture at all")["ok"] is False
    pcapng = (0x0A0D0D0A).to_bytes(4, "little") + b"\x00" * 16
    result = read_pcap(pcapng)
    assert result["ok"] is False
    assert "pcapng" in result["reason"]


def test_pcap_header_is_recognised():
    assert sniff_pcap(_pcap_file([]))["format"] == "pcap-big-endian"
    assert sniff_pcap(b"")["ok"] is False


def test_dns_and_tls_helpers_parse_their_payloads():
    query = _dns_query("api.example.test")
    parsed = parse_dns(query)
    assert parsed["question"] == "api.example.test"
    assert parse_dns(b"") is None

    # A real ClientHello layout: 2 version + 32 random + 1 session-id len
    # (0) + 2 cipher len + ciphers + 1 compression len + method + extensions.
    body = bytearray()
    body += b"\x03\x03" + b"\xaa" * 32                  # legacy version + random
    body += bytes([0])                                   # session id length
    body += _u16(2) + b"\xc0\x2b"                       # cipher suites
    body += bytes([1, 0])                                # compression methods
    extension = _u16(0) + _u16(7) + _u16(5) + bytes([0]) + _u16(4) + b"a.bc"
    body += _u16(len(extension)) + extension
    record = b"\x01" + len(body).to_bytes(3, "big") + body
    payload = b"\x16\x03\x01" + _u16(len(record)) + record

    parsed_hello = parse_tls_client_hello(payload)
    assert parsed_hello is not None
    assert parsed_hello["server_name"] == "a.bc"


def test_http_request_parser_reads_the_headers():
    parsed = parse_http_request(_http_request())
    assert parsed["method"] == "GET"
    assert parsed["path"] == "/admin"
    assert parsed["host"] == "example.test"
    assert parsed["user_agent"] == "test/1.0"
    assert parse_http_request(b"not http at all") is None


# --------------------------------------------------------------------------- apk

def test_apk_reader_accepts_only_zips():
    with pytest.raises(ValueError):
        read_manifest(b"this is not a zip")


def test_apk_without_a_manifest_says_so():
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("classes.dex", b"dex")
    with pytest.raises(ValueError):
        read_manifest(buffer.getvalue())


def test_reads_the_real_stella_connect_apk_when_present():
    """The strongest check available: a manifest a real Android build produced."""
    from pathlib import Path

    apk = Path(__file__).resolve().parents[1] / "dist" / "Stella-Connect-1.0.0-android.apk"
    if not apk.exists():
        pytest.skip("the Android build output is not present on this machine")
    result = read_manifest(apk.read_bytes())
    assert result["ok"] is True
    assert result["package"] == "com.stella.connect"
    assert result["version_code"] == 1
    assert result["min_sdk"] == 26
    assert result["target_sdk"] == 35
    assert "android.permission.INTERNET" in result["permissions"]
    assert set(result["dangerous_permissions"]) <= set(DANGEROUS_PERMISSIONS)
    assert any(activity["name"] == "com.stella.connect.MainActivity"
               for activity in result["activities"])
    assert result["has_dex"] is True
    assert result["has_native_libs"] is True


def test_dangerous_permission_list_contains_expected_entries():
    assert "android.permission.CAMERA" in DANGEROUS_PERMISSIONS
    assert "android.permission.READ_SMS" in DANGEROUS_PERMISSIONS
    assert "android.permission.INTERNET" not in DANGEROUS_PERMISSIONS


# ---------------------------------------------------------------------- metadata

def test_metadata_pdf_fields_are_read():
    content = (
        b"%PDF-1.7\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Count 3 >>\nendobj\n"
        b"trailer\n<< /Info 4 0 R >>\nstartxref\n0\n%%EOF\n"
        b"4 0 obj\n<< /Author (Alice Liddell) /Creator (Write) /Producer (AcmePDF 3.2) >>\nendobj\n"
    )
    result = read_metadata(content, "report.pdf")
    assert result["ok"] is True
    assert result["format"] == "pdf"
    assert result["pdf_version"] == "1.7"
    assert result["author"] == "Alice Liddell"
    assert result["creator"] == "Write"
    assert result["producer"] == "AcmePDF 3.2"
    assert result["pages_estimate"] == 3
    assert any("Alice Liddell" in line for line in result["interesting"])


def test_metadata_pdf_reports_encryption():
    result = read_metadata(b"%PDF-1.4\ntrailer\n<< /Encrypt 3 0 R >>\n%%EOF\n", "locked.pdf")
    assert result["encrypted"] is True


def test_metadata_ooxml_reads_docprops():
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "docProps/core.xml",
            b"<?xml version='1.0'?><cp:coreProperties "
            b"xmlns:cp='x' xmlns:dc='x' xmlns:dcterms='x'><dc:creator>Bob</dc:creator>"
            b"<cp:lastModifiedBy>Carol</cp:lastModifiedBy>"
            b"<dcterms:created>2026-01-02T03:04:05Z</dcterms:created>"
            b"<cp:keywords>budget, secret</cp:keywords></cp:coreProperties>")
        archive.writestr(
            "docProps/app.xml",
            b"<?xml version='1.0'?><Properties>"
            b"<Application>Microsoft Office Word</Application>"
            b"<Company>Acme Corp</Company><Template>Normal.dotm</Template>"
            b"<TotalTime>42</TotalTime><Words>128</Words></Properties>")
        archive.writestr("word/document.xml", b"<w/>")
    result = read_metadata(buffer.getvalue(), "notes.docx")
    assert result["ok"] is True
    assert result["format"] == "docx"
    assert result["creator"] == "Bob"
    assert result["last_modified_by"] == "Carol"
    assert result["application"] == "Microsoft Office Word"
    assert result["company"] == "Acme Corp"
    assert result["total_time"] == "42"


def test_metadata_zip_reports_the_entry_list():
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("a.txt", b"hello")
        archive.writestr("/etc/passwd", b"root")
    result = read_metadata(buffer.getvalue(), "bundle.zip")
    assert result["entries"] == 2
    assert result["absolute_paths"] == ["/etc/passwd"]


def test_metadata_png_reads_ihdr():
    import struct

    ihdr = struct.pack(">IIBB", 64, 32, 8, 6)
    chunk = b"IHDR" + ihdr
    crc = b"\x00\x00\x00\x00"
    content = b"\x89PNG\r\n\x1a\n" + (len(ihdr)).to_bytes(4, "big") + chunk + crc
    result = read_metadata(content, "logo.png")
    assert result["ok"] is True
    assert result["width"] == 64
    assert result["height"] == 32


def test_metadata_unknown_format_is_reported_not_guessed():
    result = read_metadata(b"\x00\x01\x02\x03binary", "file.bin")
    assert result["ok"] is False
    assert "not a format" in result["reason"]


def test_sniff_prefers_magic_bytes_over_the_name():
    assert sniff_metadata(b"%PDF-1.5", "actually.docx") == "pdf"
    assert sniff_metadata(b"PK\x03\x04", "notes.docx") == "docx"
    assert sniff_metadata(b"PK\x03\x04", "bundle.zip") == "zip"
    assert sniff_metadata(b"\xff\xd8\xff\xe0", "photo.jpg") == "jpeg"
    assert sniff_metadata(b"\x00\x01", "mystery") == "unknown"
