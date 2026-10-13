"""stella_connect.pairing_flow - one pairing model for every device and edition.

Why this module exists
----------------------
Pairing used to be a one-way street: the desktop app hosted a gateway and a
phone joined it. The product needs to be symmetric - *any* Stella can host and
*any* Stella can join, whether that is phone-to-PC, PC-to-PC or phone-to-phone -
and the same flow has to ship in the public edition, not just the personal K2
build.

So the "how do I find and reach a peer" logic lives here, once, as a small
dependency-light model that the desktop service, the Android client and the
public build all consume:

* :class:`PairingTarget` - the single thing every method resolves to.
* :func:`from_qr` / :func:`to_qr_payload` - the versioned QR contract.
* :func:`manual` - the "type an address" method.
* :func:`discover` - the "find it on the network" method (mDNS browse).

All three methods produce a ``PairingTarget``; everything downstream (connect,
authenticate, exchange commands) is identical no matter how the peer was
found. That is what makes the three options behave the same for every pairing
of device types.

Imports of optional third-party packages (zeroconf, qrcode) are deferred to the
call site so this module imports cleanly on a minimal install.
"""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass, field, asdict
from typing import Any, Iterable

# Bumped only if the on-the-wire QR shape changes incompatibly. Apps should
# refuse a payload whose version they do not understand rather than guessing.
PAYLOAD_VERSION = 1
SERVICE_TYPE = "_STELLA._tcp.local."
DEFAULT_PORT = 8765

METHOD_QR = "qr"
METHOD_DISCOVER = "discover"
METHOD_MANUAL = "manual"


class PairingError(ValueError):
    """Raised when a payload or address cannot be turned into a target."""


@dataclass(slots=True)
class PairingTarget:
    """Everything needed to reach a peer, however it was found."""

    host: str
    port: int = DEFAULT_PORT
    pairing_token: str = ""
    pairing_code: str = ""
    name: str = ""
    platform: str = ""
    method: str = METHOD_MANUAL
    expires: int = 0
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Normalise eagerly so callers never have to.
        self.host = str(self.host or "").strip()
        try:
            self.port = int(self.port) if self.port else DEFAULT_PORT
        except (TypeError, ValueError):
            self.port = DEFAULT_PORT

    @property
    def ws_url(self) -> str:
        return f"ws://{self.host}:{self.port}/ws"

    @property
    def http_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def label(self) -> str:
        base = self.name or self.host
        return f"{base} ({self.host}:{self.port})"


def _coerce_port(value: Any, default: int = DEFAULT_PORT) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        return default
    return port if 0 < port < 65536 else default


def manual(host: str, port: int | str = DEFAULT_PORT, *,
           pairing_code: str = "", pairing_token: str = "",
           name: str = "") -> PairingTarget:
    """Build a target from a hand-typed address (the "Enter IP" method)."""
    host = str(host or "").strip()
    if not host:
        raise PairingError("an address is required")
    # Tolerate "host:port" typed as one string.
    if ":" in host and host.count(":") == 1:
        head, tail = host.split(":", 1)
        if tail.isdigit():
            host, port = head.strip(), _coerce_port(tail)
    return PairingTarget(
        host=host,
        port=_coerce_port(port),
        pairing_code=str(pairing_code or "").strip(),
        pairing_token=str(pairing_token or "").strip(),
        name=name,
        method=METHOD_MANUAL,
    )


def to_qr_payload(offer: dict[str, Any], *, name: str = "",
                  platform: str = "") -> dict[str, Any]:
    """Turn a gateway pairing offer into the canonical QR payload.

    The payload is self-describing and versioned so a future app can tell an
    old code from a new one. Extra keys in ``offer`` are preserved.
    """
    payload = {
        "stella": PAYLOAD_VERSION,
        "service": str(offer.get("service") or SERVICE_TYPE),
        "name": str(name or offer.get("name") or ""),
        "platform": str(platform or offer.get("platform") or ""),
        "host": str(offer.get("host") or ""),
        "port": _coerce_port(offer.get("port")),
        "pairing_token": str(offer.get("pairing_token") or ""),
        "pairing_code": str(offer.get("pairing_code") or ""),
        "expires": int(offer.get("expires") or 0),
    }
    return payload


def qr_text(payload: dict[str, Any]) -> str:
    """Serialise a QR payload to the exact string that gets encoded."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def from_qr(raw: str | bytes | dict[str, Any]) -> PairingTarget:
    """Parse a scanned QR string (or an already-decoded dict) into a target."""
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, dict):
        data: Any = raw
    else:
        text = str(raw or "").strip()
        if not text:
            raise PairingError("empty QR payload")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise PairingError(f"not a Stella pairing code: {exc}") from exc

    if not isinstance(data, dict):
        raise PairingError("QR payload is not an object")

    # Accept both a versioned payload and a bare gateway offer.
    version = data.get("stella", data.get("version"))
    if version is not None and int(version) > PAYLOAD_VERSION:
        raise PairingError(
            f"this code was made by a newer Stella (v{version}); update to pair"
        )
    host = str(data.get("host") or "").strip()
    if not host:
        raise PairingError("pairing code has no host address")
    return PairingTarget(
        host=host,
        port=_coerce_port(data.get("port")),
        pairing_code=str(data.get("pairing_code") or "").strip(),
        pairing_token=str(data.get("pairing_token") or "").strip(),
        name=str(data.get("name") or ""),
        platform=str(data.get("platform") or ""),
        method=METHOD_QR,
        expires=int(data.get("expires") or 0),
    )


def local_addresses() -> list[str]:
    """Best-effort list of this machine's LAN addresses, for display/QR."""
    addrs: set[str] = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            addrs.add(s.getsockname()[0])
        finally:
            s.close()
    except Exception:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                addrs.add(ip)
    except Exception:
        pass
    return sorted(addrs)


def encode_qr_png(payload: dict[str, Any], *, box_size: int = 6,
                  border: int = 2) -> bytes | None:
    """Render the payload to PNG bytes for display. ``None`` if qrcode is absent."""
    try:
        import io
        import qrcode  # type: ignore
    except Exception:
        return None
    qr = qrcode.QRCode(box_size=box_size, border=border,
                       error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(qr_text(payload))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Discovery (method 2). The browser is injectable so this is testable without
# a live network, and so mobile can reuse the same shape.
# ---------------------------------------------------------------------------

class HostBrowser:
    """Interface for a discovery backend. Implementations yield raw service dicts."""

    def browse(self, timeout: float) -> Iterable[dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError


class ZeroconfBrowser(HostBrowser):
    """mDNS browser over ``_STELLA._tcp.local.`` using python-zeroconf."""

    def __init__(self, service_type: str = SERVICE_TYPE) -> None:
        self.service_type = service_type

    def browse(self, timeout: float) -> Iterable[dict[str, Any]]:
        try:
            from zeroconf import Zeroconf, ServiceBrowser, IPVersion  # type: ignore
        except Exception:
            return []
        found: list[dict[str, Any]] = []
        seen: set[tuple[str, int]] = set()

        class _Listener:
            def add_service(self, zc, type_, name):  # noqa: ANN001
                try:
                    info = zc.get_service_info(type_, name, timeout=int(timeout * 1000))
                except Exception:
                    info = None
                if not info:
                    return
                addresses = [socket.inet_ntoa(a) for a in (info.addresses or []) if len(a) == 4]
                host = addresses[0] if addresses else ""
                if not host:
                    return
                key = (host, int(info.port))
                if key in seen:
                    return
                seen.add(key)
                props = {k.decode("utf-8", "replace"): v.decode("utf-8", "replace")
                         for k, v in (info.properties or {}).items() if v is not None}
                found.append({
                    "name": props.get("name") or name.split(".")[0],
                    "host": host,
                    "port": int(info.port),
                    "platform": props.get("platform", ""),
                })

            def update_service(self, *a):  # noqa: ANN002
                pass

            def remove_service(self, *a):  # noqa: ANN002
                pass

        zc = None
        try:
            zc = Zeroconf(ip_version=IPVersion.V4Only)
            ServiceBrowser(zc, self.service_type, _Listener())
            import time
            time.sleep(max(0.2, timeout))
        except Exception:
            return found
        finally:
            if zc is not None:
                try:
                    zc.close()
                except Exception:
                    pass
        return found


def discover(timeout: float = 3.0, *, browser: HostBrowser | None = None) -> list[PairingTarget]:
    """Method 2: find Stella hosts on the local network (mDNS browse)."""
    browser = browser or ZeroconfBrowser()
    targets: list[PairingTarget] = []
    for item in browser.browse(timeout):
        host = str(item.get("host") or "").strip()
        if not host:
            continue
        targets.append(PairingTarget(
            host=host,
            port=_coerce_port(item.get("port")),
            name=str(item.get("name") or ""),
            platform=str(item.get("platform") or ""),
            method=METHOD_DISCOVER,
        ))
    return targets
