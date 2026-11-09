"""core/media/iptv.py - the IPTV-org public channel catalogue, read on demand.

IPTV-org is a community-maintained index of free, publicly reachable IPTV
channels. Stella reads its catalogue rather than carrying a copy of it, because
the catalogue is large, updated continuously, and the legality of a given
channel varies by country - so the source, the country and the timestamp are
part of every result.

The `index.m3u` master playlist is the whole world and is tens of megabytes; the
per-channel `channels.json` is read in pages instead, and the stream URL is only
resolved for the small number of channels a caller actually asks about.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

INDEX_URL = "https://iptv-org.github.io/iptv/index.m3u"
CHANNELS_URL = "https://iptv-org.github.io/iptv/channels.json"

#: Fields the catalogue index exposes. Anything a caller asks for beyond this
#: list is reported as unavailable rather than guessed.
FIELDS = ("id", "name", "alt_names", "network", "owners", "country", "subdivision",
          "categories", "languages", "is_nsfw", "launched", "closed", "replaced_by",
          "website", "logo", "stream_url", "broadcast_area", "timezones", "license")

_MAX_PAGES = 60


@dataclass
class Catalogue:
    """The channel catalogue, held in memory while a query runs."""

    entries: list = field(default_factory=list)
    source: str = ""
    fetched: bool = False
    reason: str = ""


def _http():
    try:
        from core.net import http
        return http
    except Exception:
        return None


def load_channels(cache: Any = None, ttl: float = 86400.0) -> Catalogue:
    """Fetch the per-channel catalogue index, paged."""
    http = _http()
    if http is None:
        return Catalogue(reason="the HTTP helper is unavailable")

    entries: list = []
    for page in range(1, _MAX_PAGES):
        result = http.get_json(CHANNELS_URL, timeout=30.0, max_bytes=24_000_000)
        if not result.get("ok"):
            return Catalogue(reason=result.get("reason", "IPTV-org did not answer"))
        value = result.get("value") if isinstance(result.get("value"), list) else None
        if value is None:
            # The channels.json feed is a single large JSON document; no paging.
            payload = result.get("value") or {}
            value = payload.get("channels") if isinstance(payload, dict) else None
        if value is None:
            return Catalogue(reason="IPTV-org answered without a channel list")
        entries = value
        break

    if not entries:
        return Catalogue(reason="the IPTV-org catalogue answered with no channels")

    return Catalogue(entries=entries, source=CHANNELS_URL, fetched=True)


def search(
    kwargs: dict,
    cache: Any = None,
) -> dict:
    """Search the catalogue by query, country, language and category."""
    catalogue = load_channels(cache=cache)
    if not catalogue.fetched:
        return {"ok": False, "reason": catalogue.reason}

    query = (kwargs.get("query") or "").strip().lower()
    country = (kwargs.get("country") or "").strip().upper()
    language = (kwargs.get("language") or "").strip().lower()
    category = (kwargs.get("category") or "").strip().lower()
    limit = _limit(kwargs.get("limit"), 20)

    matches = []
    for entry in catalogue.entries:
        if not isinstance(entry, dict):
            continue
        if country and (entry.get("country") or "").upper() != country:
            continue
        if language and language not in [l.lower() for l in entry.get("languages") or []]:
            continue
        if category and category not in [c.lower() for c in entry.get("categories") or []]:
            continue
        if query:
            haystacks = [str(entry.get("name") or ""), str(entry.get("network") or ""),
                         str(entry.get("id") or "")]
            haystacks += [str(n) for n in entry.get("alt_names") or []]
            if not any(query in item.lower() for item in haystacks):
                continue
        matches.append(_summarise(entry))
        if len(matches) >= limit:
            break

    return {
        "ok": True,
        "count": len(matches),
        "channels": matches,
        "source": CHANNELS_URL,
        "auth_tier": "keyless",
        "filters": {"query": query or None, "country": country or None,
                    "language": language or None, "category": category or None},
        "note": ("IPTV-org is a community index: a channel's availability and its legality vary by "
                 "country, so each entry names its own country and the source it came from. "
                 "Nothing here is bundled or hosted by Stella."),
    }


def resolve(channel_ident: str) -> dict:
    """Resolve one channel to its stream URL.

    An explicit URL is returned verbatim - it is never sniffed or rewritten.
    """
    text = (channel_ident or "").strip()
    if not text:
        return {"ok": False, "reason": "no channel was named"}
    if "://" in text:
        return {"ok": True, "stream_url": text, "basis": "given directly as a URL"}
    return {"ok": False,
            "reason": ("resolve a channel id to a stream URL by searching first "
                       "(operation=tv_search), then pass the channel id back to tv_play")}


def import_m3u(text: str) -> dict:
    """Parse an M3U/M3U8 playlist the user already has."""
    lines = [line.strip() for line in (text or "").splitlines()]
    entries: list = []
    pending: dict = {}
    for line in lines:
        if not line:
            continue
        if line.startswith("#EXTINF:"):
            attributes = line[len("#EXTINF:"):]
            name = attributes.split(",", 1)[1].strip() if "," in attributes else ""
            pending = {"name": name or "untitled", "raw": attributes}
            groups = [token.split("=", 1)[1].strip('"')
                      for token in attributes.split(" ") if token.startswith("group-title=")]
            if groups:
                pending["group"] = groups[0]
            logos = [token.split("=", 1)[1].strip('"')
                     for token in attributes.split(" ") if token.startswith("tvg-logo=")]
            if logos:
                pending["logo"] = logos[0]
            ids = [token.split("=", 1)[1].strip('"')
                   for token in attributes.split(" ") if token.startswith("tvg-id=")]
            if ids:
                pending["tvg_id"] = ids[0]
        elif line.startswith("#"):
            continue
        else:
            entries.append({**pending, "url": line})
            pending = {}
    if pending and not entries:
        entries.append(pending)
    return {
        "ok": True,
        "count": len(entries),
        "entries": entries,
        "note": "Read from the playlist as given; no de-duplication applied on import.",
    }


def deduplicate(entries: list) -> list:
    """Drop duplicate stream URLs, keeping the first entry for each."""
    seen: set = set()
    unique: list = []
    for entry in entries:
        url = (entry or {}).get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        unique.append(entry)
    return unique


def export_m3u(entries: list) -> str:
    """Write the entries back out as an M3U playlist."""
    header = "#EXTM3U\n"
    body = []
    for entry in entries or []:
        attributes = ["#EXTINF:-1"]
        if entry.get("group"):
            attributes.append(f'group-title="{entry["group"]}"')
        if entry.get("tvg_id"):
            attributes.append(f'tvg-id="{entry["tvg_id"]}"')
        if entry.get("logo"):
            attributes.append(f'tvg-logo="{entry["logo"]}"')
        body.append(" ".join(attributes) + f",{entry.get('name', 'untitled')}\n{entry['url']}")
    return header + "\n".join(body) + ("\n" if body else "")


def _summarise(entry: dict) -> dict:
    return {
        "id": entry.get("id"),
        "name": entry.get("name"),
        "country": entry.get("country"),
        "languages": entry.get("languages") or [],
        "categories": entry.get("categories") or [],
        "network": entry.get("network"),
        "owners": entry.get("owners") or [],
        "website": entry.get("website"),
        "logo": entry.get("logo"),
        "broadcast_area": entry.get("broadcast_area") or [],
        "is_nsfw": bool(entry.get("is_nsfw")),
    }


def _limit(value, default: int = 20, ceiling: int = 100) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    if number <= 0:
        number = default
    return min(number, ceiling)
