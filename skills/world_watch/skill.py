"""
Feature: world_watch
Description: Watch the world through public feeds — flights, vessels, satellites, earthquakes, fires, launches, weather, cameras, radio, transit and infrastructure.
Uses theme tokens from themes.json (no hardcoded colours). Keyless operations run without a key; key-gated operations name the key and report unavailability. Reports stale, rate-limited and fallback feeds explicitly, and never fabricates a position, a time or a beam.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

FEATURE_METADATA = {
    "name": "world_watch",
    "aliases": ["world_watch", "flight tracker", "track flights", "flights over",
                "vessel tracker", "ship tracking", "satellite tracker", "satellite passes",
                "track satellites", "iss pass", "when does the iss pass", "earthquake",
                "earthquakes", "wildfire", "fire tracking", "launch tracker", "space launches",
                "rocket launch", "cyclone tracker", "hurricane tracker", "weather radar",
                "air quality", "public cameras", "world radio", "internet radio", "transit",
                "bikeshare", "alpr cameras", "street imagery", "infrastructure atlas",
                "traffic flow", "military flights", "gnss interference", "submarine cables"],
    "description": (
        "Watch the world through public feeds: live flights (civilian and military) over "
        "any area, vessel positions, satellite catalogues and ground-pass predictions, "
        "earthquakes, wildfires, rocket launches, cyclone tracks, forecast wind and rain "
        "radar, air quality, public cameras, internet radio stations, transit and bikeshare, "
        "ALPR camera locations, street-level imagery, submarine cables, datacenters and dams, "
        "and traffic flow. Keyless operations work without any API key; operations that need "
        "a key name the key and report unavailability instead of returning nothing. Reports "
        "when a feed is stale, rate-limited or on a fallback, and never fabricates a position."
    ),
    "triggers": [
        "track flights", "flights over", "what planes are overhead", "flight radar",
        "track ships", "vessels near", "ship tracking", "ais ships",
        "satellite", "iss", "starlink", "when will the iss pass", "satellite pass",
        "earthquake", "seismic", "quake near", "wildfire", "fire near", "active fires",
        "rocket launch", "spacex launch", "upcoming launches", "launch schedule",
        "hurricane", "cyclone", "typhoon", "weather radar", "rain radar",
        "air quality", "aqi", "pollution near", "public camera", "traffic camera",
        "radio station", "internet radio", "bus locations", "bikeshare", "bike stations",
        "license plate cameras", "alpr", "street view", "mapillary", "submarine cable",
        "datacenter", "military aircraft", "gnss jamming", "traffic jam",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: flights | military_flights | vessels | satellites | space_passes | earthquakes | fires | cyclones | launches | wind | radar | air_quality | cameras | radio | transit | bikeshare | alpr | street_level | infrastructure | traffic | gnss_integrity | sources. Defaults to flights.",
            },
            "area": {
                "type": "STRING",
                "description": "Free-text place name (e.g. 'Mumbai', 'Bay Area', 'my area' or 'here' for the device location). Used to geocode and to build a bounding box.",
            },
            "bbox": {
                "type": "STRING",
                "description": "Explicit bounding box as 'lat_min,lat_max,lon_min,lon_max' in decimal degrees. Overrides the area and is never inferred.",
            },
            "lat": {"type": "STRING",
                    "description": "Observer latitude in decimal degrees for point-based operations."},
            "lon": {"type": "STRING",
                    "description": "Observer longitude in decimal degrees."},
            "radius_km": {"type": "NUMBER",
                          "description": "Bounding-box radius in kilometres when no bbox is given. Defaults to 130 km."},
            "norad_id": {"type": "INTEGER",
                         "description": "NORAD catalogue id for satellite operations. Defaults to 25544 (ISS)."},
            "hours": {"type": "NUMBER",
                      "description": "Prediction horizon in hours for satellite passes. Defaults to 48."},
            "min_elevation": {"type": "NUMBER",
                              "description": "Minimum elevation in degrees for a pass to count. Defaults to 10."},
            "category": {"type": "STRING",
                         "description": "Category filter: launch provider, transit operator, channel country, or infrastructure type (datacenter, dam, cable)."},
            "limit": {"type": "INTEGER", "description": "Maximum items to return. Defaults to 20."},
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "author": "Stella",
    "category": "observability",
    "optional_dependencies": ["matplotlib"],
    "notes": "Sources: OpenSky Network, adsb.lol, AISStream, CelesTrak, USGS, NASA FIRMS, WFIGS/NIFC, NOAA NHC/CPHC, NOAA GFS/ECMWF, NOAA nowCOAST, ECCC GeoMet, Launch Library 2, GTFS-RT operators, GBFS, OSRM on FOSSGIS, Radio Browser, Mapillary, KartaView, Panoramax, OpenStreetMap.",
}


def _theme_colour(key: str, fallback: str | None = None) -> str | None:
    """Read a colour from the active theme, with an optional fallback."""
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


def _http():
    try:
        from core.net import http
        return http
    except Exception:
        return None


def _cache():
    try:
        from core.net.http import feed_cache
        return feed_cache(ttl=900.0)
    except Exception:
        return None


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    """One operation record, stating its own outcome and the reason either way."""
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _as_float(value, default=None) -> Optional[float]:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _as_int(value, default=None) -> Optional[int]:
    number = _as_float(value)
    return int(number) if number is not None else default


def _clamp_limit(value, default: int = 20, ceiling: int = 200) -> int:
    number = _as_int(value, default)
    if number is None or number <= 0:
        number = default
    return min(number, ceiling)


def _device_location() -> Optional[Dict[str, float]]:
    try:
        from core.device_location import get_device_location
        location = get_device_location() or {}
        latitude = _as_float(location.get("latitude"))
        longitude = _as_float(location.get("longitude"))
        if latitude is None or longitude is None:
            return None
        return {"latitude": latitude, "longitude": longitude,
                "city": str(location.get("city") or "Current Location")}
    except Exception:
        return None


def _geocode(area: str) -> Dict[str, Any]:
    """Resolve a place name to a centre point, or report why it could not."""
    text = (area or "").strip()
    lowered = text.lower()

    if lowered in ("my area", "local", "here", "current", "device", "current location", ""):
        location = _device_location()
        if location:
            return {"ok": True, "latitude": location["latitude"], "longitude": location["longitude"],
                    "name": location["city"], "source": "device location"}
        return {"ok": False, "reason": "no device location is available, and no area was given to geocode"}

    http = _http()
    if http is None:
        return {"ok": False, "reason": "the HTTP helper is unavailable, so the area cannot be geocoded"}

    encoded = _quote(text)
    result = http.get_json(
        f"https://geocoding-api.open-meteo.com/v1/search?name={encoded}&count=1&language=en&format=json",
        timeout=8.0, cache=_cache(), ttl=86400.0)
    if not result.get("ok"):
        return {"ok": False, "reason": result.get("reason", "geocoding failed")}
    results = (result.get("value") or {}).get("results") or []
    if not results:
        return {"ok": False, "reason": f"no place called '{text}' was found by the geocoder"}
    top = results[0]
    latitude = _as_float(top.get("latitude"))
    longitude = _as_float(top.get("longitude"))
    if latitude is None or longitude is None:
        return {"ok": False, "reason": f"the geocoder returned no coordinates for '{text}'"}
    label = str(top.get("name") or text)
    country = str(top.get("country") or "")
    return {"ok": True, "latitude": latitude, "longitude": longitude,
            "name": f"{label}, {country}".strip(", "), "source": "Open-Meteo geocoding"}


def _quote(text: str) -> str:
    try:
        from urllib.parse import quote
        return quote(text)
    except Exception:
        return text.replace(" ", "%20")


def _bounds(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve the bounding box: explicit bbox wins, then area, then device."""
    http = _http()

    explicit = (kwargs.get("bbox") or "").strip()
    if explicit:
        parts = [p.strip() for p in explicit.split(",")]
        if len(parts) != 4:
            return {"ok": False, "reason": "bbox must be 'lat_min,lat_max,lon_min,lon_max'"}
        lat_min, lat_max, lon_min, lon_max = (_as_float(p) for p in parts)
        if None in (lat_min, lat_max, lon_min, lon_max):
            return {"ok": False, "reason": "bbox values were not all numbers"}
        if not _plausible_bounds(lat_min, lat_max, lon_min, lon_max):
            return {"ok": False, "reason": (
                f"bbox {explicit} does not describe a real box: latitudes must be -90..90, "
                "longitudes -180..180, and min must be below max")}
        return {"ok": True, "lat_min": lat_min, "lat_max": lat_max,
                "lon_min": lon_min, "lon_max": lon_max, "source": "explicit bbox"}

    geocoded = _geocode(str(kwargs.get("area") or ""))
    if not geocoded.get("ok"):
        return geocoded

    radius = _as_float(kwargs.get("radius_km"), 130.0) or 130.0
    radius = max(0.5, min(radius, 1800.0))
    delta = radius / 111.0
    latitude = geocoded["latitude"]
    lat_min = max(-90.0, latitude - delta)
    lat_max = min(90.0, latitude + delta)
    scale = max(0.05, abs(_safe_cosine(latitude)))
    lon_min = geocoded["longitude"] - delta / scale
    lon_max = geocoded["longitude"] + delta / scale
    return {"ok": True, "lat_min": lat_min, "lat_max": lat_max,
            "lon_min": lon_min, "lon_max": lon_max,
            "centre": geocoded, "source": geocoded.get("source"), "radius_km": radius}


def _safe_cosine(latitude: float) -> float:
    try:
        import math
        return math.cos(math.radians(latitude))
    except Exception:
        return 1.0


def _plausible_bounds(lat_min, lat_max, lon_min, lon_max) -> bool:
    if not (-90.0 <= lat_min <= 90.0 and -90.0 <= lat_max <= 90.0):
        return False
    if not (-180.0 <= lon_min <= 180.0 and -180.0 <= lon_max <= 180.0):
        return False
    return lat_min < lat_max and lon_min < lon_max


def _bounds_or_error(kwargs: Dict[str, Any]) -> tuple:
    resolved = _bounds(kwargs)
    if not resolved.get("ok"):
        return None, _op("flights", False, None, resolved.get("reason", "no area could be resolved"))
    return resolved, None


def _centre(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """The centre of whatever area the caller asked about.

    An explicit bbox is reduced to its centre (the callers that need one do not
    accept a box), and an area is geocoded first.
    """
    explicit = (kwargs.get("bbox") or "").strip()
    if explicit:
        bounds, error = _bounds_or_error(kwargs)
        if error is not None:
            return {"ok": False, "reason": bounds.get("reason") if not isinstance(bounds, dict) else "no box"}
        return {"ok": True,
                "latitude": (bounds["lat_min"] + bounds["lat_max"]) / 2.0,
                "longitude": (bounds["lon_min"] + bounds["lon_max"]) / 2.0,
                "source": "centre of the explicit bbox"}

    observer = _observer(kwargs)
    if observer and observer.get("ok"):
        return observer
    if observer and not observer.get("ok"):
        return observer

    return _geocode(str(kwargs.get("area") or ""))


def _clamp_radius_km(value, default: float = 130.0, ceiling: float = 250.0) -> float:
    radius = _as_float(value, default) or default
    return max(1.0, min(radius, ceiling))


# ---------------------------------------------------------------------- flights

def _op_flights(kwargs: Dict[str, Any]) -> dict:
    bounds, error = _bounds_or_error(kwargs)
    if error is not None:
        return error

    http = _http()
    if http is None:
        return _op("flights", False, None, "the HTTP helper is unavailable")

    url = ("https://opensky-network.org/api/states/all?"
           f"lamin={bounds['lat_min']:.4f}&lomin={bounds['lon_min']:.4f}"
           f"&lamax={bounds['lat_max']:.4f}&lomax={bounds['lon_max']:.4f}")
    fetched = http.get_json(url, timeout=12.0)
    if not fetched.get("ok"):
        return _op("flights", False, None, fetched.get("reason", "OpenSky did not answer"))
    payload = fetched.get("value") or {}
    states = payload.get("states") or []
    limit = _clamp_limit(kwargs.get("limit"), 20)

    flights = []
    for state in states[:limit]:
        if not isinstance(state, (list, tuple)) or len(state) < 8:
            continue
        latitude, longitude = state[6], state[5]
        if latitude is None or longitude is None:
            continue
        altitude_m = state[7]
        velocity = state[9]
        flights.append({
            "icao24": state[0],
            "callsign": (state[1] or "").strip() or "UNKNOWN",
            "origin_country": state[2],
            "longitude": longitude,
            "latitude": latitude,
            "on_ground": bool(state[8]),
            "altitude_ft": round(altitude_m * 3.28084) if altitude_m is not None else None,
            "speed_kmh": round(velocity * 3.6, 1) if velocity is not None else None,
            "heading_deg": round(state[10]) if len(state) > 10 and state[10] is not None else None,
        })

    centre = bounds.get("centre") or {}
    return _op("flights", True, {
        "count": len(states),
        "returned": len(flights),
        "flights": flights,
        "bbox": {k: bounds[k] for k in ("lat_min", "lat_max", "lon_min", "lon_max")},
        "area": centre.get("name"),
        "source": "OpenSky Network (anonymous)",
        "auth_tier": "keyless",
        "note": ("OpenSky's anonymous tier allows about 400 API credits a day, and each bounding-box "
                 "request costs 4, so roughly 100 such queries per day. This result is not cached "
                 "beyond this run; repeated area queries will eventually return HTTP 429 and that "
                 "will be reported rather than hidden."),
    })


def _op_military(kwargs: Dict[str, Any]) -> dict:
    """Military and emergency ADS-B contacts, from the adsb.lol point query.

    The endpoint is a centre point plus a radius in kilometres (250 km maximum),
    so an area or bounding box is reduced to its centre before the query.
    """
    http = _http()
    if http is None:
        return _op("military_flights", False, None, "the HTTP helper is unavailable")

    centre = _centre(kwargs)
    if not centre.get("ok"):
        return _op("military_flights", False, None, centre.get("reason", "no area could be resolved"))

    radius = _clamp_radius_km(kwargs.get("radius_km"), default=130.0, ceiling=250.0)
    url = (f"https://api.adsb.lol/v2/lat/{centre['latitude']:.4f}"
           f"/lon/{centre['longitude']:.4f}/dist/{radius}")
    fetched = http.get_json(url, timeout=15.0)
    if not fetched.get("ok"):
        return _op("military_flights", False, None,
                   fetched.get("reason", "adsb.lol did not answer"))

    aircraft = (fetched.get("value") or {}).get("ac") or []
    limit = _clamp_limit(kwargs.get("limit"), 20)
    records = []
    for entry in aircraft[:limit]:
        altitude = entry.get("alt_geo") or entry.get("alt_baro")
        records.append({
            "icao24": str(entry.get("hex") or "").upper(),
            "callsign": (entry.get("flight") or "").strip(),
            "registration": entry.get("r"),
            "type": entry.get("t"),
            "latitude": entry.get("lat"),
            "longitude": entry.get("lon"),
            "altitude_ft": altitude,
            "ground_speed_kt": entry.get("gs"),
            "track_deg": entry.get("track"),
            "squawk": entry.get("squawk"),
            "emergency": entry.get("emergency"),
            "category": entry.get("category"),
        })

    return _op("military_flights", True, {
        "count": len(aircraft),
        "returned": len(records),
        "aircraft": records,
        "radius_km": radius,
        "area": centre.get("name"),
        "source": "adsb.lol community feed (point query)",
        "auth_tier": "keyless",
        "note": ("The endpoint is a centre point plus a radius, capped at 250 km, so an area or box "
                 "is reduced to its centre. Military traffic carries the feed's own classification "
                 "of the transponder reply, not an independent identification."),
    })


def _op_vessels(kwargs: Dict[str, Any]) -> dict:
    from core.providers import registry

    if not registry.has_service_credential("aisstream"):
        return _op("vessels", False, None, (
            "No AISSTREAM_API_KEY is configured, so live vessel positions cannot be read. AISStream "
            "is the keyed source for ship traffic; nothing is invented in its place. Add the key in "
            "Settings > Cloud Providers to enable this layer."))

    return _op("vessels", False, None, (
        "AISSTREAM_API_KEY is configured, but the live vessel feed needs a websocket session that "
        "holds open for the whole query; this skill reports that as unsupported rather than "
        "returning a stale snapshot. Use a vessel-tracking dashboard for live AIS."))


def _op_satellites(kwargs: Dict[str, Any]) -> dict:
    http = _http()
    if http is None:
        return _op("satellites", False, None, "the HTTP helper is unavailable")

    group = str(kwargs.get("category") or "stations").strip() or "stations"
    fetched = http.get_text(
        f"https://celestrak.org/NORAD/elements/gp.php?GROUP={_quote(group)}&FORMAT=TLE",
        timeout=15.0, cache=_cache(), ttl=3600.0)
    if not fetched.get("ok"):
        return _op("satellites", False, None, fetched.get("reason", "CelesTrak did not answer"))
    lines = [line for line in str(fetched.get("value") or "").splitlines() if line.strip()]
    limit = _clamp_limit(kwargs.get("limit"), 20)
    catalog = []
    from core.astro.sgp4 import Satrec
    for index in range(0, min(len(lines), limit * 3) - 2, 3):
        name, line1, line2 = lines[index], lines[index + 1], lines[index + 2]
        try:
            sat = Satrec.twoline2rv(line1, line2)
            described = sat.describe()
            catalog.append({
                "name": name.strip(),
                "norad_id": sat.satnum,
                "period_minutes": described["period_minutes"],
                "inclination_deg": described["inclination_deg"],
                "apogee_km": described["apogee_km"],
                "perigee_km": described["perigee_km"],
                "checksum_verified": sat.checksum_verified,
            })
        except Exception:
            continue

    return _op("satellites", True, {
        "count": len(catalog),
        "requested_group": group,
        "satellites": catalog[:limit],
        "source": "CelesTrak (TLE, keyless)",
        "auth_tier": "keyless",
        "note": ("CelesTrak also publishes the full Starlink shell under group 'starlink' and the "
                 "active catalogue under 'active'."),
    })


def _op_space_passes(kwargs: Dict[str, Any]) -> dict:
    http = _http()
    if http is None:
        return _op("space_passes", False, None, "the HTTP helper is unavailable")

    observer = _observer(kwargs)
    if observer is None:
        return _op("space_passes", False, None,
                   "an observer latitude and longitude are required for pass geometry; give them "
                   "explicitly, or use area='here' to use the device location")

    norad_id = _as_int(kwargs.get("norad_id"), 25544)
    fetched = http.get_text(
        f"https://celestrak.org/NORAD/elements/gp.php?CATNR={norad_id}&FORMAT=TLE",
        timeout=15.0, cache=_cache(), ttl=3600.0)
    if not fetched.get("ok"):
        return _op("space_passes", False, None, fetched.get("reason", "CelesTrak did not answer"))

    lines = [line for line in str(fetched.get("value") or "").splitlines() if line.strip()]
    if len(lines) < 3:
        return _op("space_passes", False, None,
                   f"the catalogue returned fewer than three TLE lines for NORAD {norad_id}")

    try:
        from core.astro.passes import predict_passes
        from core.astro.sgp4 import Satrec

        sat = Satrec.twoline2rv(lines[1], lines[2])
        horizon_hours = max(0.1, min(_as_float(kwargs.get("hours"), 48.0) or 48.0, 24 * 14))
        min_elevation = max(0.0, min(_as_float(kwargs.get("min_elevation"), 10.0) or 10.0, 89.0))
        limit = _clamp_limit(kwargs.get("limit"), 5)
        passes = predict_passes(sat, observer["latitude"], observer["longitude"],
                                min_elevation_deg=min_elevation, horizon_hours=horizon_hours,
                                step_seconds=30.0)
    except Exception as exc:
        return _op("space_passes", False, None, f"{type(exc).__name__}: {exc}")

    return _op("space_passes", True, {
        "norad_id": sat.satnum,
        "element_set": f"{lines[0].strip()} (CelesTrak)",
        "checksum_verified": sat.checksum_verified,
        "observer": {"latitude": observer["latitude"], "longitude": observer["longitude"]},
        "horizon_hours": horizon_hours,
        "min_elevation_deg": min_elevation,
        "propagation": {
            "method": sat.describe()["method"],
            "accuracy_km": sat.describe()["accuracy_km"],
            "note": ("Pass times are computed from these elements with the stated method, on a "
                     "spherical-earth horizon with no atmosphere or terrain. They are a geometry "
                     "answer, not a tracking service."),
        },
        "passes": [window.as_dict() for window in passes[:limit]],
        "pass_count": len(passes),
        "summaries": [window.summary() for window in passes[:limit]],
        "source": "CelesTrak + local propagation",
        "auth_tier": "keyless",
    })


def _op_earthquakes(kwargs: Dict[str, Any]) -> dict:
    http = _http()
    if http is None:
        return _op("earthquakes", False, None, "the HTTP helper is unavailable")

    bounds, error = _bounds_or_error(kwargs)
    if error is not None:
        return error

    window = str(kwargs.get("category") or "all_day").strip() or "all_day"
    fetched = http.get_json(
        f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{window}.geojson",
        timeout=12.0, cache=_cache(), ttl=300.0)
    if not fetched.get("ok"):
        return _op("earthquakes", False, None, fetched.get("reason", "USGS did not answer"))

    features = (fetched.get("value") or {}).get("features") or []
    limit = _clamp_limit(kwargs.get("limit"), 20)
    inside = []
    for feature in features:
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if len(coordinates) < 3:
            continue
        longitude, latitude, depth_km = coordinates[0], coordinates[1], coordinates[2]
        if not (bounds["lat_min"] <= latitude <= bounds["lat_max"]
                and bounds["lon_min"] <= longitude <= bounds["lon_max"]):
            continue
        properties = feature.get("properties") or {}
        inside.append({
            "place": properties.get("place"),
            "magnitude": properties.get("mag"),
            "time": properties.get("time"),
            "depth_km": round(depth_km, 1) if isinstance(depth_km, (int, float)) else None,
            "tsunami_warning": bool(properties.get("tsunami")),
            "felt_reports": properties.get("felt"),
            "significance": properties.get("sig"),
            "detail_url": properties.get("url"),
        })
        if len(inside) >= limit:
            break

    total_count = len(features)
    return _op("earthquakes", True, {
        "feed_window": window,
        "events_in_feed": total_count,
        "events_in_area": len(inside),
        "earthquakes": inside,
        "area": (bounds.get("centre") or {}).get("name"),
        "source": "USGS real-time earthquake feed",
        "auth_tier": "keyless",
        "note": (f"The USGS {window} feed was read whole and filtered to the box, so the counts above "
                 "describe that feed window, not every earthquake."),
    })


def _op_fires(kwargs: Dict[str, Any]) -> dict:
    http = _http()
    if http is None:
        return _op("fires", False, None, "the HTTP helper is unavailable")

    bounds, error = _bounds_or_error(kwargs)
    if error is not None:
        return error

    from core.providers import registry

    if not registry.has_service_credential("firms"):
        return _op("fires", False, None, (
            "No NASA_FIRMS_MAP_KEY is configured, so fire detections cannot be read. A free key is "
            "issued at firms.modaps.eosdis.nasa.gov; add it in Settings > Cloud Providers. Until "
            "then this layer reports unavailable rather than showing a stale or empty fire list."))

    from urllib.parse import quote

    try:
        from core.providers.catalogue import keyed_service_url

        base = keyed_service_url("firms", "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}")
    except KeyError:
        return _op("fires", False, None, (
            "The FIRMS key disappeared between the check and the request; nothing was sent."))
    url = (f"{base}/"
           f"VIIRS_SNPP_NRT/{bounds['lon_min']},{bounds['lat_min']},"
           f"{bounds['lon_max']},{bounds['lat_max']}/1")
    fetched = http.get_text(url, timeout=20.0)
    if not fetched.get("ok"):
        return _op("fires", False, None, fetched.get("reason", "FIRMS did not answer"))
    text = str(fetched.get("value") or "")
    rows = [line.split(",") for line in text.splitlines() if line.strip()]
    if not rows:
        return _op("fires", False, None, "FIRMS answered with no rows")

    header = [name.strip().lower() for name in rows[0]]
    limit = _clamp_limit(kwargs.get("limit"), 20)
    detections = []
    for row in rows[1:limit + 1]:
        record = dict(zip(header, row))
        detections.append({
            "latitude": _as_float(record.get("latitude")),
            "longitude": _as_float(record.get("longitude")),
            "brightness": record.get("bright_ti4") or record.get("brightness"),
            "confidence": record.get("confidence"),
            "acquisition": f"{record.get('acq_date', '')} {record.get('acq_time', '')}".strip(),
            "satellite": record.get("satellite"),
        })

    return _op("fires", True, {
        "count": max(0, len(rows) - 1),
        "returned": len(detections),
        "detections": detections,
        "source": "NASA FIRMS (VIIRS SNPP NRT, last 24h)",
        "auth_tier": "free key",
        "note": ("Detections are satellite brightness readings over the last day; a detection is "
                 "evidence of heat, not confirmation of a wildfire."),
    })


def _op_cyclones(kwargs: Dict[str, Any]) -> dict:
    http = _http()
    if http is None:
        return _op("cyclones", False, None, "the HTTP helper is unavailable")

    basin = str(kwargs.get("category") or "AL").strip().upper() or "AL"
    fetched = http.get_json(
        f"https://www.nhc.noaa.gov/nhc_{basin}.json", timeout=12.0, cache=_cache(), ttl=900.0)
    if not fetched.get("ok"):
        return _op("cyclones", False, None, fetched.get("reason", "the NHC did not answer"))

    payload = fetched.get("value") or {}
    active = payload.get("activeStorms") or []
    limit = _clamp_limit(kwargs.get("limit"), 10)
    storms = [{"name": storm.get("name"), "id": storm.get("id"),
               "classification": storm.get("classification"),
               "intensity_kt": storm.get("intensity"),
               "latitude": storm.get("latitude"), "longitude": storm.get("longitude"),
               "movement": storm.get("movement")} for storm in active[:limit]]

    return _op("cyclones", True, {
        "basin": basin,
        "active_storms": storms,
        "source": "NOAA NHC advisories",
        "auth_tier": "keyless",
        "note": ("Advisory positions and forecast tracks are the published forecast, including its "
                 "uncertainty cones; a cone is a probability field, not a path."),
    })


def _op_launches(kwargs: Dict[str, Any]) -> dict:
    http = _http()
    if http is None:
        return _op("launches", False, None, "the HTTP helper is unavailable")

    from core.providers import registry

    token = "launchlibrary" if registry.has_service_credential("launchlibrary") else ""
    limit = _clamp_limit(kwargs.get("limit"), 20)
    params = [f"limit={limit}", "mode=detailed"]
    if token:
        params.append(f"token={token}")

    fetched = http.get_json(
        "https://ll.thespacedevs.com/2.2.0/launch/upcoming?" + "&".join(params),
        timeout=15.0, cache=_cache(), ttl=1800.0)
    if not fetched.get("ok"):
        return _op("launches", False, None, fetched.get("reason", "Launch Library 2 did not answer"))

    results = (fetched.get("value") or {}).get("results") or []
    launches = []
    for entry in results[:limit]:
        pad = entry.get("pad") or {}
        status = entry.get("status") or {}
        launches.append({
            "name": entry.get("name"),
            "net": entry.get("net"),
            "status": status.get("name"),
            "probability": entry.get("probability"),
            "provider": (entry.get("launch_service_provider") or {}).get("name"),
            "pad": pad.get("name"),
            "location": (pad.get("location") or {}).get("name"),
            "mission": (entry.get("mission") or {}).get("name"),
            "mission_description": ((entry.get("mission") or {}).get("description") or "")[:240],
            "webcast_live": entry.get("webcast_live"),
            "hashtag": entry.get("hashtag"),
        })

    return _op("launches", True, {
        "count": len(launches),
        "launches": launches,
        "source": "Launch Library 2",
        "auth_tier": "anonymous keyless (rate-limited) or key for a higher allowance",
        "note": ("Launch times are the published target window and slip frequently; a time is what "
                 "the provider published, not a promise."),
    })


def _op_wind(kwargs: Dict[str, Any]) -> dict:
    http = _http()
    if http is None:
        return _op("wind", False, None, "the HTTP helper is unavailable")

    bounds, error = _bounds_or_error(kwargs)
    if error is not None:
        return error

    centre = bounds.get("centre") or {}
    if "latitude" not in centre:
        latitude = (bounds["lat_min"] + bounds["lat_max"]) / 2.0
        longitude = (bounds["lon_min"] + bounds["lon_max"]) / 2.0
    else:
        latitude = centre["latitude"]
        longitude = centre["longitude"]

    url = ("https://api.open-meteo.com/v1/forecast?"
           f"latitude={latitude:.4f}&longitude={longitude:.4f}"
           "&hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m,temperature_2m"
           "&forecast_days=2&timezone=UTC")
    fetched = http.get_json(url, timeout=12.0, cache=_cache(), ttl=900.0)
    if not fetched.get("ok"):
        return _op("wind", False, None, fetched.get("reason", "Open-Meteo did not answer"))
    payload = fetched.get("value") or {}
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    speeds = hourly.get("wind_speed_10m") or []
    directions = hourly.get("wind_direction_10m") or []
    limit = _clamp_limit(kwargs.get("limit"), 12)
    samples = [{"time": times[index], "speed_kmh": speeds[index],
                "direction_deg": directions[index]}
               for index in range(min(len(times), len(speeds), limit))]

    return _op("wind", True, {
        "forecast_hours": samples,
        "max_speed_kmh": max(speeds) if speeds else None,
        "units": payload.get("hourly_units"),
        "model": (payload.get("current") or {}).get("model", "Open-Meteo best-match model"),
        "source": "Open-Meteo (NOAA GFS / ECMWF IFS blend)",
        "auth_tier": "keyless",
    })


def _op_radar(kwargs: Dict[str, Any]) -> dict:
    http = _http()
    if http is None:
        return _op("radar", False, None, "the HTTP helper is unavailable")

    fetched = http.get_json("https://api.rainviewer.com/public/weather-maps.json",
                           timeout=12.0, cache=_cache(), ttl=600.0)
    if not fetched.get("ok"):
        return _op("radar", False, None, fetched.get("reason", "RainViewer did not answer"))
    value = fetched.get("value") or {}
    satellite = value.get("satellite") or {}
    infrared = satellite.get("infrared") or []
    generated = value.get("generated")
    frames = [{"time": frame.get("time"), "tile_url": frame.get("path"), "steps": frame.get("steps")}
              for frame in infrared[-6:]]
    return _op("radar", True, {
        "radar_frames": frames,
        "host": value.get("host"),
        "generated": generated,
        "source": "RainViewer public weather maps",
        "auth_tier": "keyless",
        "note": ("Radar and satellite frames are the most recent observations published by the "
                 "source; a frame is a snapshot, not a forecast."),
    })


def _op_air_quality(kwargs: Dict[str, Any]) -> dict:
    http = _http()
    if http is None:
        return _op("air_quality", False, None, "the HTTP helper is unavailable")

    observer = _observer(kwargs) or _geocode(str(kwargs.get("area") or ""))
    if not observer.get("ok"):
        return _op("air_quality", False, None, observer.get(
            "reason", "a location is required to read air quality"))

    url = ("https://air-quality-api.open-meteo.com/v1/air-quality?"
           f"latitude={observer['latitude']:.4f}&longitude={observer['longitude']:.4f}"
           "&hourly=pm10,pm2_5,us_aqi,european_aqi&timezone=auto&forecast_days=1")
    fetched = http.get_json(url, timeout=12.0)
    if not fetched.get("ok"):
        return _op("air_quality", False, None, fetched.get("reason", "Open-Meteo did not answer"))
    hourly = (fetched.get("value") or {}).get("hourly") or {}
    times = hourly.get("time") or []
    us_aqi = hourly.get("us_aqi") or []
    eu_aqi = hourly.get("european_aqi") or []
    limit = _clamp_limit(kwargs.get("limit"), 8)
    now_index = 0
    samples = [{"time": times[now_index + offset] if now_index + offset < len(times) else None,
                "us_aqi": us_aqi[now_index + offset] if now_index + offset < len(us_aqi) else None,
                "european_aqi": eu_aqi[now_index + offset] if now_index + offset < len(eu_aqi) else None}
               for offset in range(min(limit, max(len(times), 0)))]
    return _op("air_quality", True, {
        "location": observer,
        "hourly": samples,
        "source": "Open-Meteo air quality (CAMS)",
        "auth_tier": "keyless",
        "note": ("Air-quality indices are modelled estimates from CAMS, not a measurement at this "
                 "exact address; the ECCC AQHI scale used by some agencies is a different scale."),
    })


def _op_cameras(kwargs: Dict[str, Any]) -> dict:
    http = _http()
    if http is None:
        return _op("cameras", False, None, "the HTTP helper is unavailable")

    bounds, error = _bounds_or_error(kwargs)
    if error is not None:
        return error

    box = (f"{bounds['lat_min']},{bounds['lon_min']},{bounds['lat_max']},{bounds['lon_max']}")
    query = f"""
[out:json][timeout:25];
node["highway"="speed_camera"]["man_made"="surveillance"]({box});
out center {int(_clamp_limit(kwargs.get('limit'), 40))};
"""
    fetched = http.get_json(
        "https://overpass-api.de/api/interpreter?data=" + _quote(query.strip()),
        timeout=30.0)
    if not fetched.get("ok"):
        return _op("cameras", False, None, fetched.get("reason", "Overpass did not answer"))

    elements = (fetched.get("value") or {}).get("elements") or []
    cameras = []
    for element in elements[: _clamp_limit(kwargs.get("limit"), 40)]:
        tags = element.get("tags") or {}
        cameras.append({
            "id": element.get("id"),
            "latitude": (element.get("center") or element).get("lat"),
            "longitude": (element.get("center") or element).get("lon"),
            "operator": tags.get("operator"),
            "name": tags.get("name"),
            "description": tags.get("description"),
            "camera:mount": tags.get("camera:mount"),
        })
    return _op("cameras", True, {
        "count": len(cameras),
        "cameras": cameras,
        "source": "OpenStreetMap (ALPR and surveillance camera tags)",
        "auth_tier": "keyless",
        "note": ("These are mapped camera *locations* only: no plate data and no video. Positions "
                 "come from contributor mapping and may be incomplete."),
    })


def _op_radio(kwargs: Dict[str, Any]) -> dict:
    http = _http()
    if http is None:
        return _op("radio", False, None, "the HTTP helper is unavailable")

    name = str(kwargs.get("category") or "").strip()
    params = f"name={_quote(name)}" if name else "order=votes&reverse=true"
    limit = _clamp_limit(kwargs.get("limit"), 20)
    url = f"https://de1.api.radio-browser.info/json/stations/search?{params}&limit={limit}&hidebroken=true"
    fetched = http.get_json(url, timeout=15.0, cache=_cache(), ttl=3600.0)
    if not fetched.get("ok"):
        return _op("radio", False, None, fetched.get("reason", "Radio Browser did not answer"))

    stations = fetched.get("value") or []
    records = [{"name": station.get("name"), "country": station.get("country"),
                "countrycode": station.get("countrycode"),
                "language": station.get("language"), "tags": station.get("tags"),
                "bitrate": station.get("bitrate"), "codec": station.get("codec"),
                "votes": station.get("votes"), "url": station.get("url_resolved"),
                "homepage": station.get("homepage"), "favicon": station.get("favicon")}
               for station in stations if isinstance(station, dict)]
    return _op("radio", True, {
        "count": len(records),
        "stations": records,
        "source": "Radio Browser (community database)",
        "auth_tier": "keyless",
    })


def _op_transit(kwargs: Dict[str, Any]) -> dict:
    http = _http()
    if http is None:
        return _op("transit", False, None, "the HTTP helper is unavailable")

    network = str(kwargs.get("category") or "").strip().lower()
    catalog = _transit_networks()
    if not network:
        networks = ", ".join(f"{name}" for name in sorted(catalog))
        return _op("transit", True, {
            "available_networks": networks,
            "note": ("Transit positions come from each transit operator's own GTFS-Realtime feed. "
                     "Name a network to query it, e.g. category='ttc' for Toronto Transit, or "
                     "'by' for Bièvre."),
            "source": "public operator GTFS-Realtime feeds",
            "auth_tier": "keyless (per operator)",
        })
    if network not in catalog:
        return _op("transit", False, None,
                  f"no GTFS-Realtime feed for '{network}' is registered in this build; "
                  f"known networks: {', '.join(sorted(catalog))}")
    return _op("transit", False, None, (
        f"GTFS-Realtime payloads are Protocol Buffers. This reader does not decode protobuf, so "
        f"positions for '{network}' are reported as unsupported rather than parsed wrong. Use "
        "a transit dashboard for live vehicle positions."))


def _transit_networks() -> Dict[str, str]:
    return {
        "ttc": "Toronto Transit Commission",
        "by": "Bièvre (Île-de-France)",
        "mbta": "MBTA (Boston)",
        "cmt": "Capital MetroTrail (Austin)",
        "hsl": "HSL (Helsinki)",
        "ovapi": "OVapi (Netherlands, aggregated)",
        "entur": "Entur (Norway)",
        "translink": "Translink (South East Queensland)",
    }


def _op_bikeshare(kwargs: Dict[str, Any]) -> dict:
    http = _http()
    if http is None:
        return _op("bikeshare", False, None, "the HTTP helper is unavailable")

    network = str(kwargs.get("category") or "").strip().lower()
    if not network:
        return _op("bikeshare", False, None,
                   "name a bikeshare network id (category=...) — for example 'velib' for Paris "
                   "Vélib, or a GBFS system id from the systems index")
    known = {"velib": "https://gbfs.api.velib-metropole.fr/gbfs/gbfs_station_status.json",
             "paris": "https://gbfs.api.velib-metropole.fr/gbfs/gbfs_station_status.json"}
    url = known.get(network, f"https://gbfs.veloparking.com/gbfs/{network}/station_status.json")

    fetched = http.get_json(url, timeout=15.0)
    if not fetched.get("ok"):
        return _op("bikeshare", False, None, fetched.get("reason", "the GBFS feed did not answer"))
    stations = ((fetched.get("value") or {}).get("data") or {}).get("stations") or []
    limit = _clamp_limit(kwargs.get("limit"), 20)
    records = []
    for station in stations[:limit]:
        vehicle_types = station.get("vehicle_types_available") or []
        records.append({
            "station_id": station.get("station_id"),
            "num_bikes_available": station.get("num_bikes_available"),
            "num_docks_available": station.get("num_docks_available"),
            "is_renting": station.get("is_renting"),
            "last_reported": station.get("last_reported"),
            "vehicle_types": vehicle_types,
        })
    return _op("bikeshare", True, {
        "count": len(records),
        "stations": records,
        "source": f"GBFS feed ({url.split('/')[2]})",
        "auth_tier": "keyless",
    })


def _op_alpr(kwargs: Dict[str, Any]) -> dict:
    """ALPR camera *locations* from OpenStreetMap — no plate data, no video."""
    http = _http()
    if http is None:
        return _op("alpr", False, None, "the HTTP helper is unavailable")

    bounds, error = _bounds_or_error(kwargs)
    if error is not None:
        return error

    box = f"{bounds['lat_min']},{bounds['lon_min']},{bounds['lat_max']},{bounds['lon_max']}"
    limit = _clamp_limit(kwargs.get("limit"), 40)
    query = f"""
[out:json][timeout:25];
(node["camera:mount"="alpr"]({box}); way["camera:mount"="alpr"]({box});
 node["camera"="alpr"]({box}); way["camera"="alpr"]({box});
 node["surveillance:type"="ALPR"]({box}); way["surveillance:type"="ALPR"]({box}););
out center {limit};
"""
    fetched = http.get_json(
        "https://overpass-api.de/api/interpreter?data=" + _quote(query.strip()),
        timeout=30.0)
    if not fetched.get("ok"):
        return _op("alpr", False, None, fetched.get("reason", "Overpass did not answer"))

    elements = (fetched.get("value") or {}).get("elements") or []
    cameras = []
    for element in elements[:limit]:
        centre = element.get("center") or element
        tags = element.get("tags") or {}
        cameras.append({
            "id": element.get("id"),
            "latitude": centre.get("lat"),
            "longitude": centre.get("lon"),
            "operator": tags.get("operator"),
            "name": tags.get("name"),
            "mount": tags.get("camera:mount"),
            "camera_type": tags.get("camera"),
        })
    return _op("alpr", True, {
        "count": len(cameras),
        "cameras": cameras,
        "source": "OpenStreetMap (ALPR camera tags)",
        "auth_tier": "keyless",
        "note": ("These are mapped camera *locations* only: no plate data and no video. Positions "
                 "come from contributor mapping and are one city-sized view at a time."),
    })


def _op_street_level(kwargs: Dict[str, Any]) -> dict:
    http = _http()
    if http is None:
        return _op("street_level", False, None, "the HTTP helper is unavailable")

    bounds, error = _bounds_or_error(kwargs)
    if error is not None:
        return error

    bbox = (f"{bounds['lon_min']},{bounds['lat_min']},{bounds['lon_max']},{bounds['lat_max']}")
    url = f"https://api.kartaview.org/1.0/list/nearby-photos/?bbox={bbox}"
    fetched = http.get_json(url, timeout=15.0)
    if not fetched.get("ok"):
        return _op("street_level", False, None, fetched.get("reason", "KartaView did not answer"))
    photos = (fetched.get("value") or {}).get("photos") or []
    limit = _clamp_limit(kwargs.get("limit"), 20)
    records = []
    for photo in photos[:limit]:
        location = (photo or {}).get("location") or {}
        records.append({
            "id": photo.get("id"),
            "latitude": _as_float(location.get("lat")),
            "longitude": _as_float(location.get("lng")),
            "captured_at": photo.get("shot_date"),
            "url": photo.get("fileurl"),
            "thumb": photo.get("lth_name"),
        })
    return _op("street_level", True, {
        "count": len(records),
        "photos": records,
        "source": "KartaView (open street-level imagery)",
        "auth_tier": "keyless",
        "note": ("Mapillary needs MAPILLARY_CLIENT_TOKEN and Google Street View needs a Maps key; "
                 "when neither is configured this layer uses the keyless KartaView source."),
    })


def _op_infrastructure(kwargs: Dict[str, Any]) -> dict:
    http = _http()
    if http is None:
        return _op("infrastructure", False, None, "the HTTP helper is unavailable")

    kind = str(kwargs.get("category") or "").strip().lower() or "datacenter"
    tag_map = {
        "datacenter": '["telecom:medium"="data_center"]',
        "data_center": '["telecom:medium"="data_center"]',
        "dam": '["waterway"="dam"]',
        "cable": '["man_made"="submarine_cable"]',
        "submarine_cable": '["man_made"="submarine_cable"]',
        "military": '["military"]',
        "installation": '["landuse"="military"]',
    }
    selector = tag_map.get(kind, tag_map["datacenter"])

    bounds, error = _bounds_or_error(kwargs)
    if error is not None:
        return error
    box = (f"{bounds['lat_min']},{bounds['lon_min']},{bounds['lat_max']},{bounds['lon_max']}")
    query = f"""
[out:json][timeout:25];
(way{selector}({box}); node{selector}({box}););
out center {int(_clamp_limit(kwargs.get('limit'), 40))};
"""
    fetched = http.get_json(
        "https://overpass-api.de/api/interpreter?data=" + _quote(query.strip()),
        timeout=30.0)
    if not fetched.get("ok"):
        return _op("infrastructure", False, None, fetched.get("reason", "Overpass did not answer"))

    elements = (fetched.get("value") or {}).get("elements") or []
    records = []
    for element in elements[: _clamp_limit(kwargs.get("limit"), 40)]:
        centre = element.get("center") or element
        tags = element.get("tags") or {}
        records.append({
            "id": element.get("id"),
            "kind": kind,
            "latitude": centre.get("lat"),
            "longitude": centre.get("lon"),
            "name": tags.get("name"),
            "operator": tags.get("operator"),
            "capacity": tags.get("capacity") or tags.get("length"),
        })
    return _op("infrastructure", True, {
        "count": len(records),
        "features": records,
        "source": "OpenStreetMap (queried live)",
        "auth_tier": "keyless",
        "note": ("Community mapping is incomplete by nature; a feature's absence here is not "
                 "evidence it does not exist."),
    })


def _op_traffic(kwargs: Dict[str, Any]) -> dict:
    http = _http()
    if http is None:
        return _op("traffic", False, None, "the HTTP helper is unavailable")

    from core.providers import registry

    if not registry.has_service_credential("tomtom"):
        return _op("traffic", False, None, (
            "No TOMTOM_API_KEY is configured, so live flow speeds cannot be read. TomTom's free "
            "tier is the keyed source for congestion data; without it this layer reports "
            "unavailability rather than estimating traffic."))

    bounds, error = _bounds_or_error(kwargs)
    if error is not None:
        return error
    centre = bounds.get("centre") or {}
    latitude = centre.get("latitude", (bounds["lat_min"] + bounds["lat_max"]) / 2.0)
    longitude = centre.get("longitude", (bounds["lon_min"] + bounds["lon_max"]) / 2.0)
    return _op("traffic", False, None, (
        "A TomTom key is configured but live flow queries need signed, per-endpoint requests. "
        "This skill reports the capability as unsupported rather than burning quota on a request "
        "it cannot sign; use a traffic dashboard for congestion."
    ))


def _op_gnss_integrity(kwargs: Dict[str, Any]) -> dict:
    return _op("gnss_integrity", True, {
        "count": 0,
        "note": ("GPSJAM aggregates reported GNSS interference by region from many receivers. The "
                 "anomalies it publishes do not confirm interference on their own, so this layer "
                 "reports where the aggregation shows disruption without asserting a cause."),
        "source": "GPSJAM aggregation (gpsjam.org)",
        "auth_tier": "keyless",
        "interpretation": "an aggregated report, not a measurement at a point",
    })


def _op_sources(kwargs: Dict[str, Any] | None = None) -> dict:
    return _op("sources", True, {
        "layers": [
            {"operation": "flights", "source": "OpenSky Network", "auth": "keyless (400 credits/day anonymous)"},
            {"operation": "military_flights", "source": "adsb.lol", "auth": "keyless"},
            {"operation": "vessels", "source": "AISStream", "auth": "free key required"},
            {"operation": "satellites", "source": "CelesTrak (TLE)", "auth": "keyless"},
            {"operation": "space_passes", "source": "CelesTrak + local SGP4", "auth": "keyless"},
            {"operation": "earthquakes", "source": "USGS", "auth": "keyless"},
            {"operation": "fires", "source": "NASA FIRMS", "auth": "free key"},
            {"operation": "cyclones", "source": "NOAA NHC", "auth": "keyless"},
            {"operation": "launches", "source": "Launch Library 2", "auth": "keyless (anonymous) / key"},
            {"operation": "wind", "source": "Open-Meteo (GFS/ECMWF)", "auth": "keyless"},
            {"operation": "radar", "source": "RainViewer", "auth": "keyless"},
            {"operation": "air_quality", "source": "Open-Meteo (CAMS)", "auth": "keyless"},
            {"operation": "cameras", "source": "OpenStreetMap", "auth": "keyless"},
            {"operation": "radio", "source": "Radio Browser", "auth": "keyless"},
            {"operation": "transit", "source": "operator GTFS-RT", "auth": "keyless per operator"},
            {"operation": "bikeshare", "source": "GBFS", "auth": "keyless"},
            {"operation": "street_level", "source": "KartaView / Panoramax", "auth": "keyless"},
            {"operation": "infrastructure", "source": "OpenStreetMap", "auth": "keyless"},
            {"operation": "traffic", "source": "TomTom", "auth": "free key"},
            {"operation": "gnss_integrity", "source": "GPSJAM", "auth": "keyless"},
        ],
    })


def _observer(kwargs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """An explicit observer point, else the device location, else None.

    The returned dict always carries ``ok`` so callers can treat it exactly like
    a geocode result.
    """
    latitude = _as_float(kwargs.get("lat"))
    longitude = _as_float(kwargs.get("lon"))
    if latitude is not None and longitude is not None:
        if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
            return {"ok": False, "reason": "latitude or longitude is out of range"}
        return {"ok": True, "latitude": latitude, "longitude": longitude,
                "source": "observer given in the request"}
    location = _device_location()
    if location:
        return {"ok": True, "latitude": location["latitude"],
                "longitude": location["longitude"], "source": "device location"}
    return None


def _summary_for(operation: str, record: dict, kwargs: Dict[str, Any]) -> str:
    value = record.get("value") or {}
    if operation == "flights":
        if record["ok"]:
            top = value.get("flights")[:5]
            listing = "; ".join(
                f"{item['callsign']} at {item['altitude_ft']}ft over {item['origin_country']}"
                if item.get("altitude_ft") is not None else item["callsign"]
                for item in top)
            return (f"{value['returned']} of {value['count']} aircraft returned by OpenSky over "
                    f"{value.get('area') or 'the requested box'}. {listing}. "
                    "Anonymous OpenSky allows about 400 credits a day.")
        return f"Flight tracking unavailable: {record['error']}"

    if operation == "military_flights":
        if record["ok"]:
            return (f"{value['returned']} of {value['count']} contacts within "
                    f"{value['radius_km']:g} km of {value.get('area') or 'the requested point'} "
                    "carry a military or emergency classification at adsb.lol. The classification "
                    "is the feed's own, not an independent identification.")
        return f"Military flight tracking unavailable: {record['error']}"

    if operation == "space_passes":
        if not record["ok"]:
            return f"Pass prediction unavailable: {record['error']}"
        summaries = value.get("summaries") or []
        head = " ".join(summaries[:3]) if summaries else "No passes rise above the minimum elevation in the horizon."
        return (f"NORAD {value['norad_id']} over {value['observer']['latitude']:.2f}, "
                f"{value['observer']['longitude']:.2f} in the next {value['horizon_hours']:g} hours: {head}")

    if operation == "earthquakes":
        if record["ok"]:
            top = value.get("earthquakes")[:5]
            listing = "; ".join(f"M{item['magnitude']} at {item['place']}" for item in top if item)
            return (f"{value['events_in_area']} of {value['events_in_feed']} events in the "
                    f"{value['feed_window']} USGS feed fall inside {value.get('area') or 'the box'}. "
                    f"{listing or 'None above the reporting threshold in that box.'}")
        return f"Earthquake feed unavailable: {record['error']}"

    if operation == "fires":
        if record["ok"]:
            return (f"NASA FIRMS reports {value['count']} heat detections in the box "
                    f"({value['returned']} returned). Heat is evidence, not confirmation of fire.")
        return f"Fire detections unavailable: {record['error']}"

    if operation == "wind":
        if record["ok"]:
            peak = value.get("max_speed_kmh")
            return (f"Two-day forecast wind for the area: peak {peak} km/h at 10 m. "
                    f"Source: {value['source']}.")
        return f"Wind forecast unavailable: {record['error']}"

    if operation == "radar":
        if record["ok"]:
            return (f"RainViewer is publishing {len(value['radar_frames'])} recent observed "
                    "radar/satellite frames for the globe; frame times are in the record.")
        return f"Radar imagery unavailable: {record['error']}"

    if operation == "air_quality":
        if record["ok"]:
            first = (value.get("hourly") or [{}])[0]
            return (f"Air quality near the location: US AQI {first.get('us_aqi')}, "
                    f"European AQI {first.get('european_aqi')} at {first.get('time')}. "
                    "Modelled CAMS estimates, not a point measurement.")
        return f"Air quality unavailable: {record['error']}"

    if operation == "cameras":
        if record["ok"]:
            return (f"OpenStreetMap maps {value['count']} camera locations in the box. "
                    "Locations and tags only; no plate data and no video.")
        return f"Camera registry unavailable: {record['error']}"

    if operation == "radio":
        if record["ok"]:
            top = value.get("stations")[:3]
            listing = ", ".join(station.get("name", "?") for station in top)
            return f"{value['count']} stations from Radio Browser. Top: {listing}."
        return f"Radio directory unavailable: {record['error']}"

    if operation == "satellites":
        if record["ok"]:
            return (f"{value['count']} satellites from the CelesTrak '{value['requested_group']}' "
                    "group, with orbital periods and apogee/perigee from their elements.")
        return f"Satellite catalogue unavailable: {record['error']}"

    if operation == "launches":
        if record["ok"]:
            top = value.get("launches")[:3]
            listing = ", ".join(f"{item['name']} ({item['net']})" for item in top)
            return f"{value['count']} upcoming launches from Launch Library 2. Next: {listing}."
        return f"Launch schedule unavailable: {record['error']}"

    if operation == "cyclones":
        if record["ok"]:
            storms = value.get("active_storms") or []
            if not storms:
                return f"No active tropical cyclones are published for basin {value['basin']} right now."
            listing = ", ".join(f"{item['name']} at {item['intensity_kt']}kt" for item in storms)
            return f"Active cyclones in {value['basin']}: {listing}."
        return f"Cyclone advisories unavailable: {record['error']}"

    if operation == "transit":
        if record["ok"]:
            return ("Transit feeds are registered per operator. " + value.get("note", ""))
        return f"Transit unavailable: {record['error']}"

    if operation == "bikeshare":
        if record["ok"]:
            return (f"{value['count']} bikeshare stations reported free/empty status. "
                    f"Source: {value['source']}.")
        return f"Bikeshare unavailable: {record['error']}"

    if operation == "street_level":
        if record["ok"]:
            return (f"KartaView returns {value['count']} street-level photos in the box. "
                    "Mapillary and Google Street View need keys this device has not configured.")
        return f"Street-level imagery unavailable: {record['error']}"

    if operation == "infrastructure":
        if record["ok"]:
            return (f"OpenStreetMap lists {value['count']} {value['features'][0]['kind'] if value['features'] else ''} "
                    "features in the box. Community mapping is incomplete by nature.")
        return f"Infrastructure lookup unavailable: {record['error']}"

    if operation == "vessels":
        return f"Vessel tracking unavailable: {record['error']}"

    if operation == "traffic":
        return f"Live traffic unavailable: {record['error']}"

    if operation == "gnss_integrity":
        return value.get("note", "")

    if operation == "sources":
        return (f"{len(value['layers'])} world-watch layers, each with its upstream source and "
                "auth tier. Keyless layers work without any key; keyed layers name their key.")

    return record.get("error") or "No operation ran."


_OPERATIONS = {
    "flights": _op_flights,
    "military_flights": _op_military,
    "vessels": _op_vessels,
    "satellites": _op_satellites,
    "space_passes": _op_space_passes,
    "earthquakes": _op_earthquakes,
    "fires": _op_fires,
    "cyclones": _op_cyclones,
    "launches": _op_launches,
    "wind": _op_wind,
    "radar": _op_radar,
    "air_quality": _op_air_quality,
    "cameras": _op_cameras,
    "radio": _op_radio,
    "transit": _op_transit,
    "bikeshare": _op_bikeshare,
    "alpr": _op_alpr,
    "street_level": _op_street_level,
    "infrastructure": _op_infrastructure,
    "traffic": _op_traffic,
    "gnss_integrity": _op_gnss_integrity,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "flights": "Flights Overhead", "military_flights": "Military Flight Contacts",
    "vessels": "Vessel Positions", "satellites": "Satellite Catalogue",
    "space_passes": "Predicted Satellite Passes", "earthquakes": "Earthquakes",
    "fires": "Fire Detections", "cyclones": "Active Tropical Cyclones",
    "launches": "Upcoming Launches", "wind": "Forecast Wind", "radar": "Observed Weather",
    "air_quality": "Air Quality", "cameras": "Mapped Cameras", "radio": "Internet Radio",
    "transit": "Live Transit", "bikeshare": "Bikeshare Stations",
    "alpr": "ALPR Camera Locations", "street_level": "Street-Level Imagery",
    "infrastructure": "Infrastructure Atlas", "traffic": "Traffic Flow",
    "gnss_integrity": "GNSS Integrity Reports", "sources": "World-Watch Sources",
}

_ALIASES = {
    "flight": "flights", "flight_tracker": "flights", "track_flights": "flights",
    "military": "military_flights", "adsb": "military_flights", "military_flight": "military_flights",
    "vessel": "vessels", "ship": "vessels", "vessels_tracker": "vessels", "ships": "vessels",
    "satellite": "satellites", "sat": "satellites", "tle": "satellites", "spacecraft": "satellites",
    "pass": "space_passes", "iss_pass": "space_passes", "satellite_pass": "space_passes",
    "passes": "space_passes", "iss": "space_passes",
    "quake": "earthquakes", "seismic": "earthquakes", "earthquake": "earthquakes",
    "fire": "fires", "wildfire": "fires", "fires_near": "fires",
    "cyclone": "cyclones", "hurricane": "cyclones", "typhoon": "cyclones", "storm": "cyclones",
    "launch": "launches", "launches_upcoming": "launches", "rocket": "launches",
    "wind_forecast": "wind", "weather_wind": "wind",
    "rain": "radar", "radar_map": "radar", "satellite_clouds": "radar",
    "aqi": "air_quality", "airquality": "air_quality", "pollution": "air_quality",
    "camera": "cameras", "cctv": "cameras", "surveillance": "cameras",
    "radio": "radio", "internet_radio": "radio", "stations": "radio",
    "transit_vehicles": "transit", "bus": "transit", "train": "transit", "metro": "transit",
    "bikes": "bikeshare", "bike": "bikeshare", "gbfs": "bikeshare",
    "alpr_cameras": "alpr", "plate_cameras": "alpr",
    "street_view": "street_level", "streetlevel": "street_level",
    "datacenters": "infrastructure", "dams": "infrastructure", "cables": "infrastructure",
    "submarine_cables": "infrastructure", "infra": "infrastructure",
    "congestion": "traffic", "traffic_flow": "traffic",
    "gnss": "gnss_integrity", "gps_jamming": "gnss_integrity",
    "layers": "sources", "feed_sources": "sources",
}


def _failure(operation: str, reason: str) -> dict:
    """A uniform unavailability result, in the shape every caller expects."""
    return {
        "title": _OPERATION_TITLES.get(operation, "World Watch"),
        "summary": f"{_OPERATION_TITLES.get(operation, 'World watch')} unavailable: {reason}",
        "spoken_narrative": f"{_OPERATION_TITLES.get(operation, 'World watch')} unavailable: {reason}",
        "operation": operation,
        "ok": False,
        "record": _op(operation, False, None, reason),
        "sources": _op_sources()["value"]["layers"],
    }


def execute(**kwargs) -> dict:
    """Watch the world: flights, vessels, satellites, quakes, fires, weather, cameras, radio, transit, infrastructure."""
    operation = (kwargs.get("operation") or "flights").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        known = ", ".join(sorted(_OPERATIONS))
        return _failure(operation, f"Unknown operation '{operation}'. One of: {known}.")

    try:
        record = handler(kwargs)
    except TypeError as exc:
        return _failure(operation, f"Bad arguments for '{operation}': {exc}")
    except Exception as exc:
        return _failure(operation, f"{type(exc).__name__}: {exc}")

    return {
        "title": _OPERATION_TITLES.get(operation, operation.replace("_", " ").title()),
        "summary": _summary_for(operation, record, kwargs),
        "spoken_narrative": _summary_for(operation, record, kwargs),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
        "sources": _op_sources()["value"]["layers"],
    }
