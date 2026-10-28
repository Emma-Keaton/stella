"""core/media/radiobrowser.py - the Radio Browser community station directory.

Radio Browser is a community database of tens of thousands of internet radio
stations, keyless, served by a cluster of mirrors. This module reads its search
endpoint and normalises the record, because the API's field names are neither
obvious nor stable across mirrors - every station also carries the mirror it came
from so a result can be re-checked.
"""

from __future__ import annotations

from typing import Any, Optional

MIRRORS = (
    "https://de1.api.radio-browser.info",
    "https://de2.api.radio-browser.info",
    "https://at1.api.radio-browser.info",
    "https://nl1.api.radio-browser.info",
    "https://fi1.api.radio-browser.info",
)


def _http():
    try:
        from core.net import http
        return http
    except Exception:
        return None


def search(kwargs: dict, cache: Any = None) -> dict:
    """Search stations by name, country, tag, language, codec or bitrate."""
    http = _http()
    if http is None:
        return {"ok": False, "reason": "the HTTP helper is unavailable"}

    query = (kwargs.get("query") or "").strip()
    country = (kwargs.get("country") or "").strip().upper()
    language = (kwargs.get("language") or "").strip()
    category = (kwargs.get("category") or "").strip()
    limit = _limit(kwargs.get("limit"), 20)

    params = {"limit": str(limit), "hidebroken": "true", "order": "votes", "reverse": "true"}
    if query:
        params["name"] = query
    if country:
        params["countrycode"] = country
    if language:
        params["language"] = language
    if category:
        params["tag"] = category.split(",")[0]

    from urllib.parse import urlencode

    last_reason = "Radio Browser did not answer"
    for mirror in MIRRORS:
        url = f"{mirror}/json/stations/search?{urlencode(params)}"
        result = http.get_json(url, timeout=15.0, cache=cache, ttl=3600.0)
        if result.get("ok"):
            stations = result.get("value") or []
            records = [_summarise(station, mirror) for station in stations
                       if isinstance(station, dict)]
            return {
                "ok": True,
                "count": len(records),
                "stations": records,
                "mirror": mirror,
                "source": "Radio Browser community database",
                "auth_tier": "keyless",
                "filters": {"query": query or None, "country": country or None,
                            "language": language or None, "tag": params.get("tag")},
            }
        last_reason = result.get("reason", last_reason)

    return {"ok": False, "reason": last_reason}


def playable_url(station: dict) -> Optional[str]:
    """The station's resolved stream URL, when it has one."""
    url = (station or {}).get("url_resolved") or (station or {}).get("url")
    return str(url).strip() if url else None


def _summarise(station: dict, mirror: str) -> dict:
    return {
        "stationuuid": station.get("stationuuid"),
        "name": (station.get("name") or "").strip(),
        "country": station.get("country"),
        "countrycode": (station.get("countrycode") or "").upper(),
        "language": station.get("language"),
        "tags": (station.get("tags") or "").strip(),
        "bitrate": station.get("bitrate"),
        "codec": station.get("codec"),
        "votes": station.get("votes"),
        "url": station.get("url"),
        "url_resolved": station.get("url_resolved"),
        "homepage": station.get("homepage"),
        "favicon": station.get("favicon"),
        "hls": station.get("hls"),
        "mirror": mirror,
    }


def _limit(value, default: int = 20, ceiling: int = 200) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    if number <= 0:
        number = default
    return min(number, ceiling)
