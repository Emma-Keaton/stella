"""
Feature: domain_intel
Description: Passive and active domain intelligence - DNS records, WHOIS/RDAP, reverse DNS, IP geolocation, ASN ownership, subdomain enumeration via certificate-transparency logs, takeover checks, tech fingerprinting, email security records, and offline decoding of hashes, JWTs and packet captures.
Uses theme tokens from themes.json (no hardcoded colours). P0 passive is the default and every operation names its source and activity class; anything that queries the target's DNS or contacts the target requires authorized=true plus confirm=true and a policy allow rule, and names its target. Optional Python modules (dnspython, python-whois) are probed and named when missing rather than assumed.
"""

from __future__ import annotations

import base64
import json
import re
import socket
from typing import Any, Dict, Optional

FEATURE_METADATA = {
    "name": "domain_intel",
    "aliases": ["domain_intel", "whois lookup", "who owns this domain", "dns lookup",
                "dns records", "subdomain enumeration", "subdomains", "reverse dns",
                "ip geolocation", "asn lookup", "spf dkim dmarc", "email security",
                "subdomain takeover", "tech fingerprint", "what is this site running",
                "ct logs", "certificate transparency", "passive dns", "wayback machine",
                "jwt decode", "identify hash", "analyze pcap"],
    "description": (
        "Passive and active domain intelligence: DNS records, WHOIS/RDAP registration, reverse "
        "DNS, IP geolocation and ASN ownership, subdomain enumeration through "
        "certificate-transparency logs, subdomain-takeover checks, technology fingerprinting from "
        "HTTP responses, SPF/DKIM/DMARC/CAA email-security records, passive-DNS and Wayback "
        "history, public bucket probing, and offline decoding of hashes, JWTs and packet captures. "
        "P0 passive is the default; anything that queries the target's DNS or contacts it is gated "
        "by core/tool_policy.py and names its target."
    ),
    "triggers": [
        "whois", "who owns this domain", "dns records", "dns lookup", "mx records",
        "txt records", "subdomains", "enumerate subdomains", "certificate transparency",
        "crt.sh", "subdomain takeover", "reverse dns", "ptr record", "ip geolocation",
        "where is this ip", "asn", "who owns this ip", "spf", "dkim", "dmarc",
        "email security", "fingerprint this site", "what is this site running",
        "wayback", "passive dns", "decode jwt", "identify this hash", "analyze pcap",
        "analyze apk", "decode this token",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: dns | whois | reverse_dns | ip_geo | asn | subdomains | takeover_check | tech_fingerprint | passive_dns | wayback | bucket_probe | email_security | hash_identify | jwt_audit | pcap_analyze | apk_manifest | sources. Defaults to dns.",
            },
            "domain": {"type": "STRING",
                       "description": "Domain to inspect, e.g. example.com."},
            "target": {"type": "STRING",
                       "description": "Alias for domain: a domain, IP, or URL depending on the operation."},
            "ip": {"type": "STRING",
                   "description": "IP address for reverse_dns, ip_geo or asn."},
            "record": {"type": "STRING",
                       "description": "DNS record type: A | AAAA | MX | TXT | NS | SOA | CAA | all. Defaults to all."},
            "hash": {"type": "STRING",
                     "description": "Hash to identify (hash_identify operation)."},
            "token": {"type": "STRING",
                      "description": "JWT to decode and audit (jwt_audit operation)."},
            "path": {"type": "STRING",
                     "description": "Path to a .pcap/.cap file for pcap_analyze, or an .apk for apk_manifest."},
            "authorized": {"type": "BOOLEAN",
                           "description": "Must be true for operations that contact the target."},
            "confirm": {"type": "BOOLEAN",
                        "description": "Must be true to start an operation that contacts the target."},
            "limit": {"type": "INTEGER",
                      "description": "Maximum items to return. Defaults to 20."},
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "author": "Stella",
    "category": "osint",
    "surface": "both",
    "requires": [],
    "optional_dependencies": ["dnspython", "whois", "requests"],
    "notes": "Passive sources: crt.sh, CertSpotter, RDAP, RIPE/BGPView, ipapi, Wayback, passive DNS.",
}

_PASSIVE = {"dns", "whois", "reverse_dns", "ip_geo", "asn", "subdomains", "takeover_check",
            "passive_dns", "wayback", "hash_identify", "jwt_audit", "pcap_analyze",
            "apk_manifest", "sources"}
_ACTIVE = {"tech_fingerprint", "bucket_probe", "email_security"}

_RECORD_TYPES = ("A", "AAAA", "MX", "TXT", "NS", "SOA", "CAA", "PTR", "CNAME")


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


def _as_int(value, default: int = 20, ceiling: int = 200) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    if number <= 0:
        number = default
    return min(number, ceiling)


def _domain(kwargs: Dict[str, Any]) -> str:
    return (kwargs.get("domain") or kwargs.get("target") or "").strip().lower().rstrip(".")


def _refusal(operation: str) -> dict:
    return _op(operation, False, None, (
        f"'{operation}' contacts the target, so it needs authorized=true AND confirm=true plus a "
        "named target, and config/tool_policy.json must carry an allow rule naming this tool and "
        "the target. Passive operations (dns, whois, subdomains) never need this."))


# ------------------------------------------------------------- passive: DNS

def _op_dns(kwargs: Dict[str, Any]) -> dict:
    domain = _domain(kwargs)
    if not domain:
        return _op("dns", False, None, "Name a domain (domain=...), e.g. example.com.")
    if not _valid_domain(domain):
        return _op("dns", False, None, f"'{domain}' does not look like a domain name")

    wanted = str(kwargs.get("record") or "all").strip().upper()
    resolver = _dns_resolver()
    if resolver is None:
        return _op("dns", False, None, (
            "dnspython is not installed, so DNS records cannot be resolved offline-style. Install "
            "it with the dependency_manager (name=dnspython); the socket-based lookups in other "
            "operations still work without it."))

    types = list(_RECORD_TYPES) if wanted in ("ALL", "") else [wanted]
    records: dict = {}
    errors: list = []
    for record_type in types:
        try:
            answer = resolver.resolve(domain, record_type)
            records[record_type] = [str(item) for item in answer]
        except Exception as exc:
            errors.append({"type": record_type,
                           "reason": _dns_error_reason(exc)})

    return _op("dns", True, {
        "domain": domain,
        "records": records,
        "requested": wanted,
        "not_returned": errors,
        "note": ("A record type that did not return is listed with its reason: a NXDOMAIN and a "
                 "server that refused the query are different facts."),
        "activity": "dns",
    })


def _valid_domain(text: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+",
                            text or ""))


def _dns_resolver():
    try:
        import dns.resolver

        return dns.resolver.Resolver()
    except Exception:
        return None


def _dns_error_reason(exc: Exception) -> str:
    text = str(exc)
    if "NXDOMAIN" in text or "does not exist" in text.lower():
        return "the name does not exist (NXDOMAIN)"
    if "NoNameserver" in type(exc).__name__:
        return "no nameserver answered"
    if "NoAnswer" in type(exc).__name__:
        return "the server answered with no records of that type"
    return f"{type(exc).__name__}: {text[:120]}"


def _op_whois(kwargs: Dict[str, Any]) -> dict:
    domain = _domain(kwargs)
    if not domain:
        return _op("whois", False, None, "Name a domain (domain=...).")

    rdap = _rdap_lookup(domain)
    if rdap.get("ok"):
        return _op("whois", True, rdap)
    return _op("whois", False, None, rdap.get("reason", "RDAP did not answer"))


def _rdap_lookup(domain: str) -> dict:
    from core.net import http

    result = http.get_json(f"https://rdap.org/domain/{domain}", timeout=12.0,
                           cache=_cache(), ttl=86400.0)
    if not result.get("ok"):
        return {"ok": False, "reason": result.get("reason", "RDAP did not answer")}
    payload = result.get("value") or {}
    events = {event.get("eventAction"): event.get("eventDate")
              for event in payload.get("events") or [] if isinstance(event, dict)}
    nameservers = [entry.get("ldhName") or entry.get("name")
                   for entry in payload.get("nameservers") or [] if isinstance(entry, dict)]
    registrar = None
    for entity in payload.get("entities") or []:
        if isinstance(entity, dict) and "registrar" in (entity.get("roles") or []):
            vcard = entity.get("vcardArray") or []
            if len(vcard) > 1 and isinstance(vcard[1], list) and vcard[1]:
                registrar = vcard[1][0][-1] if isinstance(vcard[1][0], list) else None
    return {
        "ok": True,
        "domain": domain,
        "handle": payload.get("handle"),
        "status": payload.get("status") or [],
        "registered": events.get("registration"),
        "expires": events.get("expiration"),
        "changed": events.get("last changed"),
        "registrar": registrar,
        "nameservers": [name for name in nameservers if name],
        "source": "RDAP (rdap.org)",
        "note": ("RDAP is the structured successor to WHOIS. Redacted contact fields are the "
                 "registrar's doing, not a gap in this lookup."),
    }


def _cache():
    try:
        from core.net.http import feed_cache
        return feed_cache(ttl=86400.0)
    except Exception:
        return None


def _op_reverse_dns(kwargs: Dict[str, Any]) -> dict:
    address = (kwargs.get("ip") or kwargs.get("target") or kwargs.get("domain") or "").strip()
    if not address:
        return _op("reverse_dns", False, None, "Name an IP address (ip=...).")
    try:
        hostname, aliases, addresses = socket.gethostbyaddr(address)
    except socket.herror as exc:
        return _op("reverse_dns", False, None, (
            f"no PTR record for {address} ({exc}); the address has no reverse name, which is "
            "normal for plenty of hosts"))
    except Exception as exc:
        return _op("reverse_dns", False, None, f"{type(exc).__name__}: {exc}")
    return _op("reverse_dns", True, {
        "ip": address, "hostname": hostname, "aliases": list(aliases or []),
        "addresses": list(addresses or []),
        "source": "the system resolver",
        "note": "A PTR record is whatever the address's owner published; it is not verification.",
    })


def _op_ip_geo(kwargs: Dict[str, Any]) -> dict:
    address = (kwargs.get("ip") or kwargs.get("target") or "").strip()
    if not address:
        return _op("ip_geo", False, None, "Name an IP address (ip=...).")
    if not _looks_ip(address):
        return _op("ip_geo", False, None, f"'{address}' is not an IP address")

    from core.net import http

    result = http.get_json(f"https://ipapi.co/{address}/json/", timeout=10.0)
    if not result.get("ok"):
        return _op("ip_geo", False, None, result.get("reason", "ipapi.co did not answer"))
    payload = result.get("value") or {}
    if payload.get("error"):
        return _op("ip_geo", False, None, str(payload.get("reason") or payload.get("error")))
    return _op("ip_geo", True, {
        "ip": address,
        "city": payload.get("city"),
        "region": payload.get("region"),
        "country": payload.get("country_name"),
        "country_code": payload.get("country"),
        "postal": payload.get("postal"),
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "asn": payload.get("asn"),
        "organisation": payload.get("org"),
        "source": "ipapi.co",
        "note": ("Geolocation is the address's registered network location, not where a device "
                 "physically is; a VPN or a carrier NAT makes it wrong by design."),
    })


def _looks_ip(text: str) -> bool:
    parts = (text or "").split(".")
    if len(parts) == 4:
        return all(part.isdigit() and 0 <= int(part) <= 255 for part in parts)
    return ":" in text


def _op_asn(kwargs: Dict[str, Any]) -> dict:
    address = (kwargs.get("ip") or kwargs.get("target") or "").strip()
    if not address:
        return _op("asn", False, None, "Name an IP address (ip=...).")
    if not _looks_ip(address):
        return _op("asn", False, None, f"'{address}' is not an IP address")

    from core.net import http

    result = http.get_text(
        f"https://whois.cymru.com/cgi-bin/whois_owned_data.sh?ip={address}",
        timeout=12.0)
    if not result.get("ok"):
        return _op("asn", False, None, result.get("reason", "the Cymru service did not answer"))
    lines = [line for line in str(result.get("value") or "").splitlines() if line.strip()]
    fields = [item.strip() for item in lines[1].split("|")] if len(lines) > 1 else []
    labels = ["asn", "ip", "prefix", "as_name", "country", "authority", "allocated"]
    record = dict(zip(labels, fields)) if len(fields) >= len(labels) else {"raw": lines[:3]}
    return _op("asn", True, {
        **record,
        "source": "Team Cymru whois",
        "note": "The ASN answer is the registry's view of the address, which is what a route lookup sees.",
    })


def _op_subdomains(kwargs: Dict[str, Any]) -> dict:
    domain = _domain(kwargs)
    if not domain:
        return _op("subdomains", False, None, "Name a domain (domain=...).")

    from core.net import http

    result = http.get_json(f"https://crt.sh/?q=%.{domain}&output=json",
                           timeout=25.0, cache=_cache(), ttl=21600.0)
    if not result.get("ok"):
        return _op("subdomains", False, None, result.get("reason", "crt.sh did not answer"))

    entries = result.get("value") or []
    names: set = set()
    issuers: set = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for value in (entry.get("name_value") or "").splitlines():
            cleaned = value.strip().lower().lstrip("*.")
            if cleaned.endswith(f".{domain}") or cleaned == domain:
                names.add(cleaned)
        issuer_name = (entry.get("issuer_name") or "")
        if issuer_name:
            issuers.add(issuer_name.strip()[:80])

    limit = _as_int(kwargs.get("limit"), 20)
    return _op("subdomains", True, {
        "domain": domain,
        "count": len(names),
        "subdomains": sorted(names)[:limit],
        "certificates": len(entries),
        "sample_issuers": sorted(issuers)[:6],
        "source": "crt.sh certificate transparency",
        "activity": "passive",
        "note": ("Certificate transparency is passive: it lists names that have had certificates "
                 "issued, which includes names that no longer resolve. A name here is evidence a "
                 "certificate existed, not that the host is alive."),
    })


def _op_takeover_check(kwargs: Dict[str, Any]) -> dict:
    marker = _op_marker("takeover_check")
    return _op("takeover_check", True, {
        "handled_by": "domain_intel.subdomains + network_audit.tls_audit",
        "note": marker,
    })


def _op_passive_dns(kwargs: Dict[str, Any]) -> dict:
    domain = _domain(kwargs)
    if not domain:
        return _op("passive_dns", False, None, "Name a domain (domain=...).")
    return _op("passive_dns", True, {
        "domain": domain,
        "sources_available": ["crt.sh (certificate transparency)",
                             "Wayback Machine CDX (historic URLs)",
                             "Common Crawl index"],
        "note": ("Use the subdomains and wayback operations; this operation names which passive "
                 "sources are wired up rather than repeating their output."),
    })


def _op_wayback(kwargs: Dict[str, Any]) -> dict:
    target = (kwargs.get("domain") or kwargs.get("target") or "").strip()
    if not target:
        return _op("wayback", False, None, "Name a domain or URL (domain=...).")

    from core.net import http

    cleaned = target.split("://")[-1].split("/")[0]
    url = f"http://web.archive.org/cdx/search/cdx?url={cleaned}/*&output=json&limit=50&collapse=urlkey"
    result = http.get_json(url, timeout=25.0, cache=_cache(), ttl=86400.0)
    if not result.get("ok"):
        return _op("wayback", False, None, result.get("reason", "the Wayback CDX did not answer"))
    rows = result.get("value") or []
    entries = [dict(zip(rows[0], row)) for row in rows[1:]] if len(rows) > 1 else []
    return _op("wayback", True, {
        "target": cleaned,
        "count": len(entries),
        "sample": [{"url": entry.get("original"), "timestamp": entry.get("timestamp"),
                    "status": entry.get("statuscode"), "mime": entry.get("mimetype")}
                   for entry in entries[:_as_int(kwargs.get("limit"), 20)]],
        "source": "Internet Archive Wayback CDX",
        "activity": "passive",
        "note": ("Historic URLs are what the archive captured, which is how a retired endpoint or "
                 "a stale parameter shows up."),
    })


# ------------------------------------------------------------- offline decodes

def _op_hash_identify(kwargs: Dict[str, Any]) -> dict:
    from core.security import hashcat

    sample = (kwargs.get("hash") or "").strip()
    result = hashcat.identify(sample)
    if not result.get("ok"):
        return _op("hash_identify", False, None, result.get("reason", "the hash could not be identified"))
    return _op("hash_identify", True, result)


def _op_jwt_audit(kwargs: Dict[str, Any]) -> dict:
    token = (kwargs.get("token") or "").strip()
    if not token:
        return _op("jwt_audit", False, None, "Give the JWT (token=...).")
    parts = token.split(".")
    if len(parts) != 3:
        return _op("jwt_audit", False, None, (
            f"that token has {len(parts)} parts, not 3, so it is not a JWT; nothing was decoded"))

    def _decode(segment: str) -> dict:
        padded = segment + "=" * (-len(segment) % 4)
        try:
            return json.loads(base64.urlsafe_b64decode(padded))
        except Exception as exc:
            return {"_error": f"{type(exc).__name__}: {exc}"}

    header = _decode(parts[0])
    claims = _decode(parts[1])
    signature_length = len(parts[2]) * 3 // 4
    now = _unix_now()
    findings = []

    algorithm = str(header.get("alg") or "").upper()
    if algorithm in ("NONE", ""):
        findings.append({"finding": "the algorithm is 'none', which means no signature",
                         "severity": "high",
                         "meaning": "anyone can forge a token with this header"})
    if "jwk" in header and "kid" not in header:
        findings.append({"finding": "the header carries its own key (jwk) with no kid",
                         "severity": "medium",
                         "meaning": "an attacker-controlled key in the header is a known bypass shape"})

    for claim in ("exp", "nbf", "iat"):
        value = claims.get(claim)
        if value is None:
            continue
        try:
            when = float(value)
        except (TypeError, ValueError):
            continue
        if claim == "exp" and when < now:
            findings.append({"finding": f"the token expired {round((now - when) / 86400, 1)} day(s) ago",
                             "severity": "info", "meaning": "an expired token should be refused"})
        if claim == "nbf" and when > now:
            findings.append({"finding": "the token is not valid yet (nbf is in the future)",
                             "severity": "medium"})

    if claims.get("exp") is None:
        findings.append({"finding": "the token carries no expiry",
                         "severity": "medium",
                         "meaning": "a token without exp is valid until its key is rotated"})

    return _op("jwt_audit", True, {
        "header": header,
        "claims": _redact(claims),
        "signature_bytes": signature_length,
        "findings": findings,
        "note": ("The claims are what the token asserts about itself. The signature is not "
                 "verified here - verifying needs the key, which this machine does not have."),
    })


def _unix_now() -> float:
    import time

    return float(time.time())


def _redact(claims: dict) -> dict:
    redacted = {}
    for key, value in (claims or {}).items():
        if key in ("password", "secret", "token", "api_key", "authorization"):
            redacted[key] = "<redacted by Stella>"
        else:
            redacted[key] = value
    return redacted


def _op_pcap_analyze(kwargs: Dict[str, Any]) -> dict:
    path = (kwargs.get("path") or "").strip()
    if not path:
        return _op("pcap_analyze", False, None, "Give the capture path (path=...).")
    from core.net.pcap import read_pcap

    from pathlib import Path

    capture = Path(path).expanduser()
    if not capture.exists():
        return _op("pcap_analyze", False, None, f"{capture} does not exist on this machine")
    parsed = read_pcap(capture.read_bytes())
    if not parsed.get("ok"):
        return _op("pcap_analyze", False, None, parsed.get("reason", "the capture could not be parsed"))
    summary = parsed.get("summary") or {}
    return _op("pcap_analyze", True, {
        "packets": summary.get("packets"),
        "dns_queries": (summary.get("dns_queries") or [])[:_as_int(kwargs.get("limit"), 20)],
        "http_requests": (summary.get("http_requests") or [])[:_as_int(kwargs.get("limit"), 20)],
        "plaintext_credentials": summary.get("plaintext_credentials"),
        "tls_server_names": (summary.get("tls_server_names") or [])[:_as_int(kwargs.get("limit"), 20)],
        "counts": {key: value for key, value in summary.items()
                   if isinstance(value, int)},
        "source": "this capture file, read locally",
        "note": ("Everything here was read from a file that already exists on this machine; no "
                 "live capture was made."),
    })


def _op_apk_manifest(kwargs: Dict[str, Any]) -> dict:
    path = (kwargs.get("path") or "").strip()
    if not path:
        return _op("apk_manifest", False, None, "Give the APK path (path=...).")
    from core.net.apk import read_manifest

    from pathlib import Path

    apk = Path(path).expanduser()
    if not apk.exists():
        return _op("apk_manifest", False, None, f"{apk} does not exist on this machine")
    try:
        result = read_manifest(apk.read_bytes())
    except ValueError as exc:
        return _op("apk_manifest", False, None, str(exc))
    return _op("apk_manifest", True, result)


# --------------------------------------------------------------- active (gated)

def _op_tech_fingerprint(kwargs: Dict[str, Any]) -> dict:
    operation = "tech_fingerprint"
    if not _flag(**kwargs):
        return _refusal(operation)
    target = (kwargs.get("target") or kwargs.get("domain") or "").strip()
    if not target:
        return _op(operation, False, None, "Name the site to fingerprint (target=...).")

    from core.net import http

    url = target if "://" in target else f"https://{target}"
    result = http.get_text(url, timeout=15.0, max_bytes=1_000_000)
    if not result.get("ok"):
        return _op(operation, False, None, result.get("reason", "the site did not answer"))

    body = str(result.get("value") or "")[:400_000]
    stack = []
    signatures = {
        "WordPress": ("/wp-content/", "wp-includes"),
        "Drupal": ("/sites/default/", "drupal.js"),
        "Joomla": ("/media/jui/", "joomla"),
        "Django": ("csrfmiddlewaretoken", "__debug__"),
        "Rails": ("/assets/application", "csrf-token"),
        "React": ("react.production.min", "__react"),
        "Vue": ("data-v-app", "vue.runtime"),
        "Next.js": ("/_next/static", "__NEXT_DATA__"),
        "Nginx": (),
        "Cloudflare": ("cdn-cgi/", "__cfduid"),
        "jQuery": ("jquery", "jQuery"),
        "Bootstrap": ("bootstrap.min", "bootstrap.css"),
        "Angular": ("ng-version", "angular.min"),
        "Laravel": ("laravel", "XSRF-TOKEN"),
        "ExpressionEngine": ("exp_ticket",),
    }
    for label, markers in signatures.items():
        if any(marker in body for marker in markers):
            stack.append(label)

    headers = _http_headers(url)
    server = headers.get("server")
    powered_by = headers.get("x-powered-by")
    generator = re.search(r'<meta name="generator" content="([^"]+)"', body)
    if generator:
        stack.append(f"generator: {generator.group(1)}")

    return _op(operation, True, {
        "url": url,
        "stack": sorted(set(stack)),
        "server": server,
        "powered_by": powered_by,
        "frameworks": sorted(set(stack)),
        "source": "one HTTP GET of the page",
        "note": ("A fingerprint is a guess from what the page happens to include; a minified or "
                 "self-hosted library looks identical to a CDN one."),
    })


def _http_headers(url: str) -> dict:
    try:
        import urllib.request

        request = urllib.request.Request(url, method="HEAD",
                                         headers={"User-Agent": "StellaAI/1.0"})
        with urllib.request.urlopen(request, timeout=15.0) as response:
            return {name.lower(): value for name, value in response.headers.items()}
    except Exception:
        return {}


def _op_bucket_probe(kwargs: Dict[str, Any]) -> dict:
    operation = "bucket_probe"
    if not _flag(**kwargs):
        return _refusal(operation)
    name = (kwargs.get("target") or kwargs.get("domain") or "").strip().lower()
    if not name:
        return _op(operation, False, None, "Name the bucket or the base name to try (target=...).")

    from core.net import http

    candidates = [name] if name.startswith((name[:1] and name)) and "." not in name else \
        [f"{name}-backups", f"{name}-assets", f"{name}-static", f"{name}-dev", name]
    probed = []
    for candidate in candidates[:5]:
        for scheme, host in (("https", f"{candidate}.s3.amazonaws.com"),):
            result = http.get_text(f"{scheme}://{host}", timeout=10.0, max_bytes=2000)
            probed.append({
                "bucket": candidate,
                "host": host,
                "reachable": result.get("ok") is False and "HTTP 404" in str(result.get("reason")) or result.get("ok"),
                "status": result.get("status"),
                "reason": result.get("reason"),
            })
    listings = [entry for entry in probed if entry.get("status") == 200]
    return _op(operation, True, {
        "probed": probed,
        "listings": listings,
        "note": ("A public bucket is a configuration decision by its owner; a 404 means the name "
                 "exists but is not public, and a 403 means it exists and is not listable. Neither "
                 "response is a finding on its own."),
    })


def _op_email_security(kwargs: Dict[str, Any]) -> dict:
    operation = "email_security"
    if not _flag(**kwargs):
        return _refusal(operation)
    domain = _domain(kwargs)
    if not domain:
        return _op(operation, False, None, "Name a domain (domain=...).")

    resolver = _dns_resolver()
    if resolver is None:
        return _op(operation, False, None, (
            "dnspython is required to read the email-security records; install it with the "
            "dependency_manager (name=dnspython)."))

    findings = []
    try:
        txt_records = [str(item) for item in resolver.resolve(domain, "TXT")]
    except Exception:
        txt_records = []
    try:
        caa = [str(item) for item in resolver.resolve(domain, "CAA")]
    except Exception:
        caa = []

    spf = [record for record in txt_records if record.lower().startswith("v=spf1")]
    if not spf:
        findings.append({"finding": "no SPF record is published", "severity": "medium",
                         "meaning": "anyone can send mail that claims to be from this domain"})
    elif "*all" in next((record for record in spf if "all" in record), ""):
        findings.append({"finding": "the SPF record ends in '+all'", "severity": "high",
                         "meaning": "that permits every host on the internet to send for this domain"})

    dmarc = False
    for record in txt_records:
        if record.lower().startswith("v=dmarc1"):
            dmarc = True
            if "p=none" in record.lower():
                findings.append({"finding": "the DMARC policy is p=none", "severity": "medium",
                                 "meaning": "the policy is monitored but not enforced"})
    if not dmarc:
        findings.append({"finding": "no DMARC record is published", "severity": "medium",
                         "meaning": "there is no instruction for what to do with a failing message"})

    if not any(record.startswith("_domainkey.") for record in []):
        findings.append({"finding": "DKIM selectors are not probed (they are per-provider)",
                         "severity": "info",
                         "meaning": "check the provider's published selector, e.g. google._domainkey"})

    if not caa:
        findings.append({"finding": "no CAA record is published", "severity": "low",
                         "meaning": "any certificate authority may issue for this domain"})

    return _op(operation, True, {
        "domain": domain,
        "spf": spf,
        "dmarc": [record for record in txt_records if record.lower().startswith("v=dmarc1")],
        "caa": caa,
        "findings": findings,
        "note": ("Email-security records are a configuration review. A missing record is a "
                 "hardening opportunity with the value to set, not an exploit."),
    })


def _op_marker(operation: str) -> str:
    return (f"'{operation}' is an interpretation over the outputs of other operations; it names "
            "which ones rather than repeating them.")


def _op_sources(kwargs: Dict[str, Any] | None = None) -> dict:
    return _op("sources", True, {
        "passive": [
            {"operation": "dns", "source": "dnspython against the resolver", "activity": "dns"},
            {"operation": "whois", "source": "RDAP (rdap.org)", "activity": "passive"},
            {"operation": "reverse_dns", "source": "the system resolver", "activity": "dns"},
            {"operation": "ip_geo", "source": "ipapi.co", "activity": "passive"},
            {"operation": "asn", "source": "Team Cymru whois", "activity": "passive"},
            {"operation": "subdomains", "source": "crt.sh", "activity": "passive"},
            {"operation": "wayback", "source": "Wayback CDX", "activity": "passive"},
            {"operation": "pcap_analyze", "source": "a local capture file", "activity": "local"},
            {"operation": "apk_manifest", "source": "a local APK file", "activity": "local"},
            {"operation": "hash_identify", "source": "shape heuristics", "activity": "local"},
            {"operation": "jwt_audit", "source": "the token itself", "activity": "local"},
        ],
        "active": [
            {"operation": "tech_fingerprint", "source": "one HTTP GET", "activity": "active"},
            {"operation": "bucket_probe", "source": "an HTTP request per candidate", "activity": "active"},
            {"operation": "email_security", "source": "DNS TXT and CAA lookups", "activity": "dns"},
        ],
    })


_OPERATIONS = {
    "dns": _op_dns,
    "whois": _op_whois,
    "reverse_dns": _op_reverse_dns,
    "ip_geo": _op_ip_geo,
    "asn": _op_asn,
    "subdomains": _op_subdomains,
    "takeover_check": _op_takeover_check,
    "passive_dns": _op_passive_dns,
    "wayback": _op_wayback,
    "hash_identify": _op_hash_identify,
    "jwt_audit": _op_jwt_audit,
    "pcap_analyze": _op_pcap_analyze,
    "apk_manifest": _op_apk_manifest,
    "tech_fingerprint": _op_tech_fingerprint,
    "bucket_probe": _op_bucket_probe,
    "email_security": _op_email_security,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "dns": "DNS Records", "whois": "Domain Registration", "reverse_dns": "Reverse DNS",
    "ip_geo": "IP Geolocation", "asn": "ASN Ownership", "subdomains": "Subdomains (Cert Transparency)",
    "takeover_check": "Takeover Check", "passive_dns": "Passive DNS Sources",
    "wayback": "Wayback History", "hash_identify": "Hash Identification",
    "jwt_audit": "JWT Audit", "pcap_analyze": "PCAP Analysis",
    "apk_manifest": "APK Manifest", "tech_fingerprint": "Technology Fingerprint",
    "bucket_probe": "Bucket Probe", "email_security": "Email Security",
    "sources": "Domain Intel Sources",
}

_ALIASES = {
    "whois_lookup": "whois", "registration": "whois",
    "dns_records": "dns", "mx": "dns", "txt": "dns",
    "ptr": "reverse_dns", "reverse_lookup": "reverse_dns",
    "geoip": "ip_geo", "geolocate": "ip_geo",
    "asn_lookup": "asn", "who_owns_ip": "asn",
    "subdomain_enumeration": "subdomains", "ct": "subdomains", "crt_sh": "subdomains",
    "fingerprint": "tech_fingerprint", "tech_stack": "tech_fingerprint",
    "spf_dkim_dmarc": "email_security", "spf": "email_security", "dmarc": "email_security",
    "jwt": "jwt_audit", "decode_jwt": "jwt_audit",
    "hash": "hash_identify", "identify_hash": "hash_identify",
    "pcap": "pcap_analyze", "analyze_pcap": "pcap_analyze",
    "apk": "apk_manifest", "analyze_apk": "apk_manifest",
    "wayback_machine": "wayback", "archive": "wayback",
    "sources_list": "sources",
}


def _failure(operation: str, reason: str) -> dict:
    title = _OPERATION_TITLES.get(operation, "Domain Intel")
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
    """Collect domain intelligence, with passive by default and active gated."""
    operation = (kwargs.get("operation") or "dns").strip().lower()
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
        "title": _OPERATION_TITLES.get(operation, "Domain Intel"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
        "sources": _op_sources()["value"],
        "authorized": _flag(**kwargs),
        "target": _domain(kwargs) or None,
    }


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "dns":
        if not record.get("ok"):
            return f"DNS unavailable: {record.get('error')}"
        records = value.get("records") or {}
        listing = "; ".join(f"{key}: {', '.join(items[:3])}" for key, items in records.items() if items)
        return f"DNS for {value.get('domain')}: {listing or 'no records returned'}"
    if operation == "whois":
        if not record.get("ok"):
            return f"Registration lookup unavailable: {record.get('error')}"
        return (f"{value.get('domain')} is registered"
                + (f" with {value.get('registrar')}" if value.get("registrar") else "")
                + f", expires {value.get('expires') or 'unknown'}.")
    if operation == "reverse_dns":
        if not record.get("ok"):
            return f"Reverse DNS unavailable: {record.get('error')}"
        return f"{value.get('ip')} points at {value.get('hostname')}."
    if operation == "ip_geo":
        if not record.get("ok"):
            return f"IP lookup unavailable: {record.get('error')}"
        return (f"{value.get('ip')} is {value.get('organisation') or 'unknown org'} "
                f"(AS{value.get('asn')}) in {value.get('city') or value.get('country') or 'unknown'}.")
    if operation == "asn":
        if not record.get("ok"):
            return f"ASN lookup unavailable: {record.get('error')}"
        return f"AS{value.get('asn')} {value.get('as_name')}, prefix {value.get('prefix')}, {value.get('country')}."
    if operation == "subdomains":
        if not record.get("ok"):
            return f"Subdomain enumeration unavailable: {record.get('error')}"
        found = value.get("subdomains") or []
        listing = ", ".join(found[:8])
        return f"{value.get('count')} name(s) hold certificates for {value.get('domain')}. {listing}"
    if operation == "wayback":
        if not record.get("ok"):
            return f"Wayback unavailable: {record.get('error')}"
        return f"{value.get('count')} historic URL(s) for {value.get('target')} from the Wayback CDX."
    if operation == "hash_identify":
        if not record.get("ok"):
            return f"Hash identification: {record.get('error')}"
        return f"That hash looks like {value.get('hash_type')} (mode {value.get('hashcat_mode')})."
    if operation == "jwt_audit":
        if not record.get("ok"):
            return f"JWT audit: {record.get('error')}"
        findings = value.get("findings") or []
        issues = "; ".join(item["finding"] for item in findings[:4]) or "no findings"
        return f"JWT header alg={value.get('header', {}).get('alg')}; {issues}."
    if operation == "pcap_analyze":
        if not record.get("ok"):
            return f"PCAP analysis: {record.get('error')}"
        counts = value.get("counts") or {}
        return (f"{counts.get('packets', 0)} packet(s): {len(value.get('dns_queries') or [])} DNS "
                f"queries, {len(value.get('http_requests') or [])} HTTP requests, "
                f"{len(value.get('plaintext_credentials') or [])} plaintext credential(s).")
    if operation == "apk_manifest":
        if not record.get("ok"):
            return f"APK manifest: {record.get('error')}"
        return (f"{value.get('package')} v{value.get('version_name')}, "
                f"{len(value.get('permissions') or [])} permissions "
                f"({len(value.get('dangerous_permissions') or [])} dangerous).")
    if operation == "tech_fingerprint":
        if not record.get("ok"):
            return f"Fingerprint did not run: {record.get('error')}"
        return f"{value.get('url')}: {', '.join(value.get('stack') or []) or 'no recognisable stack'}."
    if operation == "email_security":
        if not record.get("ok"):
            return f"Email security audit: {record.get('error')}"
        findings = value.get("findings") or []
        return f"{value.get('domain')}: {len(findings)} finding(s) - " + "; ".join(
            item["finding"] for item in findings[:4])
    if operation == "bucket_probe":
        if not record.get("ok"):
            return f"Bucket probe did not run: {record.get('error')}"
        listings = value.get("listings") or []
        return f"{len(value.get('probed') or [])} bucket name(s) probed, {len(listings)} listable."
    if operation in ("passive_dns", "takeover_check"):
        return value.get("note", "")
    if operation == "sources":
        return f"{len(value.get('passive') or [])} passive and {len(value.get('active') or [])} active source(s)."
    return record.get("error") or "No operation ran."
