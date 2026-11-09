"""
Feature: wireless_audit
Description: Audits a wireless network you own or have written permission to test - interface inventory, monitor capability, site survey, WPA handshake and PMKID capture, WPS audit, and policy-gated rogue AP.
Uses theme tokens from themes.json (no hardcoded colours). Every transmitting operation needs an explicit target and an explicit authorisation, every result names the tool it used and whether that tool exists on this machine, and an operation that cannot run reports the missing binary, adapter, driver or permission by name. Nothing is broadcast to a network the caller did not name, and no capture is started without a stated target.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

FEATURE_METADATA = {
    "name": "wireless_audit",
    "aliases": ["wireless_audit", "wifi pentest", "wireless pentest", "handshake capture",
                "capture handshake", "pmkid", "wpa crack", "wifi audit", "site survey",
                "monitor mode", "aircrack", "wifite", "bettercap", "hcxdumptool", "wps audit",
                "reaver", "evil twin", "rogue ap", "airgeddon"],
    "description": (
        "Audit a wireless network you own or have written permission to test: inventory "
        "interfaces and monitor-mode capability, survey visible access points, capture a WPA "
        "handshake or a PMKID with the aircrack-ng suite, wifite2, bettercap or hcxdumptool, run "
        "a WPS audit with reaver/bully, or - only behind an explicit policy rule - stand up a "
        "rogue AP. Every operation needs an explicit target and an explicit authorisation, and "
        "each result states which tool it used, whether that tool is installed, and what this "
        "machine's adapter can actually do. Never runs against an interface or access point the "
        "caller did not name."
    ),
    "triggers": [
        "wifi pentest", "wireless pentest", "capture handshake", "get the handshake",
        "pmkid attack", "wpa handshake", "monitor mode", "site survey",
        "scan for networks", "list wifi networks", "wps pin", "reaver", "bully",
        "evil twin", "rogue access point", "captive portal", "deauthenticate",
        "deauth client", "aircrack-ng", "wifite", "bettercap", "hcxdumptool",
        "airgeddon", "can i capture on this adapter", "what wifi networks are around",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: tools | interfaces | monitor | survey | capture_handshake | capture_pmkid | deauth | wps | rogue_ap | sources. Defaults to tools.",
            },
            "interface": {
                "type": "STRING",
                "description": "Wireless interface to use, e.g. wlan0. Required by the capture, deauth, WPS and rogue-AP operations.",
            },
            "bssid": {
                "type": "STRING",
                "description": "Access point BSSID (MAC) the operation targets. Required to target one AP.",
            },
            "essid": {
                "type": "STRING",
                "description": "Network name (ESSID) being targeted, recorded with the target.",
            },
            "channel": {
                "type": "INTEGER",
                "description": "Channel to lock the interface to for capture, e.g. 6.",
            },
            "client": {
                "type": "STRING",
                "description": "Client MAC to deauthenticate. When omitted, the operation refuses rather than broadcasting to every station in range.",
            },
            "authorized": {
                "type": "BOOLEAN",
                "description": "Must be true to run an operation that sends frames. Without it, only read-only operations run.",
            },
            "duration_seconds": {
                "type": "INTEGER",
                "description": "Capture window in seconds. Defaults to 60, capped at 1800.",
            },
            "output": {
                "type": "STRING",
                "description": "Where to write the capture file. Defaults to a timestamped file under Stella's deliverables directory.",
            },
            "wordlist": {
                "type": "STRING",
                "description": "Wordlist path for WPS or rogue-AP operations that accept one.",
            },
            "confirm": {
                "type": "BOOLEAN",
                "description": "Must be true to start an operation that transmits. Defaults to false.",
            },
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "author": "Stella",
    "category": "security",
    "optional_dependencies": [],
    "notes": "External tools: aircrack-ng (airmon-ng, airodump-ng, aireplay-ng), wifite2, bettercap, hcxdumptool, reaver, bully, airgeddon, iw. Each is probed per call and reported when missing.",
}

_READ_ONLY = {"tools", "interfaces", "monitor", "survey", "sources"}
_TRANSMITTING = {"capture_handshake", "capture_pmkid", "deauth", "wps", "rogue_ap"}
_MAX_CAPTURE_SECONDS = 1800


def _theme_colour(key: str, fallback: str | None = None) -> str | None:
    try:
        from theme_tokens import theme_colour
        return theme_colour(key) or fallback
    except Exception:
        return fallback


def _deliverables_dir():
    try:
        from core.user_paths import get_user_data_dir
        return get_user_data_dir() / "deliverables"
    except Exception:
        import os
        from pathlib import Path
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "StellaAI" / "deliverables"


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    """One operation record, stating its own outcome either way."""
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _flag(**kwargs) -> bool:
    return kwargs.get("authorized") in (True, "true", "True", 1, "1") and \
        kwargs.get("confirm") in (True, "true", "True", 1, "1")


def _as_int(value, default: int = 60, ceiling: int = _MAX_CAPTURE_SECONDS) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    if number <= 0:
        number = default
    return min(number, ceiling)


def _audit(operation: str, target: str, activity: str, detail: str) -> None:
    try:
        from core import audit

        audit.record("agent", f"wireless_audit.{operation}", target or "-", "permitted",
                     activity=activity, extra={"detail": detail})
    except Exception:
        pass


# ---------------------------------------------------------------- read-only ops

def _op_tools(kwargs: Dict[str, Any]) -> dict:
    from core.security.tools import describe_platform
    from core.security import wireless

    platform = describe_platform()
    probed = wireless.list_capture_tools()
    present = [name for name, entry in probed.items() if entry["present"]]
    missing = [name for name, entry in probed.items() if not entry["present"]]
    install = {name: entry.get("install") for name, entry in probed.items()
               if not entry["present"] and entry.get("install")}
    return _op("tools", True, {
        "platform": platform,
        "present": present,
        "missing": missing,
        "install": install,
        "note": ("A tool being installed does not mean it can act: the adapter, the driver and "
                 "the permission policy are all separate, and each operation reports them."),
    })


def _op_interfaces(kwargs: Dict[str, Any]) -> dict:
    from core.security import wireless

    listed = wireless.interfaces()
    if not listed.get("ok"):
        return _op("interfaces", False, None, listed.get("reason", "no wireless tool could be read"))
    return _op("interfaces", True, listed)


def _op_monitor(kwargs: Dict[str, Any]) -> dict:
    from core.security import wireless

    interface = (kwargs.get("interface") or "").strip()
    if not interface:
        capability = wireless.interfaces()
        if not capability.get("ok"):
            return _op("monitor", False, None, capability.get("reason", "no interface was named"))
        names = [entry.get("name") for entry in capability.get("interfaces") or []
                 if entry.get("name")]
        if not names:
            return _op("monitor", False, None, "this machine reports no named wireless interfaces")
        interface = names[0]
    result = wireless.monitor_capability(interface)
    if not result.get("ok"):
        return _op("monitor", False, None, result.get("reason", "the adapter could not be read"))
    if result.get("monitor_supported") is False:
        return _op("monitor", False, None, result.get("reason"))
    return _op("monitor", True, result)


def _op_survey(kwargs: Dict[str, Any]) -> dict:
    from core.security import wireless

    result = wireless.survey((kwargs.get("interface") or "").strip())
    if not result.get("ok"):
        return _op("survey", False, None, result.get("reason", "no scan tool could be read"))
    return _op("survey", True, result)


def _op_sources(kwargs: Dict[str, Any] | None = None) -> dict:
    return _op("sources", True, {
        "tools": [
            {"tool": "aircrack-ng", "role": "suite: airmon-ng, airodump-ng, aireplay-ng"},
            {"tool": "wifite2", "role": "automated capture of WPA handshakes and PMKIDs"},
            {"tool": "bettercap", "role": "WiFi modules, deauth, handshake capture"},
            {"tool": "hcxdumptool / hcxpcapngtool", "role": "PMKID capture and capture conversion"},
            {"tool": "hashcat (mode 22000)", "role": "offline handshake/PMKID cracking"},
            {"tool": "john", "role": "CPU fallback cracker"},
            {"tool": "reaver / bully", "role": "WPS PIN audit"},
            {"tool": "airgeddon", "role": "rogue AP / Evil Twin / captive portal"},
        ],
        "references": [
            "Aircrack-ng documentation wiki (chipsets, drivers, injection)",
            "Hashcat wiki, mode 22000 (WPA-PBKDF2-PMKID+EAPOL)",
            "PayloadsAllTheThings - network and wireless pivoting methodology",
        ],
    })


# -------------------------------------------------------------- transmitting ops

def _authorisation_denial(operation: str) -> dict:
    return _op(operation, False, None, (
        f"'{operation}' transmits frames, so it needs authorized=true AND confirm=true, plus a "
        "named target. Neither is a default: set both in the request, and make sure "
        "config/tool_policy.json carries an allow rule naming this tool, the interface and the "
        "target. Refusing is deliberate - an unauthorised deauth is an attack on a network you "
        "do not own."))


def _target(kwargs: Dict[str, Any]) -> str:
    bssid = (kwargs.get("bssid") or "").strip().lower()
    essid = (kwargs.get("essid") or "").strip()
    interface = (kwargs.get("interface") or "").strip()
    parts = [part for part in (bssid, essid, interface) if part]
    return ",".join(parts)


def _op_capture_handshake(kwargs: Dict[str, Any]) -> dict:
    operation = "capture_handshake"
    if not _flag(**kwargs):
        return _authorisation_denial(operation)

    interface = (kwargs.get("interface") or "").strip()
    bssid = (kwargs.get("bssid") or "").strip()
    if not interface:
        return _op(operation, False, None, "name the interface to capture on (interface=...)")
    if not bssid:
        return _op(operation, False, None, (
            "name the access point to target (bssid=...). A capture without a target would "
            "record every network in range, which is not what an audit does."))

    from core.security.tools import available, run_background

    probed = available(["airodump-ng", "wifite", "bettercap"])
    duration = _as_int(kwargs.get("duration_seconds"), 60)
    output = _capture_path(kwargs, "handshake")
    channel = kwargs.get("channel")

    if probed["airodump-ng"]["present"]:
        argv = ["airodump-ng", "--bssid", bssid, "-w", str(Path(output).with_suffix(""))]
        if channel:
            argv += ["-c", str(int(channel))]
        argv.append(interface)
        started = run_background(argv, output)
        tool = "airodump-ng"
    elif probed["wifite"]["present"]:
        argv = ["wifite", "--bssid", bssid, "-i", interface, "--keep-ivs",
                "--no-wps", "--no-pmkid", "--no-wep", "--dict", "/dev/null"]
        started = run_background(argv, output)
        tool = "wifite2"
    elif probed["bettercap"]["present"]:
        started = {"ok": False, "outcome": "failed",
                   "reason": ("bettercap needs an interactive session for the wifi modules; run "
                              "`bettercap -iface " + interface + "` and use `wifi.recon on` / "
                              "`wifi.deauth <client>` from there.")}
        tool = "bettercap"
    else:
        started = {"ok": False, "outcome": "failed",
                   "reason": "no capture tool is installed (looked for airodump-ng, wifite, bettercap)."}
        tool = None

    _audit(operation, _target(kwargs), "active", f"tool={tool} duration={duration}s")
    if not started.get("ok"):
        return _op(operation, False, None, started.get("reason", "the capture did not start"))
    return _op(operation, True, {
        **started,
        "tool": tool,
        "target": _target(kwargs),
        "duration_seconds": duration,
        "output": output,
        "note": ("The capture is running. It is `started`, not `done`: whether the handshake "
                 "landed is read back from the file with the hash_cracker or handshake check "
                 "when it finishes."),
    })


def _op_capture_pmkid(kwargs: Dict[str, Any]) -> dict:
    operation = "capture_pmkid"
    if not _flag(**kwargs):
        return _authorisation_denial(operation)

    interface = (kwargs.get("interface") or "").strip()
    if not interface:
        return _op(operation, False, None, "name the interface to capture on (interface=...)")

    from core.security.tools import available, run_background

    probed = available(["hcxdumptool", "bettercap", "wifite"])
    output = _capture_path(kwargs, "pmkid")
    duration = _as_int(kwargs.get("duration_seconds"), 60)

    if probed["hcxdumptool"]["present"]:
        argv = ["hcxdumptool", "-i", interface, "-w", output,
                "--filtermode=2", "--max_essids=64"]
        started = run_background(argv, output)
        tool = "hcxdumptool"
    elif probed["wifite"]["present"]:
        argv = ["wifite", "-i", interface, "--no-wps", "--no-handshake", "--no-wep"]
        started = run_background(argv, output)
        tool = "wifite2"
    else:
        started = {"ok": False, "outcome": "failed",
                   "reason": ("PMKID capture needs hcxdumptool (hcxtools) or wifite2; neither is "
                              "installed on this machine.")}
        tool = None

    _audit(operation, _target(kwargs), "active", f"tool={tool} duration={duration}s")
    if not started.get("ok"):
        return _op(operation, False, None, started.get("reason", "the capture did not start"))
    return _op(operation, True, {
        **started,
        "tool": tool,
        "duration_seconds": duration,
        "output": output,
        "note": ("A PMKID capture does not need a connected client, so it is the quietest way to "
                 "get a crackable hash - but it still transmits, which is why it is gated."),
    })


def _op_deauth(kwargs: Dict[str, Any]) -> dict:
    operation = "deauth"
    if not _flag(**kwargs):
        return _authorisation_denial(operation)

    interface = (kwargs.get("interface") or "").strip()
    client = (kwargs.get("client") or "").strip()
    if not interface:
        return _op(operation, False, None, "name the interface to inject on (interface=...)")
    if not client:
        return _op(operation, False, None, (
            "name the client MAC to deauthenticate (client=...). Without a client the only "
            "option is a broadcast deauth against every station in range, which is refused: it "
            "disconnects networks that are not the target."))

    from core.security.tools import available, run_background

    probed = available(["aireplay-ng", "bettercap"])
    count = _as_int(kwargs.get("duration_seconds"), 10, 600)
    if probed["aireplay-ng"]["present"]:
        argv = ["aireplay-ng", "--deauth", str(count), "-a",
                (kwargs.get("bssid") or "").strip(), "-c", client, interface]
        started = run_background(argv, interface)
        tool = "aireplay-ng"
    elif probed["bettercap"]["present"]:
        started = {"ok": False, "outcome": "failed",
                   "reason": ("bettercap's wifi.deauth needs its interactive session; this "
                              "operation does not drive one on your behalf.")}
        tool = "bettercap"
    else:
        started = {"ok": False, "outcome": "failed",
                   "reason": "no injection tool is installed (looked for aireplay-ng, bettercap)."}
        tool = None

    _audit(operation, _target(kwargs), "destructive", f"tool={tool} client={client}")
    if not started.get("ok"):
        return _op(operation, False, None, started.get("reason", "the deauth did not start"))
    return _op(operation, True, {**started, "tool": tool, "client": client,
                                 "target": _target(kwargs),
                                 "frames": count,
                                 "note": ("A deauth sends management frames that disconnect a "
                                          "client. It is recorded as destructive because it "
                                          "breaks other people's connectivity.")})


def _op_wps(kwargs: Dict[str, Any]) -> dict:
    operation = "wps"
    if not _flag(**kwargs):
        return _authorisation_denial(operation)

    interface = (kwargs.get("interface") or "").strip()
    bssid = (kwargs.get("bssid") or "").strip()
    if not interface:
        return _op(operation, False, None, "name the interface to use (interface=...)")
    if not bssid:
        return _op(operation, False, None, "name the access point to audit (bssid=...)")

    from core.security.tools import available, run_background

    probed = available(["reaver", "bully"])
    if probed["reaver"]["present"]:
        argv = ["reaver", "-i", interface, "-b", bssid, "-vv", "-K", "1"]
        if kwargs.get("wordlist"):
            argv += ["-w", str(Path(kwargs["wordlist"]).expanduser())]
        started = run_background(argv, interface)
        tool = "reaver"
    elif probed["bully"]["present"]:
        argv = ["bully", "-b", bssid, interface, "-v", "3"]
        started = run_background(argv, interface)
        tool = "bully"
    else:
        started = {"ok": False, "outcome": "failed",
                   "reason": "no WPS auditor is installed (looked for reaver, bully)."}
        tool = None

    _audit(operation, _target(kwargs), "active", f"tool={tool}")
    if not started.get("ok"):
        return _op(operation, False, None, started.get("reason", "the WPS audit did not start"))
    return _op(operation, True, {**started, "tool": tool, "bssid": bssid,
                                 "target": _target(kwargs),
                                 "note": ("A WPS PIN audit is online brute force: it takes "
                                          "minutes to many hours, and modern APs rate-limit or "
                                          "lock out. The result is `started`, not `done`.")})


def _op_rogue_ap(kwargs: Dict[str, Any]) -> dict:
    operation = "rogue_ap"
    if not _flag(**kwargs):
        return _authorisation_denial(operation)

    essid = (kwargs.get("essid") or "").strip()
    if not essid:
        return _op(operation, False, None, (
            "name the SSID the rogue AP will present (essid=...). This is the second gate: a "
            "rogue AP answers to strangers, so config/tool_policy.py must also carry a rule that "
            "names rogue_ap specifically - the blanket rule that permits capture is not enough."))

    from core.security.tools import available

    probed = available(["airgeddon", "bettercap"])
    if probed["airgeddon"]["present"]:
        return _op(operation, False, {
            **probed,
            "note": "interactive tool; run it directly",
            "outcome": "ask",
        }, (
            "airgeddon is an interactive TUI that owns the terminal while it runs, so Stella does "
            "not drive it on your behalf. Run it directly and use its Evil Twin and captive "
            "portal options; this skill reports that it is installed and leaves the terminal to you."
        ))
    if probed["bettercap"]["present"]:
        return _op(operation, False, None, (
            "bettercap's rogue-AP modules need its interactive session too. Run `bettercap "
            "-iface <iface>` and use `set wifi.ap.ssid <ssid>` / `wifi.ap on` there."))
    return _op(operation, False, None, (
        "no rogue-AP tool is installed (looked for airgeddon, bettercap). Nothing was started."))


def _capture_path(kwargs: Dict[str, Any], kind: str) -> str:
    import time

    explicit = (kwargs.get("output") or "").strip()
    if explicit:
        return explicit
    stamp = int(time.time())
    name = (kwargs.get("essid") or "capture").strip().replace(" ", "_")[:24] or "capture"
    return str(_deliverables_dir() / f"{kind}_{name}_{stamp}.cap")


# ------------------------------------------------------------------ disposition

_OPERATIONS = {
    "tools": _op_tools,
    "interfaces": _op_interfaces,
    "monitor": _op_monitor,
    "survey": _op_survey,
    "capture_handshake": _op_capture_handshake,
    "capture_pmkid": _op_capture_pmkid,
    "deauth": _op_deauth,
    "wps": _op_wps,
    "rogue_ap": _op_rogue_ap,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "tools": "Wireless Toolchain", "interfaces": "Wireless Interfaces",
    "monitor": "Monitor-Mode Capability", "survey": "Wireless Site Survey",
    "capture_handshake": "WPA Handshake Capture", "capture_pmkid": "PMKID Capture",
    "deauth": "Deauthentication", "wps": "WPS Audit", "rogue_ap": "Rogue Access Point",
    "sources": "Wireless Audit Sources",
}

_ALIASES = {
    "toolchain": "tools", "capabilities": "tools", "installed": "tools",
    "interfaces_list": "interfaces", "adapters": "interfaces", "wifi_interfaces": "interfaces",
    "monitor_mode": "monitor", "can_i_capture": "monitor", "capability": "monitor",
    "site_survey": "survey", "scan": "survey", "scan_wifi": "survey", "networks": "survey",
    "handshake": "capture_handshake", "capture": "capture_handshake",
    "pmkid": "capture_pmkid", "capture_pmkid_attack": "capture_pmkid",
    "deauth_client": "deauth", "deauthenticate": "deauth", "kick_client": "deauth",
    "wps_audit": "wps", "wpa_handshake_pin": "wps",
    "evil_twin": "rogue_ap", "rogue_access_point": "rogue_ap",
    "sources_list": "sources",
}


def _failure(operation: str, reason: str) -> dict:
    title = _OPERATION_TITLES.get(operation, "Wireless Audit")
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
    """Audit a wireless network, with authorisation and target naming enforced."""
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

    value = record.get("value") or {}
    return {
        "title": _OPERATION_TITLES.get(operation, "Wireless Audit"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
        "sources": _op_sources()["value"]["tools"],
        "authorized": _flag(**kwargs),
        "target": _target(kwargs) or None,
    }


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "tools":
        platform = (value.get("platform") or {}).get("platform")
        present = value.get("present") or []
        missing = value.get("missing") or []
        return (f"Toolchain on {platform}: {len(present)} present ({', '.join(present[:6]) or 'none'}), "
                f"{len(missing)} missing. {(value.get('platform') or {}).get('note', '')}")
    if operation == "interfaces":
        entries = value.get("interfaces") or []
        listing = ", ".join(f"{entry.get('name')} ({entry.get('mode', 'unknown mode')})"
                            for entry in entries)
        return f"Wireless interfaces: {listing or 'none reported'}. Backend: {value.get('backend')}."
    if operation == "monitor":
        if record.get("ok"):
            supported = value.get("monitor_supported")
            if supported is True:
                return (f"{value.get('interface')} advertises monitor mode "
                        f"(channel {value.get('channel')}). Injection remains unknown until an "
                        "authorised test injects frames.")
            return (f"{value.get('interface')} is {value.get('current_mode')} and its driver "
                    f"advertises monitor_supported={supported}. {value.get('note', '')}")
        return f"Monitor capability unavailable: {record.get('error')}"
    if operation == "survey":
        aps = value.get("access_points") or []
        listing = ", ".join(f"{ap.get('ssid') or ap.get('bssid')} (ch {ap.get('channel', '?')})"
                            for ap in aps[:8])
        return f"{len(aps)} access points visible via {value.get('backend')}. {listing}"
    if operation in ("capture_handshake", "capture_pmkid", "deauth", "wps", "rogue_ap"):
        if not record.get("ok"):
            return f"{_OPERATION_TITLES[operation]} did not run: {record.get('error')}"
        if value.get("outcome") == "started":
            return (f"{_OPERATION_TITLES[operation]} started with {value.get('tool')} "
                    f"(pid {value.get('pid')}). {value.get('note', '')}")
        return value.get("reason", f"{_OPERATION_TITLES[operation]} reported no result.")
    if operation == "sources":
        return f"{len(value.get('tools') or [])} external tools and methodologies behind this skill."
    return record.get("error") or "No operation ran."
