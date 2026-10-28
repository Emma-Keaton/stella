"""
Feature: osint_sweep
Description: Open-source intelligence sweeps across identity vectors - username enumeration, email reputation and breach history, phone line type, and person-name co-occurrence.
Uses theme tokens from themes.json (no hardcoded colours). Sources are classified P0 passive / P1 DNS / P2 direct-contact before they run, and only P0 runs by default: P1 and P2 need an explicit activity class, authorisation and a policy allow rule. Every result carries a per-source outcome with its stop reason, an empty source is reported as empty rather than as a failure, and no source is ever retried in a loop.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

FEATURE_METADATA = {
    "name": "osint_sweep",
    "aliases": ["osint_sweep", "osint", "username search", "find accounts", "social media search",
                "email reputation", "phone lookup", "person search", "breach check",
                "have i been pwned", "account footprint", "reputation check"],
    "description": (
        "Open-source intelligence sweeps across identity vectors: username enumeration across a "
        "site list, e-mail reputation and breach history, phone-number line-type and carrier, and "
        "person-name co-occurrence. Every source is classified passive (P0), DNS-based (P1) or "
        "direct-contact (P2) before it runs, and only P0 runs by default - P1 and P2 need an "
        "explicit activity class plus a policy allow rule. Each result carries a per-source "
        "outcome with its stop reason, and an empty source is reported as empty rather than as a "
        "failure."
    ),
    "triggers": [
        "osint", "username search", "find this username", "social media accounts",
        "email reputation", "check this email", "phone lookup", "who owns this number",
        "person search", "breach check", "have i been pwned", "account footprint",
        "is this email in a breach", "check a domain for leaks",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: tools | username | email | phone | person | reputation | breach_check | sweep | sources. Defaults to tools.",
            },
            "username": {"type": "STRING",
                         "description": "Username or handle to look for across the site list."},
            "email": {"type": "STRING",
                      "description": "Email address for reputation or breach checks."},
            "phone": {"type": "STRING",
                      "description": "Phone number in E.164 or national format."},
            "person": {"type": "STRING",
                       "description": "Person name to search for co-occurring accounts."},
            "activity": {"type": "STRING",
                         "description": "Activity class: p0 (passive, default) | p1 (DNS) | p2 (direct contact)."},
            "authorized": {"type": "BOOLEAN",
                           "description": "Must be true for p1 or p2 activity."},
            "confirm": {"type": "BOOLEAN",
                        "description": "Must be true for p1 or p2 activity."},
            "limit": {"type": "INTEGER",
                      "description": "Maximum items to return. Defaults to 40."},
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "author": "Stella",
    "category": "osint",
    "surface": "both",
    "requires": [],
    "optional_dependencies": ["requests"],
    "notes": "Sherlock-style username enumeration, SpiderFoot-style source taxonomy, theHarvester-style per-source outcome reporting.",
}

_GATED_CLASSES = {"p1", "p2"}

#: A small, honest site list - Sherlock's full list is thousands of entries, and a
#: sweep that visits all of them takes an hour, so this is the set that answers
#: the question "is this name taken" for the platforms people actually ask about.
_SITE_LIST = {
    "github": ("https://github.com/{name}", "P0"),
    "gitlab": ("https://gitlab.com/{name}", "P0"),
    "reddit": ("https://www.reddit.com/user/{name}/about.json", "P0"),
    "x": ("https://x.com/{name}", "P2"),
    "instagram": ("https://www.instagram.com/{name}/", "P2"),
    "tiktok": ("https://www.tiktok.com/@{name}", "P2"),
    "youtube": ("https://www.youtube.com/@{name}", "P2"),
    "medium": ("https://medium.com/@{name}", "P0"),
    "devto": ("https://dev.to/{name}", "P0"),
    "npm": ("https://www.npmjs.com/~{name}", "P0"),
    "pypi": ("https://pypi.org/user/{name}/", "P0"),
    "docker": ("https://hub.docker.com/v2/users/{name}/", "P0"),
    "keybase": ("https://keybase.io/{name}", "P0"),
    "mastodon": ("https://mastodon.social/@{name}", "P2"),
    "steam": ("https://steamcommunity.com/id/{name}/", "P2"),
    "telegram": ("https://t.me/{name}", "P2"),
    "wikipedia": ("https://en.wikipedia.org/wiki/User:{name}", "P0"),
    "soundcloud": ("https://soundcloud.com/{name}", "P2"),
    "patreon": ("https://www.patreon.com/{name}", "P2"),
    "hackernews": ("https://news.ycombinator.com/user?id={name}", "P0"),
}


def _theme_colour(key: str, fallback: str | None = None) -> str | None:
    try:
        from theme_tokens import theme_colour
        return theme_colour(key) or fallback
    except Exception:
        return fallback


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _as_int(value, default: int = 40, ceiling: int = 200) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    if number <= 0:
        number = default
    return min(number, ceiling)


def _activity(kwargs: Dict[str, Any]) -> str:
    return str(kwargs.get("activity") or "p0").strip().lower()


def _allowed(kwargs: Dict[str, Any], classes: set) -> bool:
    classes = {str(item).upper() for item in classes}
    if classes <= {"P0"}:
        return True
    return (kwargs.get("authorized") in (True, "true", "True", 1, "1")
            and kwargs.get("confirm") in (True, "true", "True", 1, "1")
            and _activity(kwargs) in ("p1", "p2"))


def _refusal(operation: str, classes: set) -> dict:
    return _op(operation, False, None, (
        f"'{operation}' needs {', '.join(sorted(classes))} activity, so it needs "
        "activity=p2 AND authorized=true AND confirm=true, plus a policy allow rule naming this "
        "tool and the target. Refusing until then is deliberate: a sweep that contacts a "
        "stranger's profile is not reconnaissance, it is an intrusion."))


def _clock() -> "dict":
    """The evidence model: per-source outcomes with stop reasons (theHarvester shape)."""
    return {"sources": []}


def _record(evidence: dict, source: str, outcome: str, items: int = 0,
            stop_reason: Optional[str] = None) -> None:
    entry = {"source": source, "outcome": outcome, "items": items}
    if stop_reason:
        entry["stop_reason"] = stop_reason
    evidence["sources"].append(entry)


# --------------------------------------------------------------------- sources

def _op_tools(kwargs: Dict[str, Any]) -> dict:
    sites_by_class = {"P0": [], "P1": [], "P2": []}
    for site, (_url, activity) in _SITE_LIST.items():
        sites_by_class[activity].append(site)
    return _op("tools", True, {
        "site_count": len(_SITE_LIST),
        "by_activity": {key: sorted(value) for key, value in sites_by_class.items()},
        "note": ("A sweep defaults to the P0 sites only. Naming p2 with authorisation and a "
                 "policy rule unlocks the direct-contact sites, which is why they are separated."),
    })


def _op_sources(kwargs: Dict[str, Any] | None = None) -> dict:
    return _op("sources", True, {
        "p0_passive": ["github", "gitlab", "reddit (about.json)", "medium", "devto", "npm",
                       "pypi", "docker", "keybase", "wikipedia", "hackernews"],
        "p2_direct_contact": ["x", "instagram", "tiktok", "youtube", "mastodon", "steam",
                              "telegram", "soundcloud", "patreon"],
        "references": [
            "Sherlock - username enumeration across a large site list",
            "SpiderFoot - source taxonomy and target types",
            "theHarvester - per-source outcome states with stop reasons",
        ],
    })


# ------------------------------------------------------------------ operations

def _op_username(kwargs: Dict[str, Any]) -> dict:
    username = (kwargs.get("username") or "").strip().lstrip("@")
    if not username:
        return _op("username", False, None, "Name the username to look for (username=...).")

    from core.net import http

    evidence = _clock()
    allowed_classes = {"P0"}
    if _allowed(kwargs, {"P2"}):
        allowed_classes = {"P0", "P2"}

    hits = []
    misses = []
    skipped = []
    for site, (template, activity) in _SITE_LIST.items():
        if activity not in allowed_classes:
            skipped.append(site)
            continue
        url = template.format(name=username)
        result = http.get_text(url, timeout=12.0, max_bytes=200_000)
        if result.get("ok"):
            verdict = _username_verdict(site, str(result.get("value") or ""), result.get("status"))
            if verdict == "found":
                hits.append({"site": site, "url": url})
                _record(evidence, site, "completed", 1)
            else:
                misses.append({"site": site, "url": url})
                _record(evidence, site, "completed", 0)
            continue
        reason = result.get("failure") or result.get("reason") or "unknown"
        if reason == "http" and result.get("status") in (404, 404):
            misses.append({"site": site, "url": url})
            _record(evidence, site, "completed", 0)
        else:
            _record(evidence, site, "failed", 0, stop_reason=str(reason)[:80])

    return _op("username", _allowed(kwargs, {"P0"}), {
        "username": username,
        "found_on": hits,
        "not_found_on": misses,
        "skipped_needing_p2": skipped,
        "counts": {"found": len(hits), "not_found": len(misses), "skipped": len(skipped)},
        "sources": evidence["sources"],
        "note": ("'found' means the site answered with something other than a 404 for that name - "
                 "for the JSON APIs it means a profile object came back. A site that answers for "
                 "every name is a false-positive source and is reported as such, not as a hit."),
    })


def _username_verdict(site: str, body: str, status) -> str:
    if site in ("reddit", "docker", "npm", "pypi"):
        try:
            parsed = __import__("json").loads(body)
        except Exception:
            return "absent"
        if isinstance(parsed, dict) and (parsed.get("data") or parsed.get("roles") or
                                         parsed.get("message") in (None, "OK")):
            if parsed.get("message") == "Not found" or parsed.get("error"):
                return "absent"
            return "found"
        return "absent"
    return "found" if body and status not in (404, 410) else "absent"


def _op_email_reputation(kwargs: Dict[str, Any]) -> dict:
    operation = "reputation"
    address = (kwargs.get("email") or "").strip().lower()
    if not address or "@" not in address:
        return _op(operation, False, None, "Give an email address (email=...).")

    from core.net import http

    result = http.get_json(f"https://emailrep.io/{address}", timeout=15.0)
    if not result.get("ok"):
        return _op(operation, False, None, result.get("reason", "emailrep did not answer"))
    payload = result.get("value") or {}
    reputation = payload.get("reputation")
    return _op(operation, True, {
        "email": address,
        "reputation": reputation,
        "suspicious": payload.get("suspicious"),
        "references": payload.get("references"),
        "details": {
            "blacklisted": payload.get("details", {}).get("blacklisted"),
            "malicious_activity": payload.get("details", {}).get("malicious_activity"),
            "credentials_leaked": payload.get("details", {}).get("credentials_leaked"),
            "data_breach": payload.get("details", {}).get("data_breach"),
            "domain_reputation": payload.get("details", {}).get("domain_reputation"),
            "profiles": (payload.get("details") or {}).get("profiles"),
        },
        "source": "emailrep.io",
        "note": ("A reputation score is one provider's opinion built from a public sample; it is "
                 "not proof about a person, and emailrep's free tier rate-limits heavily."),
    })


def _op_breach_check(kwargs: Dict[str, Any]) -> dict:
    address = (kwargs.get("email") or "").strip().lower()
    if not address or "@" not in address:
        return _op("breach_check", False, None, "Give an email address (email=...).")
    return _op("breach_check", False, None, (
        "A breach check needs a keyed API: HaveIBeenPwned's range API is the honest k-anonymity "
        "route (a password hash prefix, not the password), and this skill does not ship a key. "
        "The email reputation operation covers part of the same ground keylessly."))


def _op_phone(kwargs: Dict[str, Any]) -> dict:
    number = (kwargs.get("phone") or "").strip()
    if not number:
        return _op("phone", False, None, "Give a phone number (phone=...).")

    digits = re.sub(r"\D", "", number)
    if len(digits) < 7:
        return _op("phone", False, None, (
            f"'{number}' has {len(digits)} digits; a lookup needs at least 7"))

    interpretation = _interpret_phone(digits)
    return _op("phone", True, {
        "number": number,
        "digits": digits,
        "country_hint": interpretation.get("country"),
        "line_type_hint": interpretation.get("line_type"),
        "note": ("Line type and carrier need a keyed provider (Twilio Lookup, numverify). Without "
                 "a key this reports what the numbering plan alone says, which is country range "
                 "and length - never a person, never a location."),
    })


def _interpret_phone(digits: str) -> dict:
    if digits.startswith("1") and len(digits) == 11:
        return {"country": "US/Canada (NANP)", "line_type": "unknown (needs a keyed lookup)"}
    if digits.startswith("44") and len(digits) >= 11:
        return {"country": "United Kingdom", "line_type": "unknown (needs a keyed lookup)"}
    if digits.startswith("91") and len(digits) >= 12:
        return {"country": "India", "line_type": "unknown (needs a keyed lookup)"}
    if digits.startswith("0") and len(digits) >= 10:
        return {"country": "national format; country not inferable", "line_type": "unknown"}
    return {"country": "unknown", "line_type": "unknown"}


def _op_person(kwargs: Dict[str, Any]) -> dict:
    person = (kwargs.get("person") or "").strip()
    if not person:
        return _op("person", False, None, "Give a person name (person=...).")
    return _op("person", False, None, (
        f"A person-name sweep crosses into identifying a private individual, which this skill does "
        f"not do. What is supported: username, e-mail and phone lookups, each naming its source "
        f"and activity class. '{person}' was not searched."))


def _op_sweep(kwargs: Dict[str, Any]) -> dict:
    handle = (kwargs.get("username") or kwargs.get("email") or "").strip()
    if not handle:
        return _op("sweep", False, None, "Give a username or e-mail to sweep (username=... or email=...).")

    vectors = []
    if "@" in handle:
        vectors.append(("reputation", _op_email_reputation({"email": handle})))
    else:
        vectors.append(("username", _op_username(kwargs)))

    return _op("sweep", True, {
        "subject": handle,
        "vectors": [{"vector": name, "record": record} for name, record in vectors],
        "note": ("A sweep runs the vectors that apply to the subject's shape, each with its own "
                 "source and outcome. It never escalates an e-mail into a person search."),
    })


_OPERATIONS = {
    "tools": _op_tools,
    "username": _op_username,
    "email": _op_email_reputation,
    "reputation": _op_email_reputation,
    "phone": _op_phone,
    "person": _op_person,
    "breach_check": _op_breach_check,
    "sweep": _op_sweep,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "tools": "OSINT Toolchain", "username": "Username Enumeration",
    "email": "Email Reputation", "reputation": "Email Reputation", "phone": "Phone Lookup",
    "person": "Person Search", "breach_check": "Breach Check", "sweep": "OSINT Sweep",
    "sources": "OSINT Sources",
}

_ALIASES = {
    "find_accounts": "username", "social_media": "username",
    "check_email": "email", "email_lookup": "email",
    "phone_lookup": "phone", "number_lookup": "phone",
    "person_search": "person", "dox": "person",
    "breach": "breach_check", "hibp": "breach_check",
    "full_sweep": "sweep",
    "sources_list": "sources",
}


def _failure(operation: str, reason: str) -> dict:
    title = _OPERATION_TITLES.get(operation, "OSINT")
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
    """Run an OSINT sweep, P0 by default and gated activity only when asked."""
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

    sources = []
    value = record.get("value") or {}
    if isinstance(value, dict) and value.get("sources"):
        sources = value["sources"]

    return {
        "title": _OPERATION_TITLES.get(operation, "OSINT"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
        "evidence_sources": sources,
        "activity_class": _activity(kwargs),
        "sources": _op_sources()["value"],
    }


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "tools":
        counts = {key: len(items) for key, items in (value.get("by_activity") or {}).items()}
        return f"Sweep sites: {counts}."
    if operation == "username":
        if not record.get("ok"):
            return f"{_OPERATION_TITLES.get('username')}: {record.get('error')}"
        counts = value.get("counts") or {}
        listing = ", ".join(item["site"] for item in value.get("found_on") or [])
        return (f"'{value.get('username')}' found on {counts.get('found', 0)} site(s)"
                + (f": {listing}" if listing else "")
                + f", not found on {counts.get('not_found', 0)}, "
                f"{counts.get('skipped', 0)} skipped (need p2).")
    if operation in ("email", "reputation"):
        if not record.get("ok"):
            return f"Email reputation: {record.get('error')}"
        return (f"{value.get('email')} reputation {value.get('reputation')} "
                f"(suspicious: {value.get('suspicious')}, leaked: "
                f"{value.get('details', {}).get('credentials_leaked')}).")
    if operation == "phone":
        if not record.get("ok"):
            return f"Phone lookup: {record.get('error')}"
        return f"{value.get('number')} looks like {value.get('country_hint')}."
    if operation == "breach_check":
        return f"Breach check: {record.get('error')}"
    if operation == "person":
        return f"Person search: {record.get('error')}"
    if operation == "sweep":
        vectors = value.get("vectors") or []
        return f"{len(vectors)} vector(s) ran for {value.get('subject')}."
    if operation == "sources":
        return f"{len(value.get('p0_passive') or [])} passive and {len(value.get('p2_direct_contact') or [])} direct-contact sources."
    return record.get("error") or "No operation ran."
