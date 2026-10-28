"""core/security/wireless.py - interface inventory, monitor capability, site survey.

Reads the operating system's own view of the radio, and nothing else: no
injection is attempted, no frames are sent, and no association is changed by this
module. Monitor *capability* is reported from what the driver advertises, and
whether injection actually works is left as `unknown` until the user authorises a
test - because the only way to know for certain is to inject.

Windows and Termux are first-class: `netsh wlan show` on Windows, `iw dev` on
Linux/Termux, and on macOS it says plainly that the built-in adapter has no
monitor mode.
"""

from __future__ import annotations

import re
import shutil
from typing import Optional

from core.security.tools import available, platform_tag, run


def interfaces() -> dict:
    """The wireless interfaces this machine has, with their mode."""
    tag = platform_tag()
    if run(["iw", "dev"])["ok"] or shutil.which("iw"):
        parsed = _iw_interfaces()
        if parsed:
            return {"ok": True, "interfaces": parsed, "backend": "iw dev",
                    "platform": tag}
    if shutil.which("netsh"):
        parsed = _netsh_interfaces()
        if parsed is not None:
            return {"ok": True, "interfaces": parsed, "backend": "netsh wlan",
                    "platform": tag,
                    "note": "Windows wireless control is limited; capture needs Npcap."}
    if shutil.which("iwconfig"):
        parsed = _iwconfig_interfaces()
        if parsed:
            return {"ok": True, "interfaces": parsed, "backend": "iwconfig",
                    "platform": tag}
    return {"ok": False, "interfaces": [],
            "reason": ("no wireless tool could be read (looked for iw, netsh, iwconfig); on a "
                       "phone install `iw` from your package manager and use an external "
                       "adapter for monitor mode"),
            "platform": tag}


def _iw_interfaces() -> list:
    result = run(["iw", "dev"])
    if not result["ok"]:
        return []
    interfaces: list = []
    current: dict = {}
    for line in result["stdout"].splitlines():
        stripped = line.strip()
        if stripped.startswith("phy#"):
            if current:
                interfaces.append(current)
            current = {"phy": stripped.replace("phy#", "")}
        elif stripped.startswith("Interface "):
            current["name"] = stripped.split(" ", 1)[1].strip()
        elif stripped.startswith("ifindex "):
            current["ifindex"] = stripped.split(" ", 1)[1].strip()
        elif stripped.startswith("type "):
            current["mode"] = stripped.split(" ", 1)[1].strip()
        elif stripped.startswith("channel "):
            channel = stripped.split(" ", 1)[1].strip().split(" ")[0]
            current["channel"] = channel
        elif stripped.startswith("addr "):
            current["mac"] = stripped.split(" ", 1)[1].strip()
    if current:
        interfaces.append(current)
    return interfaces


def _netsh_interfaces() -> Optional[list]:
    """Parse `netsh wlan show interfaces`.

    netsh echoes a blank line, a header row of dashes, then per-interface blocks
    whose first field is `Name`. A new `Name` row therefore closes the previous
    block, and the block is only kept once it has a name at all - a Windows box
    with no adapter reports an error string rather than a block.
    """
    result = run(["netsh", "wlan", "show", "interfaces"])
    if not result["ok"]:
        return None
    interfaces: list = []
    current: dict = {}
    for line in result["stdout"].splitlines():
        if " : " not in line:
            continue
        name, _, value = line.partition(" : ")
        name = name.strip()
        value = value.strip()
        if name.lower() == "name":
            if current.get("name"):
                interfaces.append(current)
            current = {"name": value}
            continue
        if not current:
            continue
        current[name.lower().replace(" ", "_")] = value
    if current.get("name"):
        interfaces.append(current)
    return interfaces or None


def _iwconfig_interfaces() -> list:
    result = run(["iwconfig"])
    text = result["stdout"] or result["stderr"]
    if not text:
        return []
    interfaces: list = []
    for match in re.finditer(r"^(\S+)\s+IEEE", text, re.MULTILINE):
        name = match.group(1)
        block = text[match.start():text.find("\n\n", match.start())]
        entry: dict = {"name": name}
        mode = re.search(r"Mode:(\S+)", block)
        if mode:
            entry["mode"] = mode.group(1)
        essid = re.search(r'ESSID:"([^"]*)"', block)
        if essid and essid.group(1):
            entry["ssid"] = essid.group(1)
        channel = re.search(r"Channel[:\s]+(\d+)", block)
        if channel:
            entry["channel"] = channel.group(1)
        interfaces.append(entry)
    return interfaces


def monitor_capability(interface: str) -> dict:
    """What the driver advertises for monitor mode on one interface.

    Reports what the chipset *says* it supports. Whether frame injection works is
    a separate question and is only answered by an authorised test, so it is
    `unknown` here rather than assumed either way.
    """
    if not interface:
        return {"ok": False, "reason": "name an interface (interface=...)"}
    listed = interfaces()
    if not listed.get("ok"):
        return {"ok": False, "reason": listed.get("reason", "no wireless tool could be read")}

    entries = [entry for entry in (listed.get("interfaces") or []) if entry.get("name")]
    match = None
    for entry in entries:
        if entry.get("name") == interface:
            match = entry
            break
    if match is None:
        available = ", ".join(entry["name"] for entry in entries) or "none"
        return {"ok": False, "reason": (
            f"no interface called '{interface}' was found; the machine lists {available}. "
            "Pass interface=<name> from that list.")}

    phy = match.get("phy")
    monitor_supported: Optional[bool] = None
    injection = "unknown"
    if phy and shutil.which("iw"):
        caps = run(["iw", f"phy#{phy}", "info"])
        if caps["ok"]:
            monitor_supported = re.search(r"\*\s*monitor", caps["stdout"]) is not None
            ap_mode = re.search(r"\*\s*AP", caps["stdout"]) is not None
        else:
            monitor_supported = False
            ap_mode = False
    else:
        ap_mode = None

    result = {
        "ok": True,
        "interface": interface,
        "current_mode": match.get("mode"),
        "monitor_supported": monitor_supported,
        "watch_mode": ap_mode,
        "channel": match.get("channel"),
        "mac": match.get("mac"),
        "injection_supported": injection,
        "note": ("Monitor support is what the driver advertises. Frame injection is reported as "
                 "unknown because confirming it means injecting frames, which needs an "
                 "authorised test."),
    }
    if monitor_supported is False:
        result["reason"] = (f"the driver for {interface} advertises no monitor mode, so this "
                            "adapter cannot capture; an external adapter is required")
    return result


def survey(interface: str = "") -> dict:
    """Survey the visible access points, from the system's own scan."""
    tag = platform_tag()
    if tag in ("linux", "termux") and shutil.which("iw"):
        argv = ["iw", "dev", interface, "scan"] if interface else ["iw", "dev"]
        if interface:
            result = run(argv, timeout=45)
            if result["ok"]:
                return {"ok": True, "access_points": _parse_iw_scan(result["stdout"]),
                        "backend": "iw dev scan", "interface": interface}
        result = run(["ip", "link"], timeout=10)
        if not result["ok"]:
            return {"ok": False, "reason": "no interface was named and none could be defaulted"}
    if shutil.which("netsh"):
        result = run(["netsh", "wlan", "show", "networks", "mode=bssid"], timeout=30)
        if result["ok"]:
            return {"ok": True, "access_points": _parse_netsh_scan(result["stdout"]),
                    "backend": "netsh wlan show networks", "interface": interface}
    if shutil.which("iwlist"):
        argv = ["iwlist", f"{interface}" if interface else "wlan0", "scanning"]
        result = run(argv, timeout=45)
        if result["ok"]:
            return {"ok": True, "access_points": _parse_iwlist_scan(result["stdout"]),
                    "backend": "iwlist scanning", "interface": interface}
    return {"ok": False, "reason": (
        "no scan tool could be read (looked for iw, netsh, iwlist). On a phone, `iw dev "
        "<iface> scan` needs the interface up and location permission granted.")}


def _parse_iw_scan(text: str) -> list:
    aps: list = []
    entry: dict = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("BSS "):
            if entry:
                aps.append(entry)
            entry = {"bssid": stripped.split(" ", 1)[1].split("(", 1)[0].strip()}
        elif stripped.startswith("freq:"):
            freq = stripped.split(" ", 1)[1]
            entry["frequency_mhz"] = freq
            entry["channel"] = _channel_from_freq(freq)
        elif stripped.startswith("signal:"):
            entry["signal_dbm"] = stripped.split(" ", 1)[1].strip()
        elif stripped.startswith("SSID:"):
            entry["ssid"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("RSN:") or stripped.startswith("WPA:"):
            entry["security"] = stripped.split(":", 1)[0]
        elif stripped.startswith("Authentication suites") and "security" not in entry:
            entry["security"] = "protected"
    if entry:
        aps.append(entry)
    return aps


def _parse_netsh_scan(text: str) -> list:
    aps: list = []
    entry: dict = {}
    for line in text.splitlines():
        if " : " in line:
            name, _, value = line.partition(" : ")
            name = name.strip()
            value = value.strip()
            if name.startswith("SSID"):
                if entry:
                    aps.append(entry)
                entry = {"ssid": value}
            elif name.startswith("BSSID"):
                entry["bssid"] = value
            elif name.startswith("Signal"):
                entry["signal"] = value
            elif name.startswith("Radio type"):
                entry["radio_type"] = value
            elif name.startswith("Authentication"):
                entry["authentication"] = value
            elif name.startswith("Cipher"):
                entry["cipher"] = value
    if entry:
        aps.append(entry)
    return aps


def _parse_iwlist_scan(text: str) -> list:
    aps: list = []
    entry: dict = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Cell "):
            if entry:
                aps.append(entry)
            entry = {"cell": stripped.split(" - ")[-1]}
        elif stripped.startswith("Address:"):
            entry["bssid"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("ESSID:"):
            entry["ssid"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Channel:"):
            entry["channel"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Quality=") or stripped.startswith("Signal level="):
            entry["signal"] = stripped.split("=", 1)[1].strip()
        elif "Encryption key:" in stripped:
            entry["encryption"] = stripped.split(":", 1)[1].strip()
    if entry:
        aps.append(entry)
    return aps


def _channel_from_freq(freq: str) -> str:
    match = re.search(r"(\d+)", freq)
    if not match:
        return freq
    value = int(match.group(1))
    if value == 2484:
        return "14"
    if value >= 5000:
        return str((value - 5000) // 5)
    if value >= 2400:
        return str((value - 2407) // 5)
    return str(value)


def list_capture_tools() -> dict:
    """Which capture and crack tools are installed, with their install hint."""
    return available(["aircrack-ng", "airodump-ng", "aireplay-ng", "wifite", "bettercap",
                      "hcxdumptool", "hcxpcapngtool", "hashcat", "john", "reaver", "bully",
                      "airgeddon", "iw", "tshark"])
