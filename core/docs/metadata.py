"""core/docs/metadata.py - extract metadata from common document formats.

Everything a published file leaks about itself: who made it, with what, when,
on what path, with what internal notes. Readers here are pure Python:

* PDF: the Info dictionary and the document catalogue, read straight from the
  file's objects (no PDF library, and no rendering)
* OOXML (docx/xlsx/pptx): `docProps/core.xml` and `docProps/app.xml` out of the
  ZIP container
* ZIP archives: entry names, counts and timestamps
* JPEG/PNG: EXIF and text chunks

Optional libraries are never required; when a format is not recognised the
reader says so instead of returning empty fields that look like a finding.
"""

from __future__ import annotations

import re
import struct
import zipfile
from typing import Optional


def sniff(content: bytes, filename: str = "") -> str:
    """Best guess at the format, from magic bytes first and the name second."""
    if content[:4] == b"%PDF":
        return "pdf"
    if content[:2] == b"\xff\xd8":
        return "jpeg"
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if content[:4] == b"PK\x03\x04" or content[:4] == b"PK\x05\x06":
        lowered = (filename or "").lower()
        if lowered.endswith((".docx", ".xlsx", ".pptx", ".potx", ".vsdx")):
            return lowered.rsplit(".", 1)[1]
        return "zip"
    if content[:4] == b"\xd0\xcf\x11\xe0":
        return "legacy-office"
    return "unknown"


def read(content: bytes, filename: str = "") -> dict:
    """Extract metadata from a file, dispatching on its sniffed format."""
    kind = sniff(content, filename)
    readers = {
        "pdf": _read_pdf,
        "jpeg": _read_jpeg,
        "png": _read_png,
        "zip": _read_zip,
        "docx": _read_ooxml,
        "xlsx": _read_ooxml,
        "pptx": _read_ooxml,
        "potx": _read_ooxml,
        "vsdx": _read_ooxml,
    }
    reader = readers.get(kind)
    if reader is None:
        return {
            "ok": False,
            "format": kind,
            "reason": f"'{kind}' is not a format this reader understands; PDF, OOXML, ZIP, JPEG and PNG are supported.",
            "filename": filename,
        }
    result = reader(content)
    result["format"] = kind
    result["filename"] = filename
    return result


# --------------------------------------------------------------------- PDF

def _read_pdf(content: bytes) -> dict:
    info: dict = {}
    # Page count: object-pattern match first, then the /Count entry in the page
    # tree, which writers set reliably even when page objects are compressed.
    pages = len(re.findall(rb"/Type\s*/Page[^s]", content))
    count_match = re.search(rb"/Count\s+(\d+)", content)
    if count_match and int(count_match.group(1)) > pages:
        pages = int(count_match.group(1))
    info_match = re.search(rb"/Info\s*(\d+)\s+\d+\s+R", content)
    if info_match:
        object_number = int(info_match.group(1))
        chunk = re.search(
            rb"%d\s+\d+\s+obj(.*?)endobj" % object_number, content, re.S)
        if chunk:
            info = _read_pdf_dictionary(chunk.group(1).decode("latin-1", errors="replace"))
    trailer = re.search(rb"trailer(.*?)startxref", content, re.S)
    if trailer and not info:
        info = _read_pdf_dictionary(trailer.group(1).decode("latin-1", errors="replace"))

    encrypted = b"/Encrypt" in content
    return {
        "ok": True,
        "pdf_version": _pdf_version(content),
        "pages_estimate": pages,
        "encrypted": encrypted,
        "info": info,
        "producer": info.get("Producer"),
        "creator": info.get("Creator"),
        "author": info.get("Author"),
        "title": info.get("Title"),
        "creation_date": info.get("CreationDate"),
        "mod_date": info.get("ModDate"),
        "interesting": _interesting_pdf_fields(info),
    }


def _pdf_version(content: bytes) -> Optional[str]:
    match = re.match(rb"%PDF-(\d\.\d)", content[:16])
    return match.group(1).decode("ascii") if match else None


def _read_pdf_dictionary(text: str) -> dict:
    out: dict = {}
    for key, value in re.findall(r"/(\w+)\s*\(([^)]*)\)", text):
        out[key] = value
    for key, value in re.findall(r"/(\w+)\s*<([0-9a-fA-F]+)>", text):
        try:
            decoded = bytes.fromhex(value).decode("utf-16-be", errors="replace")
            out[key] = decoded.strip("\0") or value
        except ValueError:
            continue
    return out


def _interesting_pdf_fields(info: dict) -> list:
    """Fields that commonly leak more than a document intends to."""
    interesting = []
    for key in ("Producer", "Creator", "Author", "Title", "CreationDate", "ModDate"):
        if info.get(key):
            interesting.append(f"{key}: {info[key]}")
    return interesting


# -------------------------------------------------------------------- OOXML

def _read_ooxml(content: bytes) -> dict:
    import io

    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise ValueError("this OOXML file is not a readable ZIP") from exc

    names = archive.namelist()
    problems: list = []
    core = _ooxml_properties(archive, "docProps/core.xml", problems)
    app = _ooxml_properties(archive, "docProps/app.xml", problems)
    pictures = [n for n in names if n.startswith("word/media/")]
    comments = [n for n in names if "comment" in n.lower()]
    authors = [n for n in names if "author" in n.lower()]
    revision_authors = _ooxml_list(archive, authors[0]) if authors else []

    return {
        "ok": True,
        "title": core.get("title") or core.get("dc:title"),
        "creator": core.get("creator") or core.get("dc:creator"),
        "last_modified_by": core.get("lastModifiedBy") or core.get("cp:lastModifiedBy"),
        "created": core.get("created") or core.get("dcterms:created"),
        "modified": core.get("modified") or core.get("dcterms:modified"),
        "application": app.get("Application"),
        "app_version": app.get("AppVersion"),
        "company": app.get("Company"),
        "template": app.get("Template"),
        "total_time": app.get("TotalTime"),
        "words": app.get("Words"),
        "revision": core.get("revision"),
        "category": core.get("category") or core.get("cp:category"),
        "keywords": core.get("keywords") or core.get("cp:keywords"),
        "comments": core.get("comments") or core.get("dc:description"),
        "entries": len(names),
        "media_files": len(pictures),
        "comment_files": comments,
        "revision_authors": revision_authors,
        "problems": problems,
        "raw": {"core": core, "app": app},
    }


def _ooxml_properties(archive, name: str, problems: list | None = None) -> dict:
    import xml.etree.ElementTree as ET

    try:
        payload = archive.read(name)
    except KeyError:
        return {}
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        # A properties part that will not parse is reported, so an empty field
        # reads as "unreadable" rather than "empty".
        if problems is not None:
            problems.append(f"{name} could not be parsed: {exc}")
        return {}
    out: dict = {}
    for element in root.iter():
        tag = element.tag.split("}")[-1]
        if element.text and element.text.strip():
            out[tag] = element.text.strip()
        for attribute_key, attribute_value in element.attrib.items():
            out[f"{tag}:{attribute_key.split('}')[-1]}"] = attribute_value
    return out


def _ooxml_list(archive, name: str) -> list:
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(archive.read(name))
    except (KeyError, ET.ParseError):
        return []
    return [element.text.strip() for element in root.iter()
            if element.text and element.text.strip()]


# ---------------------------------------------------------------------- ZIP

def _read_zip(content: bytes) -> dict:
    import io

    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise ValueError("this is not a readable ZIP archive") from exc

    infos = archive.infolist()
    return {
        "ok": True,
        "entries": len(infos),
        "comment": archive.comment.decode("utf-8", errors="replace"),
        "sample_entries": [
            {"name": info.filename, "size": info.file_size, "date": info.date_time,
             "is_dir": info.is_dir()}
            for info in infos[:40]
        ],
        "directories": sum(1 for info in infos if info.is_dir()),
        "largest": max((info.file_size for info in infos), default=0),
        "oldest": min((info.date_time for info in infos), default=None),
        "newest": max((info.date_time for info in infos), default=None),
        "absolute_paths": [info.filename for info in infos if info.filename.startswith("/")],
        "traversal_paths": [info.filename for info in infos if ".." in info.filename],
    }


# --------------------------------------------------------------------- JPEG

def _read_jpeg(content: bytes) -> dict:
    exif = _read_exif(content)
    return {
        "ok": True,
        "exif": exif,
        "make": exif.get("Make") or exif.get("Image Make"),
        "model": exif.get("Model") or exif.get("Image Model"),
        "software": exif.get("Software"),
        "date_time": exif.get("DateTime") or exif.get("Image DateTime"),
        "gps": bool(exif.get("GPS")),
        "tags": len(exif),
    }


def _read_exif(content: bytes) -> dict:
    tags: dict = {}
    if content[:2] != b"\xff\xd8":
        return tags
    offset = 2
    while offset + 4 <= len(content):
        marker = content[offset]
        if marker != 0xFF:
            break
        segment_type = content[offset + 1]
        length = struct.unpack_from(">H", content, offset + 2)[0]
        payload = content[offset + 4:offset + 2 + length]
        if segment_type == 0xE1 and payload[:6] in (b"Exif\x00\x00", b"Exif\x00"):
            tags.update(_read_tiff_exif(payload[6:]))
            break
        offset += 2 + length
    return tags


def _read_tiff_exif(payload: bytes) -> dict:
    tags: dict = {}
    if payload[:2] == b"II":
        endian = "<"
    elif payload[:2] == b"MM":
        endian = ">"
    else:
        return tags
    try:
        (ifd_offset,) = struct.unpack_from(endian + "I", payload, 4)
        entries = _read_ifd(payload, ifd_offset, endian)
        for tag_id, value in entries.items():
            tags[_EXIF_TAGS.get(tag_id, f"0x{tag_id:04x}")] = value
        gps_offset = entries.get(0x8825)
        if gps_offset:
            tags["GPS"] = len(_read_ifd(payload, gps_offset, endian))
    except (struct.error, IndexError):
        return tags
    return tags


def _read_ifd(payload: bytes, offset: int, endian: str) -> dict:
    if offset + 2 > len(payload):
        return {}
    count = struct.unpack_from(endian + "H", payload, offset)[0]
    out: dict = {}
    for index in range(min(count, 200)):
        try:
            tag_id, kind, _length, value_offset = struct.unpack_from(
                endian + "HHII", payload, offset + 2 + index * 12)
        except struct.error:
            break
        out[tag_id] = _exif_value(payload, kind, value_offset, endian, index)
    return out


def _exif_value(payload: bytes, kind: int, value_offset: int, endian: str, index: int) -> object:
    sizes = {1: 1, 2: 1, 3: 2, 4: 4, 5: 4, 7: 1, 9: 4, 10: 8}
    size = sizes.get(kind, 1)
    position = (value_offset + index * 0) if size > 4 else None
    if size <= 4:
        start = value_offset
    else:
        start = value_offset
    try:
        if kind == 2:
            end = start + 4
            chunk = payload[start:end]
            text = chunk.split(b"\x00")[0].decode("ascii", errors="replace")
            if not text and end < len(payload):
                end = payload.index(b"\x00", start)
                text = payload[start:end].decode("ascii", errors="replace")
            return text
        if kind == 3:
            return struct.unpack_from(endian + "H", payload, start)[0]
        if kind == 4:
            return struct.unpack_from(endian + "I", payload, start)[0]
        if kind == 10:
            value = struct.unpack_from(endian + "i", payload, start)[0]
            return (value >> 8) + (value & 0xFF) / 256.0
    except (struct.error, IndexError, ValueError):
        return None
    return None


_EXIF_TAGS = {
    0x010F: "Make", 0x0110: "Model", 0x0131: "Software", 0x0132: "DateTime",
    0x8769: "ExifOffset", 0x8825: "GPSOffset", 0x9000: "ExifVersion",
    0xA002: "PixelXDimension", 0xA003: "PixelYDimension", 0x829A: "ExposureTime",
    0x8827: "ISOSpeed", 0x920A: "FocalLength", 0x0112: "Orientation",
}


# ---------------------------------------------------------------------- PNG

def _read_png(content: bytes) -> dict:
    tags: dict = {}
    offset = 8
    while offset + 8 <= len(content):
        length = struct.unpack_from(">I", content, offset)[0]
        kind = content[offset + 4:offset + 8].decode("ascii", errors="replace")
        payload = content[offset + 8:offset + 8 + length]
        if kind in ("tEXt", "iTXt", "zTXt"):
            tag = {"tEXt": "text", "iTXt": "itext", "zTXt": "ztext"}[kind]
            tags.setdefault(tag, []).append(payload[:200].decode("latin-1", errors="replace"))
        elif kind == "IHDR":
            width, height, bit_depth, color_type = struct.unpack_from(">IIBB", payload, 0)
            tags["width"] = width
            tags["height"] = height
            tags["bit_depth"] = bit_depth
            tags["color_type"] = color_type
        offset += 12 + length
    return {
        "ok": True,
        "width": tags.get("width"),
        "height": tags.get("height"),
        "chunks": tags,
    }


def _exif_gps(latitude: tuple = None, longitude: tuple = None) -> Optional[dict]:
    return None
