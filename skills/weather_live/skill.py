from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional

FEATURE_METADATA = {
    "name": "weather_live",
    "aliases": [
        "weather_live", "live weather", "weather", "weather forecast",
        "current weather", "hourly forecast", "daily forecast", "air quality",
        "weather alert", "weather conditions", "temperature", "humidity",
    ],
    "description": (
        "Live weather and forecasts for any location worldwide using Open-Meteo's "
        "free public API (no API key required). Provides current conditions, "
        "hourly forecasts, daily forecasts, air quality, sunrise/sunset, and "
        "weather codes. Geocoding via OpenStreetMap Nominatim (also keyless) "
        "resolves place names to coordinates."
    ),
    "triggers": [
        "weather", "weather in", "weather for", "temperature", "forecast",
        "hourly forecast", "daily forecast", "air quality", "sunrise", "sunset",
        "is it raining", "is it sunny", "current temperature", "live weather",
        "weather alert", "weather conditions",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: current | forecast | daily | air_quality | sun | sources. Defaults to current.",
            },
            "location": {
                "type": "STRING",
                "description": "Place name (city, town, address) or 'here' for device location.",
            },
            "latitude": {
                "type": "NUMBER",
                "description": "Latitude coordinate (used directly if location is not given).",
            },
            "longitude": {
                "type": "NUMBER",
                "description": "Longitude coordinate (used directly if location is not given).",
            },
            "hours": {
                "type": "INTEGER",
                "description": "Number of hourly forecast hours (default 24, max 168).",
            },
            "days": {
                "type": "INTEGER",
                "description": "Number of daily forecast days (default 7, max 16).",
            },
        },
        "required": [],
    },
    "version": "2.0.0",
    "active": True,
    "optional_dependencies": [],
}

API_SOURCES = {
    "open_meteo": {
        "name": "Open-Meteo",
        "description": "Free global weather forecast and API (no key required)",
        "url": "https://open-meteo.com/",
        "docs": "https://open-meteo.com/en/docs",
        "auth_tier": "keyless",
        "rate_limit": "1 request per second",
        "uses": ["current", "forecast", "daily", "air_quality", "sun"],
    },
    "nominatim": {
        "name": "OpenStreetMap Nominatim",
        "description": "Free geocoding service to resolve place names to coordinates",
        "url": "https://nominatim.org/",
        "docs": "https://operations.osmfoundation.org/policies/nominatim/",
        "auth_tier": "keyless",
        "rate_limit": "1 request per second",
        "uses": ["geocoding"],
    },
}

_RATE_LIMIT = 1.0
_last_nominatim_call = 0.0

def _throttle_nominatim() -> None:
    global _last_nominatim_call
    elapsed = time.time() - _last_nominatim_call
    if elapsed < _RATE_LIMIT:
        time.sleep(_RATE_LIMIT - elapsed)
    _last_nominatim_call = time.time()

def _http_get_json(url: str, timeout: int = 15) -> Optional[Dict[str, Any]]:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Stella-AI/1.0 (https://github.com/Emma-Keaton/stella)",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

def _geocode(location: str) -> Optional[Dict[str, Any]]:
    _throttle_nominatim()
    encoded = urllib.parse.quote(location)
    url = (
        f"https://nominatim.openstreetmap.org/search?"
        f"q={encoded}&format=json&limit=1&addressdetails=1"
    )
    data = _http_get_json(url, timeout=15)
    if not data or not isinstance(data, list) or len(data) == 0:
        return None
    entry = data[0]
    return {
        "lat": float(entry.get("lat", 0)),
        "lon": float(entry.get("lon", 0)),
        "display_name": entry.get("display_name", location),
        "type": entry.get("type", ""),
        "country": entry.get("address", {}).get("country", ""),
    }

def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}

def _resolve_location(kwargs: dict) -> Optional[Dict[str, Any]]:
    lat = kwargs.get("latitude")
    lon = kwargs.get("longitude")
    if lat is not None and lon is not None:
        return {
            "lat": float(lat),
            "lon": float(lon),
            "display_name": kwargs.get("location", f"{lat}, {lon}"),
            "type": "coordinates",
        }
    location = kwargs.get("location") or kwargs.get("place") or kwargs.get("city") or ""
    if not location:
        return None
    return _geocode(location.strip())
def _format_weather_code(code: int) -> str:
    codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow fall",
        73: "Moderate snow fall",
        75: "Heavy snow fall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return codes.get(code, f"Weather code {code}")

def _op_current(kwargs: dict) -> dict:
    loc = _resolve_location(kwargs)
    if loc is None:
        return _op("current", False, None, "No location provided. Give a place name or lat/lon.")
    data = _http_get_json(
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={loc['lat']}&longitude={loc['lon']}"
        f"&current_weather=true&hourly=temperature_2m,relativehumidity_2m,"
        f"apparent_temperature,precipitation,weathercode,windspeed_10m,"
        f"winddirection_10m&timezone=auto"
    )
    if not data:
        return _op("current", False, None, "Open-Meteo did not return current weather.")
    cur = data.get("current_weather", {})
    hourly = data.get("hourly", {})
    time_index = 0
    if hourly.get("time"):
        try:
            time_index = hourly["time"].index(cur.get("time", ""))
        except ValueError:
            time_index = 0
    humidity = None
    precip = None
    app_temp = None
    if hourly.get("relativehumidity_2m") and time_index < len(hourly["relativehumidity_2m"]):
        humidity = hourly["relativehumidity_2m"][time_index]
    if hourly.get("precipitation") and time_index < len(hourly["precipitation"]):
        precip = hourly["precipitation"][time_index]
    if hourly.get("apparent_temperature") and time_index < len(hourly["apparent_temperature"]):
        app_temp = hourly["apparent_temperature"][time_index]
    weather_code = cur.get("weathercode")
    content_lines = [
        f"Current weather for {loc['display_name']}:",
        f"  Temperature: {cur.get('temperature')}Â°C",
        f"  Feels like: {app_temp}Â°C" if app_temp is not None else "",
        f"  Condition: {_format_weather_code(weather_code)}",
        f"  Wind: {cur.get('windspeed_10m')} km/h from {cur.get('winddirection_10m')}Â°",
        f"  Humidity: {humidity}%" if humidity is not None else "",
        f"  Precipitation: {precip} mm" if precip is not None else "",
        "  Source: Open-Meteo (keyless)",
    ]
    content = "\n".join(l for l in content_lines if l)
    return _op("current", True, {
        "location": loc,
        "temperature": cur.get("temperature"),
        "apparent_temperature": app_temp,
        "condition": _format_weather_code(weather_code),
        "weather_code": weather_code,
        "wind_speed_kmh": cur.get("windspeed_10m"),
        "wind_direction_deg": cur.get("winddirection_10m"),
        "humidity": humidity,
        "precipitation_mm": precip,
        "time": cur.get("time"),
        "content": content
    })

def _op_forecast(kwargs: dict) -> dict:
    loc = _resolve_location(kwargs)
    if loc is None:
        return _op("forecast", False, None, "No location provided.")
    hours = int(kwargs.get("hours") or 24)
    hours = max(1, min(hours, 168))
    data = _http_get_json(
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={loc['lat']}&longitude={loc['lon']}"
        f"&hourly=temperature_2m,relativehumidity_2m,weathercode,"
        f"windspeed_10m,precipitation_probability&timezone=auto"
    )
    if not data:
        return _op("forecast", False, None, "Open-Meteo did not return forecast data.")
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])[:hours]
    temps = hourly.get("temperature_2m", [])[:hours]
    humids = hourly.get("relativehumidity_2m", [])[:hours]
    codes = hourly.get("weathercode", [])[:hours]
    winds = hourly.get("windspeed_10m", [])[:hours]
    probs = hourly.get("precipitation_probability", [])[:hours]
    entries = []
    for i in range(len(times)):
        entries.append({
            "time": times[i] if i < len(times) else None,
            "temperature": temps[i] if i < len(temps) else None,
            "humidity": humids[i] if i < len(humids) else None,
            "condition": _format_weather_code(codes[i]) if i < len(codes) else None,
            "weather_code": codes[i] if i < len(codes) else None,
            "wind_speed_kmh": winds[i] if i < len(winds) else None,
            "precip_probability": probs[i] if i < len(probs) else None,
        })
    content_lines = [f"Hourly forecast for {loc['display_name']} (next {len(entries)} hours):"]
    for e in entries[:12]:
        content_lines.append(
            f"  {e['time']}: {e['temperature']}Â°C, {e['condition']}, "
            f"wind {e['wind_speed_kmh']} km/h, precip {e['precip_probability']}%"
        )
    content = "\n".join(content_lines)
    return _op("forecast", True, {
        "location": loc,
        "hours": hours,
        "entries": entries,
        "content": content,
    })

def _op_daily(kwargs: dict) -> dict:
    loc = _resolve_location(kwargs)
    if loc is None:
        return _op("daily", False, None, "No location provided.")
    days = int(kwargs.get("days") or 7)
    days = max(1, min(days, 16))
    data = _http_get_json(
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={loc['lat']}&longitude={loc['lon']}"
        f"&daily=weathercode,temperature_2m_max,temperature_2m_min,"
        f"precipitation_sum,windspeed_10m_max&timezone=auto"
    )
    if not data:
        return _op("daily", False, None, "Open-Meteo did not return daily forecast.")
    daily = data.get("daily", {})
    times = daily.get("time", [])[:days]
    maxes = daily.get("temperature_2m_max", [])[:days]
    mins = daily.get("temperature_2m_min", [])[:days]
    codes = daily.get("weathercode", [])[:days]
    precips = daily.get("precipitation_sum", [])[:days]
    winds = daily.get("windspeed_10m_max", [])[:days]
    entries = []
    for i in range(len(times)):
        entries.append({
            "date": times[i],
            "max_temp": maxes[i] if i < len(maxes) else None,
            "min_temp": mins[i] if i < len(mins) else None,
            "condition": _format_weather_code(codes[i]) if i < len(codes) else None,
            "weather_code": codes[i] if i < len(codes) else None,
            "precip_mm": precips[i] if i < len(precips) else None,
            "max_wind_kmh": winds[i] if i < len(winds) else None,
        })
    content_lines = [f"Daily forecast for {loc['display_name']} (next {len(entries)} days):"]
    for e in entries:
        content_lines.append(
            f"  {e['date']}: {e['min_temp']}Â°Câ€“{e['max_temp']}Â°C, "
            f"{e['condition']}, precip {e['precip_mm']} mm, wind {e['max_wind_kmh']} km/h"
        )
    content = "\n".join(content_lines)
    return _op("daily", True, {
        "location": loc,
        "days": days,
        "entries": entries,
        "content": content,
    })

def _op_air_quality(kwargs: dict) -> dict:
    loc = _resolve_location(kwargs)
    if loc is None:
        return _op("air_quality", False, None, "No location provided.")
    data = _http_get_json(
        f"https://air-quality-api.open-meteo.com/v1/air-quality?"
        f"latitude={loc['lat']}&longitude={loc['lon']}"
        f"&hourly=european_aqi,pm10,pm2_5,carbon_monoxide,"
        f"nitrogen_dioxide,sulphur_dioxide,ozone&timezone=auto"
    )
    if not data:
        return _op("air_quality", False, None, "Open-Meteo air-quality API did not respond.")
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    aqis = hourly.get("european_aqi", [])
    pms = hourly.get("pm2_5", [])
    index = 0
    if times and aqis:
        try:
            index = len(aqis) - 1
        except Exception:
            index = 0
    aqi = aqis[index] if index < len(aqis) else None
    pm25 = pms[index] if index < len(pms) else None
    aqi_label = (
        "Good" if (aqi or 0) <= 20 else
        "Fair" if (aqi or 0) <= 40 else
        "Moderate" if (aqi or 0) <= 60 else
        "Poor" if (aqi or 0) <= 80 else
        "Very Poor" if (aqi or 0) <= 100 else "Extremely Poor"
    )
    content = (
        f"Air quality for {loc['display_name']}: "
        f"European AQI {aqi} ({aqi_label}), PM2.5 {pm25} Âµg/mÂ³. "
        f"Source: Open-Meteo Air Quality (keyless)."
    )
    return _op("air_quality", True, {
        "location": loc,
        "aqi": aqi,
        "aqi_label": aqi_label,
        "pm2_5": pm25,
        "content": content,
    })

def _op_sun(kwargs: dict) -> dict:
    loc = _resolve_location(kwargs)
    if loc is None:
        return _op("sun", False, None, "No location provided.")
    data = _http_get_json(
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={loc['lat']}&longitude={loc['lon']}"
        f"&daily=sunrise,sunset&timezone=auto"
    )
    if not data:
        return _op("sun", False, None, "Open-Meteo did not return sun data.")
    daily = data.get("daily", {})
    sunrises = daily.get("sunrise", [])
    sunsets = daily.get("sunset", [])
    content = (
        f"Sun for {loc['display_name']}: "
        f"sunrise {sunrises[0] if sunrises else 'N/A'}, "
        f"sunset {sunsets[0] if sunsets else 'N/A'}. "
        f"Source: Open-Meteo (keyless)."
    )
    return _op("sun", True, {
        "location": loc,
        "sunrise": sunrises[0] if sunrises else None,
        "sunset": sunsets[0] if sunsets else None,
        "content": content,
    })

def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "source": "weather_live (Stella live weather skill)",
        "dependencies": [],
        "operations": ["current", "forecast", "daily", "air_quality", "sun", "sources"],
        "apis": API_SOURCES,
        "note": "Live weather via Open-Meteo (keyless) with OpenStreetMap Nominatim "
                "geocoding (keyless). All operations run locally, no API key required.",
    })

_OPERATIONS = {
    "sources": _op_sources,
    "current": _op_current,
    "forecast": _op_forecast,
    "daily": _op_daily,
    "air_quality": _op_air_quality,
    "sun": _op_sun,
}

_OPERATION_TITLES = {
    "sources": "Weather Sources",
    "current": "Current Weather",
    "forecast": "Hourly Forecast",
    "daily": "Daily Forecast",
    "air_quality": "Air Quality",
    "sun": "Sunrise/Sunset",
}

def execute(**kwargs) -> dict:
    """Run one weather_live operation."""
    operation = (kwargs.get("operation") or "current").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Weather Live",
            "summary": f"Unknown operation '{operation}'. One of: "
                       f"{chr(39).join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown weather operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Weather Live",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Weather Live",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Weather error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Weather Live"),
        "summary": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "spoken_narrative": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }
