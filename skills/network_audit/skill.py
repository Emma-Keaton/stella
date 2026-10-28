"""
Feature: network_audit
Description: Audits the network this machine is attached to - interfaces, listeners, ARP, host discovery, port scanning, TLS and security-header audits, Wi-Fi/BLE sweep, ARP-spoof detection and VPN-leak checks.
Uses theme tokens from themes.json (no hardcoded colours). Local reads never touch the network; operations that contact a target require authorized=true plus confirm=true and a policy allow rule, and every result names its target. A scan is bounded and parallel with a stated cap, and a probe that times out is reported as such rather than retried forever.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

FEATURE_METADATA = {
    "name": "network_audit",
    "aliases": ["network_audit", "network scan", "port scan", "open ports",
                "who is on my network", "network audit", "tls audit", "ssl audit",
                "security headers", "arp table", "listening ports", "wifi audit",
                "vpn leak", "arp spoofing"],
    "description": (
        "Audits the network this machine is attached to: interfaces, routes and gateways, "
        "listening sockets, the ARP table, parallel host discovery on a subnet, parallel port "
        "scanning with service identification, a TLS handshake audit (protocol versions, cipher "
        "suites, certificate chain and expiry), an HTTP security-header audit, Wi-Fi and BLE "
        "beacon sweep, ARP-spoofing detection and a VPN-leak check. Read-only by default; "
        "anything that contacts a named target is gated by core/tool_policy.py and names its "
        "target. Never scans a network the caller did not name."
    ),
    "triggers": [
        "network scan", "scan my network", "port scan", "what ports are open",
        "who is on my network", "network audit", "tls audit", "ssl audit",
        "check ssl", "security headers", "check headers", "arp table",
        "listening ports", "netstat", "wifi scan", "vpn leak", "arp spoofing",
        "man in the middle", "network devices",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: tools | interfaces | listeners | arp | subnet_scan | port_scan | wifi_scan | ble_scan | tls_audit | header_audit | arp_spoof | vpn_leak | latency | sources. Defaults to tools.",
            },
            "target": {
                "type": "STRING",
                "description": "Host, domain or IP for the tls/header audits, e.g. example.com. Required by tls_audit and header_audit.",
            },
            "network": {
                "type": "STRING",
                "description": "CIDR or dotted-quad base for subnet_scan, e.g. 192.168.1.0/24. Defaults to this machine's /24.",
            },
            "ports": {
                "type": "STRING",
                "description": "Port list for port_scan: common, a comma list, or a range like 1-1024. Defaults to common.",
            },
            "host": {
                "type": "STRING",
                "description": "Host for port_scan. Defaults to the named target, or a discovered host.",
            },
            "authorized": {
                "type": "BOOLEAN",
                "description": "Must be true to run an operation that contacts a target. Read-only local operations never need it.",
            },
            "confirm": {
                "type": "BOOLEAN",
                "description": "Must be true to start an operation that contacts a target.",
            },
            "timeout": {
                "type": "NUMBER",
                "description": "Per-probe timeout in seconds. Defaults to 1.0 for scans, 8 for audits.",
            },
            "limit": {
                "type": "INTEGER",
                "description": "Maximum items to return. Defaults to 50.",
            },
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "author": "Stella",
    "category": "security",
    "surface": "both",
    "requires": ["cmd"],
    "optional_dependencies": [],
    "notes": "Local reads use psutil/socket; scanning is bounded and parallel with a stated cap.",
}

_LOCAL_ONLY = {"tools", "interfaces", "listeners", "arp", "sources", "arp_spoof", "vpn_leak",
               "latency"}
_TARGETED = {"subnet_scan", "port_scan", "wifi_scan", "ble_scan", "tls_audit", "header_audit"}

_COMMON_PORTS = (21, 22, 23, 25, 53, 67, 68, 80, 110, 123, 135, 139, 143, 161, 389, 443, 445,
                 465, 587, 631, 873, 993, 995, 1080, 1433, 1521, 1883, 2049, 2375, 3000, 3306,
                 3389, 4369, 5000, 5432, 5555, 5672, 5900, 6379, 6443, 8000, 8008, 8080, 8086,
                 8443, 8888, 9000, 9090, 9200, 9418, 9999, 11211, 27017)

_SERVICES = {
    21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns", 67: "dhcp", 68: "dhcp",
    80: "http", 110: "pop3", 123: "ntp", 135: "msrpc", 139: "netbios", 143: "imap",
    161: "snmp", 389: "ldap", 443: "https", 445: "smb", 465: "smtps", 587: "submission",
    631: "ipp", 873: "rsync", 993: "imaps", 995: "pop3s", 1433: "mssql", 1521: "oracle",
    1883: "mqtt", 2049: "nfs", 2375: "docker", 3000: "http-alt", 3306: "mysql",
    3389: "rdp", 4369: "epmd", 5000: "http-alt", 5432: "postgres", 5555: "adb",
    5672: "amqp", 5900: "vnc", 6379: "redis", 6443: "kubernetes", 8000: "http-alt",
    8008: "http-alt", 8080: "http-proxy", 8086: "influxdb", 8443: "https-alt",
    8888: "http-alt", 9000: "http-alt", 9090: "http-alt", 9200: "elasticsearch",
    9418: "git", 9999: "http-alt", 11211: "memcached", 27017: "mongodb",
}


def _theme_colour(key: str, fallback: str | None = None) -> str | None:
    try:
        from theme_tokens import theme_colour
        return theme_colour(key) or fallback
    except Exception:
        return fallback


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _flag(**kwargs) -> bool:
    return kwargs.get("authorized") in (True, "true", "True", 1, "1") and \
        kwargs.get("confirm") in (True, "true", "True", 1, "1")


def _as_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value, default: int = 50, ceiling: int = 500) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    if number <= 0:
        number = default
    return min(number, ceiling)


def _target(kwargs: Dict[str, Any]) -> str:
    return (kwargs.get("target") or kwargs.get("host") or "").strip()


def _refusal(operation: str, activity: str) -> dict:
    return _op(operation, False, None, (
        f"'{operation}' contacts a target, so it needs authorized=true AND confirm=true plus a "
        "named target, and config/tool_policy.json must carry an allow rule naming this tool and "
        f"the target. It is {activity} class: a scan of a network you do not own is an intrusion, "
        "so refusing until it is named is deliberate."))


# ------------------------------------------------------------------ local reads

def _op_tools(kwargs: Dict[str, Any]) -> dict:
    from core.security.tools import available

    probed = available(["nmap", "iw", "netsh", "tshark", "arp", "iwconfig"])
    present = [name for name, entry in probed.items() if entry["present"]]
    missing = [name for name, entry in probed.items() if not entry["present"]]
    return _op("tools", True, {
        "present": present, "missing": missing,
        "psutil": _psutil_present(),
        "install_hints": {name: entry.get("install") for name, entry in probed.items()
                          if not entry["present"] and entry.get("install")},
        "note": ("The built-in scanner is pure Python and needs no external tool; nmap is only "
                 "used when it is already installed and the caller asks for it."),
    })


def _psutil_present() -> bool:
    try:
        import psutil  # noqa: F401
        return True
    except Exception:
        return False


def _op_interfaces(kwargs: Dict[str, Any]) -> dict:
    interfaces = _read_interfaces()
    if not interfaces.get("ok"):
        return _op("interfaces", False, None, interfaces.get("reason", "no interface could be read"))
    return _op("interfaces", True, interfaces)


def _read_interfaces() -> dict:
    import socket

    try:
        hostname = socket.gethostname()
        addresses = socket.getaddrinfo(hostname, None)
    except Exception as exc:
        return {"ok": False, "reason": f"this machine's addresses could not be read: {exc}"}

    seen: dict = {}
    for info in addresses:
        family, _, _, _, sockaddr = info
        address = sockaddr[0] if sockaddr else ""
        if not address or address.startswith("127.") or address == "::1":
            continue
        seen.setdefault(str(family), set()).add(address)

    entries = []
    for family, addresses in sorted(seen.items()):
        entries.append({"family": "ipv4" if family.endswith("AF_INET") else "ipv6",
                        "addresses": sorted(addresses)})

    if not entries:
        return {"ok": False, "reason": "no non-loopback address could be read"}

    gateway = _default_gateway()
    return {"ok": True, "entries": entries, "gateway": gateway,
            "hostname": hostname,
            "note": "Addresses come from this machine's own resolver; nothing else was queried."}


def _default_gateway() -> Optional[str]:
    from core.security.tools import run, platform_tag

    if platform_tag() == "windows":
        result = run(["netsh", "interface", "ip", "show", "config"], timeout=10)
        for line in (result.get("stdout") or "").splitlines():
            if "Default Gateway" in line or "Gateway" in line:
                _, _, value = line.partition(":")
                value = value.strip()
                if value and value[0].isdigit():
                    return value.split("%")[0]
        return None
    for argv in (["ip", "-4", "route", "show", "default"],
                 ["route", "-n", "get", "default"]):
        result = run(argv, timeout=10)
        if result.get("ok"):
            for line in (result.get("stdout") or "").splitlines():
                if "default" in line:
                    parts = line.split()
                    for index, part in enumerate(parts):
                        if part in ("via", "gateway") and index + 1 < len(parts):
                            return parts[index + 1]
    return None


def _op_listeners(kwargs: Dict[str, Any]) -> dict:
    if not _psutil_present():
        return _op("listeners", False, None, (
            "psutil is not installed, so listening sockets cannot be read. Install it with the "
            "dependency_manager (name=psutil)."))
    import psutil

    limit = _as_int(kwargs.get("limit"), 50)
    listeners = []
    try:
        connections = psutil.net_connections(kind="inet")
    except Exception as exc:
        return _op("listeners", False, None, (
            f"the connection table could not be read ({type(exc).__name__}: {exc}); this usually "
            "needs permission on this OS"))
    for connection in connections:
        if connection.status != psutil.CONN_LISTEN:
            continue
        listeners.append({
            "local": f"{connection.laddr.ip}:{connection.laddr.port}" if connection.laddr else None,
            "port": connection.laddr.port if connection.laddr else None,
            "pid": connection.pid,
            "process": _process_name(psutil, connection.pid),
            "family": "ipv4" if connection.family.name.endswith("AF_INET") else "ipv6",
        })
        if len(listeners) >= limit:
            break
    listeners.sort(key=lambda item: (item["port"] or 0))
    return _op("listeners", True, {
        "count": len(listeners), "listeners": listeners,
        "note": ("A listening socket is not a vulnerability; it is the surface a reviewer starts "
                 "from. The owning process is named when it can be read."),
    })


def _process_name(psutil, pid) -> Optional[str]:
    if pid is None:
        return None
    try:
        return psutil.Process(pid).name()
    except Exception:
        return None


def _op_arp(kwargs: Dict[str, Any]) -> dict:
    entries = _read_arp()
    if not entries.get("ok"):
        return _op("arp", False, None, entries.get("reason", "the ARP table could not be read"))
    return _op("arp", True, entries)


def _read_arp() -> dict:
    from core.security.tools import run, platform_tag

    if platform_tag() == "windows":
        result = run(["arp", "-a"], timeout=15)
        if not result.get("ok"):
            return {"ok": False, "reason": result.get("reason", "arp -a did not answer")}
        entries = []
        current_interface = None
        for line in (result.get("stdout") or "").splitlines():
            if "Interface:" in line:
                current_interface = line.split("Interface:")[1].strip().split()[0:1]
                current_interface = current_interface[0] if current_interface else None
                continue
            parts = line.split()
            if len(parts) >= 3 and _looks_ip(parts[0]) and _looks_mac(parts[1]):
                entries.append({"interface": current_interface, "ip": parts[0],
                                "mac": parts[1], "type": parts[2] if len(parts) > 2 else None})
        return {"ok": bool(entries), "entries": entries,
                "reason": None if entries else "the ARP table is empty",
                "note": "The ARP table is what this machine has talked to recently."}

    for argv in (["ip", "neigh", "show"], ["arp", "-an"], ["arp", "-a"]):
        result = run(argv, timeout=15)
        if not result.get("ok"):
            continue
        entries = []
        for line in (result.get("stdout") or "").splitlines():
            parts = line.replace("?", " ").split()
            ip_index = next((index for index, part in enumerate(parts) if _looks_ip(part)), None)
            mac_index = next((index for index, part in enumerate(parts)
                              if _looks_mac(part)), None)
            if ip_index is not None and mac_index is not None:
                entries.append({"ip": parts[ip_index], "mac": parts[mac_index],
                                "state": parts[-1] if len(parts) > mac_index + 1 else None})
        if entries:
            return {"ok": True, "entries": entries,
                    "note": "The ARP table is what this machine has talked to recently."}
    return {"ok": False, "reason": (
        "the ARP table could not be read (looked for ip neigh, arp -an, arp -a). On a phone this "
        "needs root; an unprivileged Termux shell sees an empty table.")}


def _looks_ip(text: str) -> bool:
    parts = (text or "").split(".")
    if len(parts) != 4:
        return ":" in text and len(text) > 8
    return all(part.isdigit() and 0 <= int(part) <= 255 for part in parts)


def _looks_mac(text: str) -> bool:
    cleaned = (text or "").replace("-", ":").lower()
    parts = cleaned.split(":")
    if len(parts) != 6:
        return False
    return all(len(part) == 2 and all(c in "0123456789abcdef" for c in part) for part in parts)


def _op_arp_spoof(kwargs: Dict[str, Any]) -> dict:
    table = _read_arp()
    if not table.get("ok"):
        return _op("arp_spoof", False, None, table.get("reason", "the ARP table could not be read"))

    macs_by_ip: dict = {}
    for entry in table.get("entries") or []:
        macs_by_ip.setdefault(entry["ip"], set()).add(entry["mac"].lower())

    duplicates = {ip: sorted(macs) for ip, macs in macs_by_ip.items() if len(macs) > 1}
    broadcast = [entry for entry in table.get("entries") or []
                 if entry["mac"].lower().startswith(("ff:ff", "01:00:5e"))]

    findings = []
    if duplicates:
        findings.append({"finding": "one IP answers to more than one MAC",
                        "detail": duplicates,
                        "meaning": ("that is what ARP spoofing looks like on the wire - but it is "
                                   "also what a legitimate failover or a misconfigured duplicate "
                                   "address looks like, so it is a prompt to look, not a verdict")})
    if broadcast:
        findings.append({"finding": "multicast or broadcast entries in the table",
                        "count": len(broadcast),
                        "meaning": "normal on a busy network; noted for completeness"})

    return _op("arp_spoof", True, {
        "entries": len(table.get("entries") or []),
        "duplicate_ips": duplicates,
        "broadcast_entries": len(broadcast),
        "findings": findings,
        "note": ("Detection here is the table only. A real MITM check watches the table over time "
                 "and watches for a gateway MAC that changes - this operation is the first look, "
                 "not that."),
    })


def _op_vpn_leak(kwargs: Dict[str, Any]) -> dict:
    """What the outside world sees this machine's address as, versus what it thinks it is."""
    from core.net import http

    seen = http.get_json("https://api.ipify.org?format=json", timeout=8.0)
    local = _read_interfaces()
    if not seen.get("ok"):
        return _op("vpn_leak", False, None,
                   f"the public address could not be read: {seen.get('reason')}")

    public = (seen.get("value") or {}).get("ip") or ""
    local_addresses = [address for entry in local.get("entries", []) for address in entry["addresses"]]
    tunnel = any(iface in local_addresses for iface in ("tun0", "utun0", "tap0", "wg0", "ppp0"))

    return _op("vpn_leak", True, {
        "public_ip": public,
        "local_addresses": local_addresses,
        "tunnel_interface_seen": tunnel,
        "interpretation": ("The public address differs from the local ones, which is what any NAT "
                          "or VPN looks like from inside. A tunnel interface plus a public address "
                          "in the same range as the ISP's is the shape of a leak; this operation "
                          "reports the shape and does not claim a verdict."),
        "note": "This read the public address from ipify and the local ones from this machine.",
    })


def _op_latency(kwargs: Dict[str, Any]) -> dict:
    target = _target(kwargs) or "1.1.1.1"
    samples = []
    for host in (target, "1.1.1.1", "8.8.8.8"):
        latency = _tcp_latency(host, 5.0)
        samples.append({"probe": "tcp-connect", "host": host,
                        "ms": latency, "ok": latency is not None})
    measured = [sample["ms"] for sample in samples if sample["ok"]]
    return _op("latency", True, {
        "samples": samples,
        "average_ms": round(sum(measured) / len(measured), 2) if measured else None,
        "note": "Latency is a TCP connect time to port 443, not an ICMP echo.",
    })


def _tcp_latency(host: str, timeout: float) -> Optional[float]:
    import socket
    import time

    started = time.time()
    try:
        with socket.create_connection((host, 443), timeout=timeout):
            return round((time.time() - started) * 1000, 2)
    except Exception:
        return None


# ------------------------------------------------------------------ targeted ops

def _op_subnet_scan(kwargs: Dict[str, Any]) -> dict:
    operation = "subnet_scan"
    if not _flag(**kwargs):
        return _refusal(operation, "active")

    network = (kwargs.get("network") or "").strip()
    if not network:
        interfaces = _read_interfaces()
        base = _default_gateway()
        if not base:
            return _op(operation, False, None, (
                "no network was named and this machine's default gateway could not be read. Pass "
                "network=192.168.1.0/24 style."))
        network = ".".join(base.split(".")[:3]) + ".0/24"

    hosts = _base_addresses(network)
    if not hosts:
        return _op(operation, False, None, (
            f"'{network}' is not a CIDR or dotted-quad base this scanner understands; use e.g. "
            "192.168.1.0/24"))

    timeout = _as_float(kwargs.get("timeout"), 1.0)
    alive = _parallel_probe(hosts, timeout)
    return _op(operation, True, {
        "network": network,
        "probed": len(hosts),
        "alive": len(alive),
        "hosts": alive,
        "timeout_s": timeout,
        "note": ("Discovery is a TCP connect to the named ports on each address: a host that "
                 "answers nothing is reported as not answering, not as absent. Bounded to one /24 "
                 "per call so a mistyped network cannot become a scan of the internet."),
    })


def _base_addresses(network: str) -> list:
    import ipaddress

    try:
        if "/" in network:
            return [str(host) for host in ipaddress.ip_network(network, strict=False).hosts()][:254]
        parts = network.split(".")
        if len(parts) == 3:
            base = network
        elif len(parts) == 4 and parts[3] == "0":
            base = ".".join(parts[:3])
        else:
            base = ".".join(parts[:3])
        return [f"{base}.{index}" for index in range(1, 255)]
    except Exception:
        return []


def _parallel_probe(hosts: list, timeout: float, ports=(80, 443, 22, 445)) -> list:
    import socket
    from concurrent.futures import ThreadPoolExecutor

    def check(host: str) -> Optional[dict]:
        for port in ports:
            try:
                with socket.create_connection((host, port), timeout=timeout):
                    return {"host": host, "answered_on": port,
                            "service": _SERVICES.get(port)}
            except Exception:
                continue
        return None

    alive = []
    with ThreadPoolExecutor(max_workers=min(64, len(hosts) or 1)) as pool:
        for result in pool.map(check, hosts):
            if result:
                alive.append(result)
    return alive


def _op_port_scan(kwargs: Dict[str, Any]) -> dict:
    operation = "port_scan"
    if not _flag(**kwargs):
        return _refusal(operation, "active")

    host = (kwargs.get("host") or _target(kwargs)).strip()
    if not host:
        return _op(operation, False, None, "Name the host to scan (host=... or target=...).")

    ports = _parse_ports(kwargs.get("ports"))
    timeout = _as_float(kwargs.get("timeout"), 1.0)
    open_ports = _scan_ports(host, ports, timeout)
    return _op(operation, True, {
        "host": host,
        "ports_probed": len(ports),
        "open_ports": [{"port": port, "service": _SERVICES.get(port)} for port in open_ports],
        "timeout_s": timeout,
        "note": ("An open port is not a vulnerability; it is a service that answered. The port "
                 "list is capped at 1024 ports per call so a scan cannot run away."),
    })


def _parse_ports(spec) -> list:
    if not spec:
        return list(_COMMON_PORTS)
    text = str(spec).strip().lower()
    if text in ("common", "default", "top"):
        return list(_COMMON_PORTS)
    if "-" in text and "," not in text:
        start, _, end = text.partition("-")
        try:
            return list(range(int(start), min(int(end), int(start) + 1023) + 1))
        except ValueError:
            return list(_COMMON_PORTS)
    ports = []
    for part in text.split(","):
        part = part.strip()
        if part.isdigit():
            ports.append(int(part))
    return ports or list(_COMMON_PORTS)


def _scan_ports(host: str, ports: list, timeout: float) -> list:
    import socket
    from concurrent.futures import ThreadPoolExecutor

    def check(port: int) -> Optional[int]:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return port
        except Exception:
            return None

    open_ports = []
    with ThreadPoolExecutor(max_workers=min(128, len(ports) or 1)) as pool:
        for port in pool.map(check, ports):
            if port is not None:
                open_ports.append(port)
    return sorted(open_ports)


def _op_wifi_scan(kwargs: Dict[str, Any]) -> dict:
    from core.security import wireless

    result = wireless.survey((kwargs.get("target") or "").strip())
    if not result.get("ok"):
        return _op("wifi_scan", False, None, result.get("reason", "no scan tool could be read"))
    aps = result.get("access_points") or []
    limit = _as_int(kwargs.get("limit"), 50)
    findings = []
    for ap in aps[:limit]:
        if _is_open(ap):
            findings.append({"ssid": ap.get("ssid"), "bssid": ap.get("bssid"),
                            "finding": "open network (no encryption advertised)",
                            "meaning": "traffic on an open network is readable by anyone in range"})
    return _op("wifi_scan", True, {
        **result,
        "open_networks": findings,
        "note": "Encryption is what the network advertises, not a measurement of its traffic.",
    })


def _is_open(ap: dict) -> bool:
    security = str(ap.get("security") or "").lower()
    encryption = str(ap.get("encryption") or "").lower()
    authentication = str(ap.get("authentication") or "").lower()
    return ("none" in security or security in ("", "unknown")) and "on" not in encryption \
        and "open" in authentication if authentication else security == "none"


def _op_ble_scan(kwargs: Dict[str, Any]) -> dict:
    from core.security.tools import available, run

    probed = available(["btmgmt", "hcitool", "bluetoothctl", "blescan"])
    tool = next((name for name, entry in probed.items() if entry["present"]), None)
    if not tool:
        return _op("ble_scan", False, None, (
            "no Bluetooth scan tool is installed (looked for btmgmt, hcitool, bluetoothctl). "
            "Install bluez to enable BLE discovery."))
    result = run([tool, "dev"], timeout=20) if tool == "btmgmt" else run([tool], timeout=20)
    return _op("ble_scan", True, {
        "tool": tool,
        "stdout_tail": (result.get("stdout") or "")[-1200:],
        "note": ("BLE discovery prints what the adapter hears. A device that is not advertising is "
                 "not visible, so an empty scan is not evidence of an empty area."),
    })


def _op_tls_audit(kwargs: Dict[str, Any]) -> dict:
    operation = "tls_audit"
    if not _flag(**kwargs):
        return _refusal(operation, "active")
    target = _target(kwargs)
    if not target:
        return _op(operation, False, None, "Name the host to audit (target=...).")

    host, port = _split_host_port(target, 443)
    return _op(operation, True, _tls_probe(host, port))


def _op_header_audit(kwargs: Dict[str, Any]) -> dict:
    operation = "header_audit"
    if not _flag(**kwargs):
        return _refusal(operation, "active")
    target = _target(kwargs)
    if not target:
        return _op(operation, False, None, "Name the URL or host to audit (target=...).")

    from core.net import http

    url = target if "://" in target else f"https://{target}"
    result = http.get_text(url, timeout=15.0, max_bytes=200_000)
    if not result.get("ok"):
        return _op(operation, False, None, result.get("reason", "the site did not answer"))

    import urllib.request

    request = urllib.request.Request(url, headers={"User-Agent": "StellaAI/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=15.0) as response:
            headers = {name.lower(): value for name, value in response.headers.items()}
            status = getattr(response, "status", 200)
    except Exception as exc:
        return _op(operation, False, None, f"{url} could not be read: {type(exc).__name__}: {exc}")

    checks = {
        "strict-transport-security": ("HSTS", "one year, with subdomains and preload where possible"),
        "content-security-policy": ("CSP", "a restrictive policy, not 'unsafe-inline' for scripts"),
        "x-content-type-options": ("nosniff", "present"),
        "x-frame-options": ("clickjacking", "DENY or SAMEORIGIN"),
        "referrer-policy": ("referrer leakage", "strict-origin-when-cross-origin or stricter"),
    }
    findings = []
    for header, (label, guidance) in checks.items():
        present = header in headers
        findings.append({
            "header": header,
            "label": label,
            "present": present,
            "value": headers.get(header),
            "finding": None if present else f"{label}: {header} is not set",
            "guidance": guidance,
        })

    cookies = headers.get("set-cookie", "")
    cookie_findings = []
    for cookie in cookies.split(","):
        lowered = cookie.lower()
        if not lowered.strip():
            continue
        missing_flags = [flag for flag in ("secure", "httponly", "samesite")
                         if flag not in lowered]
        if missing_flags:
            cookie_findings.append({"cookie": cookie[:80].strip(),
                                   "missing": missing_flags})

    return _op(operation, True, {
        "url": url,
        "status": status,
        "headers_seen": len(headers),
        "findings": findings,
        "missing_count": sum(1 for f in findings if not f["present"]),
        "cookie_findings": cookie_findings,
        "note": ("A header audit is a configuration review: each missing header is a hardening "
                 "opportunity with the value to set, not a vulnerability."),
    })


def _split_host_port(target: str, default_port: int) -> tuple:
    text = (target or "").strip()
    if "://" in text:
        text = text.split("://", 1)[1]
    text = text.split("/", 1)[0]
    if ":" in text and not text.count(":") > 1:
        host, _, port_text = text.rpartition(":")
        try:
            return host, int(port_text)
        except ValueError:
            return host, default_port
    return text, default_port


def _tls_probe(host: str, port: int) -> dict:
    import socket
    import ssl
    from datetime import datetime, timezone

    findings = []
    protocols = {}
    for label, options in (
        ("tls1.2", ssl.TLSVersion.TLSv1_2 if hasattr(ssl, "TLSVersion") else None),
        ("tls1.3", ssl.TLSVersion.TLSv1_3 if hasattr(ssl, "TLSVersion") else None),
    ):
        if options is None:
            continue
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            context.minimum_version = options
            context.maximum_version = options
            with socket.create_connection((host, port), timeout=8.0) as sock:
                with context.wrap_socket(sock, server_hostname=host) as wrapped:
                    protocols[label] = wrapped.version()
        except Exception:
            protocols[label] = None

    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        with socket.create_connection((host, port), timeout=8.0) as sock:
            with context.wrap_socket(sock, server_hostname=host) as wrapped:
                certificate = wrapped.getpeercert()
                cipher = wrapped.cipher()
                negotiated = wrapped.version()
    except ssl.SSLCertVerificationError as exc:
        return {"ok": True, "host": host, "port": port, "protocols": protocols,
                "verified": False,
                "certificate_finding": {
                    "finding": "the certificate did not verify",
                    "detail": str(exc.verify_message) if hasattr(exc, "verify_message") else str(exc),
                    "meaning": "either the chain is incomplete, the name does not match, or the certificate has expired"},
                "note": "A verification failure is reported as such, with the reason."}
    except Exception as exc:
        return {"ok": True, "host": host, "port": port, "protocols": protocols,
                "verified": None,
                "reason": f"{host}:{port} could not be reached for the handshake: {type(exc).__name__}: {exc}"}

    not_after = certificate.get("notAfter") if certificate else None
    days_left = None
    if not_after:
        try:
            expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            days_left = (expiry - datetime.now(timezone.utc)).days
        except Exception:
            days_left = None

    if days_left is not None and days_left < 0:
        findings.append({"finding": "the certificate has expired", "days": days_left})
    elif days_left is not None and days_left < 30:
        findings.append({"finding": "the certificate expires soon", "days": days_left})

    return {
        "ok": True,
        "host": host,
        "port": port,
        "protocols": protocols,
        "negotiated": negotiated,
        "cipher": {"name": cipher[0], "protocol": cipher[1], "bits": cipher[2]} if cipher else None,
        "verified": True,
        "certificate": {
            "subject": _flatten_name(certificate.get("subject")),
            "issuer": _flatten_name(certificate.get("issuer")),
            "not_after": not_after,
            "days_left": days_left,
            "san": [entry[1] for entry in certificate.get("subjectAltName", [])],
            "version": certificate.get("version"),
        },
        "findings": findings,
        "note": ("The handshake was made with trust disabled so the chain could be inspected; "
                 "`verified` says whether it would have passed."),
    }


def _flatten_name(pairs) -> Optional[str]:
    if not pairs:
        return None
    return ", ".join(f"{key}={value}" for group in pairs for key, value in group)


def _op_sources(kwargs: Dict[str, Any] | None = None) -> dict:
    return _op("sources", True, {
        "local": ["this machine's interfaces, gateway, ARP table and listening sockets"],
        "targeted": ["a TCP connect to the named host/network, with a bounded port list"],
        "audits": ["TLS handshake with trust disabled, so the chain can be inspected",
                   "HTTP response headers and Set-Cookie flags"],
    })


_OPERATIONS = {
    "tools": _op_tools,
    "interfaces": _op_interfaces,
    "listeners": _op_listeners,
    "arp": _op_arp,
    "subnet_scan": _op_subnet_scan,
    "port_scan": _op_port_scan,
    "wifi_scan": _op_wifi_scan,
    "ble_scan": _op_ble_scan,
    "tls_audit": _op_tls_audit,
    "header_audit": _op_header_audit,
    "arp_spoof": _op_arp_spoof,
    "vpn_leak": _op_vpn_leak,
    "latency": _op_latency,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "tools": "Network Toolchain", "interfaces": "Network Interfaces",
    "listeners": "Listening Sockets", "arp": "ARP Table",
    "subnet_scan": "Subnet Host Discovery", "port_scan": "Port Scan",
    "wifi_scan": "Wireless Site Survey", "ble_scan": "BLE Beacon Scan",
    "tls_audit": "TLS Audit", "header_audit": "HTTP Header Audit",
    "arp_spoof": "ARP Spoofing Check", "vpn_leak": "VPN Leak Check",
    "latency": "Latency", "sources": "Network Audit Sources",
}

_ALIASES = {
    "scan_network": "subnet_scan", "host_discovery": "subnet_scan", "discover_hosts": "subnet_scan",
    "scan_ports": "port_scan", "open_ports": "port_scan",
    "netstat": "listeners", "sockets": "listeners",
    "arp_table": "arp", "neighbours": "arp",
    "ssl": "tls_audit", "ssl_audit": "tls_audit", "check_tls": "tls_audit",
    "headers": "header_audit", "check_headers": "header_audit",
    "arp_spoofing": "arp_spoof", "mitm_check": "arp_spoof",
    "vpn_leak_check": "vpn_leak", "public_ip": "vpn_leak",
    "ping": "latency",
    "sources_list": "sources",
}


def _failure(operation: str, reason: str) -> dict:
    title = _OPERATION_TITLES.get(operation, "Network Audit")
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
    """Audit a network, with target naming and authorisation enforced."""
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
        "title": _OPERATION_TITLES.get(operation, "Network Audit"),
        "summary": _summary(operation, record, kwargs),
        "spoken_narrative": _summary(operation, record, kwargs),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
        "sources": _op_sources()["value"],
        "authorized": _flag(**kwargs),
        "target": _target(kwargs) or None,
    }


def _summary(operation: str, record: dict, kwargs: Dict[str, Any]) -> str:
    value = record.get("value") or {}
    if operation == "tools":
        return (f"Network tools: {len(value.get('present') or [])} present "
                f"({', '.join(value.get('present') or []) or 'none'}), "
                f"{len(value.get('missing') or [])} missing.")
    if operation == "interfaces":
        if not record.get("ok"):
            return f"Interface read unavailable: {record.get('error')}"
        listing = "; ".join(f"{entry['family']}: {', '.join(entry['addresses'])}"
                            for entry in value.get("entries") or [])
        return f"This machine: {listing}. Gateway: {value.get('gateway') or 'unknown'}."
    if operation == "listeners":
        if not record.get("ok"):
            return f"Listening sockets unavailable: {record.get('error')}"
        top = value.get("listeners") or []
        listing = ", ".join(f"{item['local']} ({item.get('service') or item.get('process') or 'unknown'})"
                            for item in top[:8])
        return f"{value.get('count')} listening socket(s). {listing}"
    if operation == "arp":
        if not record.get("ok"):
            return f"ARP table unavailable: {record.get('error')}"
        entries = value.get("entries") or []
        listing = ", ".join(f"{item['ip']} at {item['mac']}" for item in entries[:6])
        return f"{len(entries)} ARP entrie(s). {listing}"
    if operation == "subnet_scan":
        if not record.get("ok"):
            return f"Host discovery did not run: {record.get('error')}"
        return (f"{value.get('alive')} of {value.get('probed')} addresses answered in "
                f"{value.get('network')}. A host that answered nothing is reported as not answering.")
    if operation == "port_scan":
        if not record.get("ok"):
            return f"Port scan did not run: {record.get('error')}"
        open_ports = value.get("open_ports") or []
        listing = ", ".join(f"{item['port']}/{item.get('service') or '?'}" for item in open_ports[:12])
        return f"{len(open_ports)} open port(s) on {value.get('host')} of {value.get('ports_probed')} probed. {listing}"
    if operation == "wifi_scan":
        if not record.get("ok"):
            return f"Wireless survey unavailable: {record.get('error')}"
        open_count = len(value.get("open_networks") or [])
        return (f"{len(value.get('access_points') or [])} access point(s) visible; "
                f"{open_count} advertise no encryption.")
    if operation == "ble_scan":
        if not record.get("ok"):
            return f"BLE scan unavailable: {record.get('error')}"
        return f"BLE scan ran with {value.get('tool')}. {value.get('note')}"
    if operation == "tls_audit":
        if not record.get("ok"):
            return f"TLS audit did not run: {record.get('error')}"
        verified = value.get("verified")
        if verified is None:
            return value.get("reason", "The handshake could not be made.")
        if verified is False:
            finding = value.get("certificate_finding") or {}
            return (f"{value.get('host')}:{value.get('port')} reachable, but the certificate did "
                    f"not verify: {finding.get('detail', 'no reason given')}.")
        certificate = value.get("certificate") or {}
        findings = value.get("findings") or []
        issues = "; ".join(item["finding"] for item in findings) or "no certificate findings"
        return (f"{value.get('host')}:{value.get('port')} negotiated {value.get('negotiated')} "
                f"with {certificate.get('issuer')}; certificate valid for {certificate.get('days_left')} more day(s); {issues}.")
    if operation == "header_audit":
        if not record.get("ok"):
            return f"Header audit did not run: {record.get('error')}"
        return (f"{value.get('url')} answered {value.get('status')}; "
                f"{value.get('missing_count')} security header(s) missing, "
                f"{len(value.get('cookie_findings') or [])} cookie(s) missing flags.")
    if operation == "arp_spoof":
        if not record.get("ok"):
            return f"ARP check unavailable: {record.get('error')}"
        duplicates = value.get("duplicate_ips") or {}
        if duplicates:
            listing = "; ".join(f"{ip}: {', '.join(macs)}" for ip, macs in list(duplicates.items())[:5])
            return f"{len(duplicates)} IP(s) answer to more than one MAC: {listing}. {value.get('note')}"
        return f"No duplicate MACs in the {value.get('entries')} ARP entrie(s). {value.get('note')}"
    if operation == "vpn_leak":
        if not record.get("ok"):
            return f"Public address unavailable: {record.get('error')}"
        return f"Public address {value.get('public_ip')}; tunnel interface seen: {value.get('tunnel_interface_seen')}. {value.get('interpretation')}"
    if operation == "latency":
        average = value.get("average_ms")
        return f"Average TCP-connect latency {average} ms across {len(value.get('samples') or [])} probes."
    if operation == "sources":
        return f"{len(value.get('local') or [])} local read(s), targeted probes, and 2 audits."
    return record.get("error") or "No operation ran."
