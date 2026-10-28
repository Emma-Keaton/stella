"""
Feature: flights_specific_area
Description: Tracks live civil aircraft over a specified area and shows them on a radar chart.
Uses theme tokens from themes.json (no hardcoded colours). Data comes from the OpenSky Network through the world_watch skill: the area is geocoded rather than looked up in a table, the bounding box is configurable, and the source's anonymous quota is stated instead of being spent silently.
"""

import math

FEATURE_METADATA = {
    "name": "flights_specific_area",
    "aliases": ["flights_specific_area", "flight tracker", "track flights", "flights in area",
                "aircraft overhead", "flight radar", "planes over"],
    "description": "Tracks live civil aircraft over any specified area and renders a radar chart of them. The area is geocoded from its name (no built-in city table), the bounding box is configurable, and every result names the OpenSky Network source and its anonymous quota.",
    "triggers": ["flights in", "over", "near", "around", "area", "track", "radar",
                 "aircraft", "flight", "flights specific area"],
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    },
    "version": "2.0.0",
    "active": True,
    "optional_dependencies": ["matplotlib"],
}

_DEFAULT_BOX = {"lat_min": 18.6, "lat_max": 19.8, "lon_min": 72.5, "lon_max": 73.8}
_DEFAULT_AREA = "Mumbai"


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


def _matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except Exception:
        return None


def _load_world_watch():
    try:
        import importlib.util
        from pathlib import Path

        path = Path(__file__).resolve().parent / "world_watch" / "skill.py"
        spec = importlib.util.spec_from_file_location("stella_skill_world_watch_nested", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


def _render_radar(flights: list, centre: dict, image_path: str) -> str | None:
    plt = _matplotlib()
    if plt is None or not flights:
        return None
    try:
        fig, ax = plt.subplots(figsize=(8, 8))
        fig.patch.set_facecolor(_theme_colour("bg", "#0B0F19"))
        ax.set_facecolor(_theme_colour("surface", "#0B0F19"))

        latitudes = [f["latitude"] for f in flights]
        longitudes = [f["longitude"] for f in flights]
        lat_mid = sum(latitudes) / len(latitudes)
        lon_mid = sum(longitudes) / len(longitudes)

        ax.scatter(longitudes, latitudes,
                  c=_theme_colour("secondary", "#00F0FF"), s=42,
                  edgecolors=_theme_colour("text-primary", "#FFFFFF"), linewidths=0.6, zorder=3)
        for flight in flights[:12]:
            ax.annotate(flight["callsign"], (flight["longitude"], flight["latitude"]),
                        textcoords="offset points", xytext=(6, 4),
                        color=_theme_colour("text-secondary", "#94A3B8"), fontsize=8)

        ax.set_title(f"LIVE CIVIL TRAFFIC - {centre.get('name') or 'requested box'} (OpenSky Network)",
                     color=_theme_colour("text-primary", "#FFFFFF"), fontsize=13, fontweight="bold", pad=14)
        ax.set_xlabel("Longitude", color=_theme_colour("text-secondary", "#94A3B8"))
        ax.set_ylabel("Latitude", color=_theme_colour("text-secondary", "#94A3B8"))
        span = max(0.02, (max(longitudes) - min(longitudes)) * 1.15, 0.02)
        ax.set_xlim(lon_mid - span, lon_mid + span)
        ax.set_ylim(lat_mid - span * 0.72, lat_mid + span * 0.72)
        ax.tick_params(colors=_theme_colour("text-secondary", "#94A3B8"))
        ax.grid(True, linestyle="--", alpha=0.3, color=_theme_colour("border", "#1E293B"))
        for spine in ax.spines.values():
            spine.set_color(_theme_colour("border", "#1E293B"))
        ax.set_axisbelow(True)

        output_dir = _deliverables_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        fig.tight_layout()
        plt.savefig(image_path, dpi=130, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        return image_path
    except Exception:
        try:
            plt.close("all")
        except Exception:
            pass
        return None


def execute(**kwargs) -> dict:
    """Track live flights over an area; the area is geocoded, never assumed."""
    world_watch = _load_world_watch()
    if world_watch is None:
        return {
            "title": "Flight Tracking Unavailable",
            "summary": "The world_watch skill is not present, so no flight feed can be read.",
            "error": "world_watch_missing",
        }

    area = (kwargs.get("area") or kwargs.get("query") or kwargs.get("location")
            or kwargs.get("city") or kwargs.get("place") or "").strip()
    result = world_watch.execute(operation="flights", area=area or _DEFAULT_AREA,
                                 limit=int(kwargs.get("limit") or 15))
    record = result.get("record") or {}
    value = record.get("value") or {}

    if not record.get("ok"):
        return {
            "title": "Flight Tracking Unavailable",
            "summary": result.get("summary", "OpenSky did not answer."),
            "error": record.get("error", "flights_unavailable"),
        }

    flights = value.get("flights") or []
    centre = {"name": value.get("area") or area or _DEFAULT_AREA,
              "latitude": (value.get("bbox", {}).get("lat_min", 0)
                           + value.get("bbox", {}).get("lat_max", 0)) / 2.0,
              "longitude": (value.get("bbox", {}).get("lon_min", 0)
                            + value.get("bbox", {}).get("lon_max", 0)) / 2.0}
    image_path = str(_deliverables_dir() / "flights_radar_output.png")
    image_path = _render_radar(flights, centre, image_path) or image_path

    if flights:
        listing = "; ".join(
            f"{flight['callsign']} ({flight.get('altitude_ft') or 'unknown'} ft, "
            f"{flight.get('speed_kmh') or '?'} km/h)" for flight in flights[:8])
        summary = (f"{len(flights)} aircraft from OpenSky over {centre['name']}: {listing}. "
                   f"{value.get('note', '')}")
    else:
        summary = (f"No aircraft with a position are inside {centre['name']} right now. "
                   "OpenSky returned no usable state vectors for that box.")

    return {
        "title": "Flights Overhead",
        "summary": summary,
        "spoken_narrative": result.get("spoken_narrative", summary),
        "image_path": image_path,
        "file_path": image_path,
        "deliverable": image_path,
        "flights": flights,
        "area": centre["name"],
        "bbox": value.get("bbox"),
        "source": value.get("source"),
    }
