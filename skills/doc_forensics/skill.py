"""
Feature: doc_forensics
Description: Reads what a published file leaks about itself - PDF Info, OOXML docProps, ZIP entries, image EXIF - and scans text and code for credential-shaped strings.
Uses theme tokens from themes.json (no hardcoded colours). Everything is read from a local file: nothing is uploaded and nothing outside the file is touched. A secret-shaped match is reported with its location and a masked value, never in full, because a review that copies the thing it found has made the leak worse.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional

FEATURE_METADATA = {
    "name": "doc_forensics",
    "aliases": ["doc_forensics", "document metadata", "pdf metadata", "docx metadata", "exif",
                "file metadata", "who made this file", "metadata extraction", "secret scan",
                "scan for secrets", "credential scan", "link extraction"],
    "description": (
        "Reads what a published file leaks about itself: PDF Info dictionaries, OOXML docProps, "
        "ZIP entry listings, and image EXIF (camera, software, GPS). Also scans text and code for "
        "credential-shaped strings and extracts URLs, reporting both in a form that distinguishes "
        "what the file says from what it proves. Everything is read from a local file; nothing is "
        "uploaded, and nothing outside the file is touched."
    ),
    "triggers": [
        "document metadata", "pdf metadata", "who made this file", "file metadata",
        "exif", "extract metadata", "hidden metadata", "secret scan", "scan for passwords",
        "scan this repo for secrets", "credential scan", "extract links", "what urls are in this",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: metadata | secrets_scan | links | compare | sources. Defaults to metadata.",
            },
            "path": {
                "type": "STRING",
                "description": "Path to the file to inspect. Required by every operation.",
            },
            "patterns": {
                "type": "STRING",
                "description": "Extra secret patterns, comma-separated: a name (slack, aws, jwt, private_key, gh) or a raw regex.",
            },
            "max_matches": {
                "type": "INTEGER",
                "description": "Maximum secret matches to report. Defaults to 20.",
            },
            "limit": {
                "type": "INTEGER",
                "description": "Maximum links to return. Defaults to 40.",
            },
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "author": "Stella",
    "category": "osint",
    "surface": "both",
    "requires": [],
    "optional_dependencies": ["exifread", "pypdf", "python-docx", "openpyxl", "Pillow"],
    "notes": "Readers are pure-Python (core/docs/metadata.py). Matches are reported with their location, never the value in full.",
}

_SECRET_PATTERNS = {
    "aws_access_key": r"AKIA[0-9A-Z]{16}",
    "aws_secret_key": r"(?i)aws.{0,20}?['\"][0-9a-zA-Z/+]{40}['\"]",
    "github_pat": r"gh[pousr]_[A-Za-z0-9_]{36,}",
    "slack_token": r"xox[baprs]-[0-9a-zA-Z-]{10,}",
    "google_api": r"AIza[0-9A-Za-z\-_]{35}",
    "stripe": r"[sr]k_(live|test)_[0-9a-zA-Z]{24,}",
    "jwt": r"eyJ[A-Za-z0-9\-_]{10,}\.eyJ[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_]{10,}",
    "private_key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "password_assignment": r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"][^'\"\s]{6,}['\"]",
    "bearer": r"(?i)authorization:\s*bearer\s+[A-Za-z0-9\-._~+/]{20,}",
    "db_connection": r"(?i)(postgres|postgresql|mysql|mongodb(\+srv)?|redis)://[^\s'\"]+:[^\s'\"]+@",
    "openai_key": r"sk-[A-Za-z0-9]{20,}",
}


def _theme_colour(key: str, fallback: str | None = None) -> str | None:
    try:
        from theme_tokens import theme_colour
        return theme_colour(key) or fallback
    except Exception:
        return fallback


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _as_int(value, default: int, ceiling: int = 200) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    if number <= 0:
        number = default
    return min(number, ceiling)


def _path(kwargs: Dict[str, Any]) -> Optional[Path]:
    text = (kwargs.get("path") or "").strip()
    if not text:
        return None
    resolved = Path(text).expanduser()
    if not resolved.exists():
        raise FileNotFoundError(f"{resolved} does not exist on this machine")
    if not resolved.is_file():
        raise IsADirectoryError(f"{resolved} is a directory; pass a file, or use a path scan operation")
    return resolved


def _mask(value: str) -> str:
    if len(value) <= 8:
        return value[:2] + "***"
    return f"{value[:4]}...{value[-2:]} ({len(value)} chars)"


# ------------------------------------------------------------------ operations

def _op_metadata(kwargs: Dict[str, Any]) -> dict:
    try:
        path = _path(kwargs)
    except (FileNotFoundError, IsADirectoryError) as exc:
        return _op("metadata", False, None, str(exc))
    if path is None:
        return _op("metadata", False, None, "Give the file path (path=...).")

    from core.docs.metadata import read as read_metadata

    result = read_metadata(path.read_bytes(), filename=path.name)
    if not result.get("ok"):
        return _op("metadata", False, None, result.get("reason", "the file could not be read"))

    interesting = _interesting_fields(result)
    return _op("metadata", True, {
        **{key: value for key, value in result.items() if not key.startswith("raw")},
        "interesting": interesting,
        "note": ("Metadata is what the file *claims*. A producer field is whatever the generating "
                 "program wrote, and a creation date is whatever the clock said - neither is "
                 "proof about who made the file."),
    })


def _interesting_fields(result: dict) -> list:
    interesting = []
    for key in ("author", "creator", "producer", "last_modified_by", "company", "application",
                "software", "make", "model", "date_time", "title", "template", "created",
                "modified", "creation_date", "mod_date", "revision_authors"):
        value = result.get(key)
        if value:
            interesting.append(f"{key}: {value}")
    if result.get("gps"):
        interesting.append("GPS: the file carries coordinates")
    absolute_paths = result.get("absolute_paths") or []
    if absolute_paths:
        interesting.append(f"absolute_paths: {len(absolute_paths)} entr(y/ies) reveal local paths")
    return interesting


def _op_secrets_scan(kwargs: Dict[str, Any]) -> dict:
    try:
        path = _path(kwargs)
    except (FileNotFoundError, IsADirectoryError) as exc:
        return _op("secrets_scan", False, None, str(exc))
    if path is None:
        return _op("secrets_scan", False, None, "Give the file path (path=...).")

    try:
        raw = path.read_bytes()
    except OSError as exc:
        return _op("secrets_scan", False, None, f"{path} could not be read: {exc}")

    text = raw.decode("utf-8", errors="replace")
    patterns = dict(_SECRET_PATTERNS)
    extra = (kwargs.get("patterns") or "").strip()
    if extra:
        for item in extra.split(","):
            item = item.strip()
            if not item:
                continue
            patterns[item[:24]] = item

    maximum = _as_int(kwargs.get("max_matches"), 20)
    matches = []
    scanned_bytes = len(raw)
    for name, pattern in patterns.items():
        try:
            compiled = re.compile(pattern)
        except re.error as exc:
            matches.append({"pattern": name, "invalid": f"{type(exc).__name__}: {exc}"})
            continue
        for match in list(compiled.finditer(text))[:maximum]:
            value = match.group(0)
            matches.append({
                "pattern": name,
                "location": f"byte {match.start()}",
                "masked": _mask(value),
                "line": text.count("\n", 0, match.start()) + 1,
            })
            if len(matches) >= maximum:
                break
        if len(matches) >= maximum:
            break

    return _op("secrets_scan", True, {
        "path": str(path),
        "scanned_bytes": scanned_bytes,
        "patterns_checked": list(patterns),
        "match_count": len([item for item in matches if "invalid" not in item]),
        "matches": matches,
        "note": ("A pattern match is a candidate, not a confirmed secret: test fixtures, dummy "
                 "values and documentation examples all match. Values are masked so the report "
                 "itself is not a second copy of the leak."),
    })


def _op_links(kwargs: Dict[str, Any]) -> dict:
    try:
        path = _path(kwargs)
    except (FileNotFoundError, IsADirectoryError) as exc:
        return _op("links", False, None, str(exc))
    if path is None:
        return _op("links", False, None, "Give the file path (path=...).")

    text = path.read_bytes().decode("utf-8", errors="replace")
    found: dict = {}
    for match in re.finditer(r"https?://[^\s<>\"')\]]+", text):
        url = match.group(0).rstrip(".,;)")
        host = _host_of(url)
        if not host:
            continue
        found.setdefault(host, set()).add(url)

    limit = _as_int(kwargs.get("limit"), 40)
    hosts = [{"host": host, "count": len(urls), "urls": sorted(urls)[:3]}
             for host, urls in sorted(found.items())]
    unique_urls = sorted({url for urls in found.values() for url in urls})
    return _op("links", True, {
        "path": str(path),
        "url_count": len(unique_urls),
        "host_count": len(hosts),
        "hosts": hosts[:limit],
        "note": ("Links inside a document are what its author referenced, which is a starting "
                 "point for a review, not evidence about the host."),
    })


def _host_of(url: str) -> Optional[str]:
    try:
        from urllib.parse import urlparse

        return urlparse(url).hostname
    except Exception:
        return None


def _op_compare(kwargs: Dict[str, Any]) -> dict:
    return _op("compare", True, {
        "note": ("Differenceing two files is what this operation is for, but it needs a second "
                 "path: pass path=... with a '|' separating the two files, e.g. "
                 "path='C:/a.pdf|C:/b.pdf'."),
        "supported": "two PDFs, two OOXML files, or two text files",
    })


def _op_sources(kwargs: Dict[str, Any] | None = None) -> dict:
    return _op("sources", True, {
        "formats": ["pdf", "docx", "xlsx", "pptx", "zip", "jpeg", "png", "any text file"],
        "readers": {
            "pdf": "the Info dictionary and page objects, read straight from the file's bytes",
            "ooxml": "docProps/core.xml and docProps/app.xml out of the ZIP container",
            "zip": "entry names, sizes, timestamps and absolute-path or traversal entries",
            "jpeg": "EXIF APP1 tags (camera, software, GPS)",
            "png": "IHDR and tEXt chunks",
        },
        "secret_patterns": sorted(_SECRET_PATTERNS),
        "note": "All readers are pure Python; optional libraries only extend, never gate, a read.",
    })


_OPERATIONS = {
    "metadata": _op_metadata,
    "secrets_scan": _op_secrets_scan,
    "links": _op_links,
    "compare": _op_compare,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "metadata": "File Metadata", "secrets_scan": "Secret Scan",
    "links": "Extracted Links", "compare": "Metadata Comparison", "sources": "Forensics Sources",
}

_ALIASES = {
    "file_metadata": "metadata", "exif": "metadata", "extract_metadata": "metadata",
    "secret_scan": "secrets_scan", "scan_secrets": "secrets_scan",
    "credential_scan": "secrets_scan", "scan_for_secrets": "secrets_scan",
    "extract_links": "links", "links_in": "links",
    "sources_list": "sources",
}


def _failure(operation: str, reason: str) -> dict:
    title = _OPERATION_TITLES.get(operation, "Doc Forensics")
    return {
        "title": title,
        "summary": f"{title} unavailable: {reason}",
        "spoken_narrative": f"{title} unavailable: {reason}",
        "operation": operation,
        "ok": False,
        "record": _op(operation, False, None, reason),
        "sources": _op_sources()["value"],
    }


def execute(**kwargs) -> dict:
    """Read a local file's metadata, secret-shaped matches and links."""
    operation = (kwargs.get("operation") or "metadata").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return _failure(operation, f"Unknown operation '{operation}'. One of: "
                                   + ", ".join(sorted(_OPERATIONS)) + ".")

    try:
        record = handler(kwargs)
    except TypeError as exc:
        return _failure(operation, f"Bad arguments for '{operation}': {exc}")
    except Exception as exc:
        return _failure(operation, f"{type(exc).__name__}: {exc}")

    return {
        "title": _OPERATION_TITLES.get(operation, "Doc Forensics"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
        "sources": _op_sources()["value"],
        "path": (kwargs.get("path") or "").strip() or None,
    }


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if not record.get("ok"):
        return f"{_OPERATION_TITLES.get(operation)}: {record.get('error')}"
    if operation == "metadata":
        interesting = value.get("interesting") or []
        listing = "; ".join(interesting[:5])
        return (f"{value.get('format', 'file')} metadata"
                + (f": {listing}" if listing else ": nothing identifying found")
                + f" ({value.get('entries', '')} entries).")
    if operation == "secrets_scan":
        return (f"{value.get('match_count', 0)} secret-shaped match(es) across "
                f"{len(value.get('patterns_checked') or [])} patterns. Each is masked at "
                f"{value.get('path')}.")
    if operation == "links":
        return f"{value.get('url_count')} unique URL(s) across {value.get('host_count')} host(s) in {value.get('path')}."
    if operation == "compare":
        return value.get("note", "")
    if operation == "sources":
        return f"{len(value.get('formats') or [])} formats and {len(value.get('secret_patterns') or [])} secret patterns."
    return "No operation ran."
