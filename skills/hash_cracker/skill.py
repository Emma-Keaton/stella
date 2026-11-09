"""
Feature: hash_cracker
Description: Identify, convert and crack hashes offline with hashcat or John, including WPA handshakes and PMKIDs in hashcat's modern mode 22000.
Uses theme tokens from themes.json (no hardcoded colours). Cracking is offline-only: a hash never leaves this machine, a missing tool is named with the package that provides it, and a cracking session reports `started` with its real speed and progress read back from its own files. Nothing is claimed as cracked until hashcat or John shows it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

FEATURE_METADATA = {
    "name": "hash_cracker",
    "aliases": ["hash_cracker", "crack hash", "password crack", "hashcat", "john the ripper",
                "crack wifi password", "crack handshake", "wpa crack", "identify hash",
                "convert capture", "hc22000", "hccapx", "rockyou"],
    "description": (
        "Crack a hash you are authorised to crack, offline, on this machine. Identifies a hash by "
        "shape, converts a capture file into hashcat's modern WPA mode 22000 (or the older "
        "hccapx), lists the wordlists this machine already has, and starts a hashcat or John "
        "session that reports back its real speed and progress. Every crack runs on a file that "
        "is already here: no hash is uploaded, no server is contacted, and a missing tool is "
        "named with the package that provides it."
    ),
    "triggers": [
        "crack this hash", "identify this hash", "what hash is this", "crack the password",
        "crack the handshake", "crack the wpa password", "wpa2 crack", "hashcat",
        "john the ripper", "convert this capture", "hc22000", "hccapx",
        "do I have rockyou", "what wordlists do I have", "cracking status",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: tools | identify | convert | crack | john | status | wordlists | sources. Defaults to tools.",
            },
            "hash": {"type": "STRING",
                     "description": "The hash to identify, or its first characters."},
            "hash_file": {"type": "STRING",
                          "description": "Path to a hash file for cracking, converting or reading status."},
            "capture": {"type": "STRING",
                        "description": "Path to an existing .cap/.pcap capture to convert into a crackable hash."},
            "sample": {"type": "STRING", "description": "Alias for hash."},
            "wordlist": {"type": "STRING",
                         "description": "Wordlist path. When omitted, hashcat runs in increment mode and says so."},
            "mode": {"type": "INTEGER",
                     "description": "hashcat mode number: 22000 for WPA-PBKDF2-PMKID+EAPOL, 0 for MD5, 1000 for NTLM. Defaults to 22000."},
            "rules": {"type": "STRING", "description": "Optional hashcat rule file, e.g. best64.rule."},
            "workload": {"type": "STRING",
                         "description": "hashcat workload profile 1-4. Defaults to 2, which keeps the desktop usable."},
            "confirm": {"type": "BOOLEAN",
                        "description": "Must be true to start a cracking session. Defaults to false."},
            "limit": {"type": "INTEGER", "description": "Maximum entries to return. Defaults to 20."},
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "author": "Stella",
    "category": "security",
    "optional_dependencies": [],
    "notes": "External tools: hashcat (mode 22000), john, hcxpcapngtool, cap2hccapx, aircrack-ng. Probed per call. Cracking is offline-only.",
}


def _theme_colour(key: str, fallback: str | None = None) -> str | None:
    try:
        from theme_tokens import theme_colour
        return theme_colour(key) or fallback
    except Exception:
        return fallback


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _as_int(value, default: int = 20, ceiling: int = 200) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    if number <= 0:
        number = default
    return min(number, ceiling)


def _flag(**kwargs) -> bool:
    return kwargs.get("confirm") in (True, "true", "True", 1, "1")


def _hash_file_arg(kwargs: Dict[str, Any]) -> str:
    return (kwargs.get("hash_file") or kwargs.get("capture") or kwargs.get("path") or "").strip()


def _op_tools(kwargs: Dict[str, Any]) -> dict:
    from core.security import hashcat as hashcat_module

    probed = hashcat_module.tools()
    present = [name for name, entry in probed.items() if entry["present"]]
    missing = [name for name, entry in probed.items() if not entry["present"]]
    install = {name: entry.get("install") for name, entry in probed.items()
               if not entry["present"] and entry.get("install")}
    return _op("tools", True, {"present": present, "missing": missing, "install": install,
                               "limit": _as_int(kwargs.get("limit"), 20)})


def _op_identify(kwargs: Dict[str, Any]) -> dict:
    from core.security import hashcat as hashcat_module

    sample = (kwargs.get("hash") or kwargs.get("sample") or "").strip()
    result = hashcat_module.identify(sample)
    if not result.get("ok"):
        return _op("identify", False, None, result.get("reason", "the hash could not be identified"))
    return _op("identify", True, result)


def _op_convert(kwargs: Dict[str, Any]) -> dict:
    from core.security import hashcat as hashcat_module

    capture = _hash_file_arg(kwargs)
    if not capture:
        return _op("convert", False, None,
                   "Name the capture file to convert (capture=... or hash_file=...).")
    result = hashcat_module.convert(capture)
    if not result.get("ok"):
        return _op("convert", False, None, result.get("reason", "the conversion did not run"))
    return _op("convert", True, result)


def _op_crack(kwargs: Dict[str, Any]) -> dict:
    operation = "crack"
    if not _flag(**kwargs):
        return _op(operation, False, None, (
            "A cracking session was not started because confirm was not set. It would have run "
            f"hashcat over {_hash_file_arg(kwargs) or 'the named file'} with mode "
            f"{kwargs.get('mode') or 22000}. Set confirm=true to run it."))

    target = _hash_file_arg(kwargs)
    if not target:
        return _op(operation, False, None, "Name the hash file to crack (hash_file=...).")

    from core.security import hashcat as hashcat_module

    mode = str(_as_int(kwargs.get("mode"), 22000, 100000))
    rules = [str(kwargs.get("rules"))] if kwargs.get("rules") else None
    result = hashcat_module.start_crack(target, wordlist=kwargs.get("wordlist") or "",
                                       mode=mode, rules=rules,
                                       workload=str(kwargs.get("workload") or 2))
    if not result.get("ok"):
        return _op(operation, False, None, result.get("reason", "the session did not start"))
    return _op(operation, True, result)


def _op_john(kwargs: Dict[str, Any]) -> dict:
    operation = "john"
    if not _flag(**kwargs):
        return _op(operation, False, None, (
            "John was not started because confirm was not set. It would have run over "
            f"{_hash_file_arg(kwargs) or 'the named file'}. Set confirm=true to run it."))

    target = _hash_file_arg(kwargs)
    if not target:
        return _op(operation, False, None, "Name the hash file to crack (hash_file=...).")

    from core.security import hashcat as hashcat_module

    result = hashcat_module.john(target, wordlist=kwargs.get("wordlist") or "")
    if not result.get("ok"):
        return _op(operation, False, None, result.get("reason", "the session did not start"))
    return _op(operation, True, result)


def _op_status(kwargs: Dict[str, Any]) -> dict:
    target = _hash_file_arg(kwargs)
    if not target:
        return _op("status", False, None, "Name the hash file to read status for (hash_file=...).")

    from core.security import hashcat as hashcat_module

    result = hashcat_module.cracked(target)
    cracked = result.get("cracked") or []
    if result.get("count"):
        words = [line.split(":")[-1] for line in cracked if ":" in line]
        return _op("status", True, {**result,
                                    "note": ("Cracked hashes are shown only as their password "
                                             "field; the potfile path is in the record if you "
                                             "want the full line."),
                                    "recovered_passwords": [w for w in words if w]})
    return _op("status", True, {**result,
                                "note": ("No cracked hash yet. hashcat reports its own progress "
                                         "in its terminal, and its speed and ETA are re-read "
                                         "from the potfile and outfile by this operation.")})


def _op_wordlists(kwargs: Dict[str, Any]) -> dict:
    from core.security import hashcat as hashcat_module

    return _op("wordlists", True, hashcat_module.wordlists())


def _op_sources(kwargs: Dict[str, Any] | None = None) -> dict:
    return _op("sources", True, {
        "modes": [
            {"mode": 22000, "name": "WPA-PBKDF2-PMKID+EAPOL",
             "note": "The modern mode for both PMKID and 4-way handshakes."},
            {"mode": 2500, "name": "hccapx / hccap", "note": "The older WPA mode; still used by some workflows."},
        ],
        "tools": [
            {"tool": "hashcat", "role": "GPU-accelerated cracking, mode 22000"},
            {"tool": "john", "role": "CPU fallback with wide format detection"},
            {"tool": "hcxpcapngtool", "role": "convert pcap/pcapng to hc22000"},
            {"tool": "cap2hccapx", "role": "convert pcap to hccapx"},
            {"tool": "tshark", "role": "read pcapng, extract EAPOL"},
        ],
    })


_OPERATIONS = {
    "tools": _op_tools,
    "identify": _op_identify,
    "convert": _op_convert,
    "crack": _op_crack,
    "john": _op_john,
    "status": _op_status,
    "wordlists": _op_wordlists,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "tools": "Cracking Toolchain", "identify": "Hash Identification",
    "convert": "Capture Conversion", "crack": "hashcat Session", "john": "John Session",
    "status": "Cracking Status", "wordlists": "Available Wordlists", "sources": "Cracker Sources",
}

_ALIASES = {
    "toolchain": "tools", "installed": "tools",
    "identify_hash": "identify", "what_hash": "identify",
    "convert_capture": "convert", "to_hc22000": "convert", "convert_pcap": "convert",
    "hashcat": "crack", "crack_hash": "crack", "crack_wifi": "crack",
    "crack_handshake": "crack",
    "john_the_ripper": "john",
    "cracking_status": "status", "show_cracked": "status",
    "wordlists_list": "wordlists", "available_wordlists": "wordlists",
    "sources_list": "sources",
}


def _failure(operation: str, reason: str) -> dict:
    title = _OPERATION_TITLES.get(operation, "Hash Cracker")
    return {
        "title": title,
        "summary": f"{title} unavailable: {reason}",
        "spoken_narrative": f"{title} unavailable: {reason}",
        "operation": operation,
        "ok": False,
        "record": _op(operation, False, None, reason),
        "sources": _op_sources()["value"]["tools"],
    }


def execute(**kwargs) -> dict:
    """Identify, convert and crack hashes offline, with the outcome read back."""
    operation = (kwargs.get("operation") or "tools").strip().lower()
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
        "title": _OPERATION_TITLES.get(operation, "Hash Cracker"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
        "sources": _op_sources()["value"]["tools"],
        "hash_file": _hash_file_arg(kwargs) or None,
    }


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "tools":
        present = value.get("present") or []
        missing = value.get("missing") or []
        return (f"Cracking tools: {len(present)} present ({', '.join(present[:6]) or 'none'}) and "
                f"{len(missing)} missing. See the install hints in the record.")
    if operation == "identify":
        if not record.get("ok"):
            return f"Hash identification: {record.get('error')}"
        return (f"That hash looks like {value.get('hash_type')} "
                f"(hashcat mode {value.get('hashcat_mode')}, {value.get('sample_length')} "
                f"characters). {value.get('note', '')}")
    if operation == "convert":
        if not record.get("ok"):
            return f"Capture conversion: {record.get('error')}"
        return f"Converted with {value.get('tool')} to {value.get('output')}."
    if operation in ("crack", "john"):
        if not record.get("ok"):
            return f"{_OPERATION_TITLES[operation]}: {record.get('error')}"
        return (f"{_OPERATION_TITLES[operation]} started (pid {value.get('pid')}) over "
                f"{value.get('hash_file')} with mode {value.get('mode') or value.get('wordlist')}. "
                "It is started, not done: read the status operation to see what it found.")
    if operation == "status":
        if not record.get("ok"):
            return f"Cracking status: {record.get('error')}"
        if value.get("count"):
            return (f"{value['count']} hash(es) cracked so far. "
                    + value.get("note", ""))
        return value.get("note", "No cracked hash yet.")
    if operation == "wordlists":
        lists = value.get("wordlists") or []
        listing = ", ".join(f"{entry['path']} ({entry['bytes']} bytes)" for entry in lists[:5])
        return f"{len(lists)} wordlist(s) already on this machine. {listing or 'None found.'}"
    if operation == "sources":
        return f"Modes and tools: {len(value.get('modes') or [])} modes, {len(value.get('tools') or [])} tools."
    return record.get("error") or "No operation ran."
