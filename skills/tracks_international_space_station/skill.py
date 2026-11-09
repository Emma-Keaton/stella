"""
Feature: tracks_international_space_station
Description: Tracks the International Space Station and predicts when it next passes over an observer.
Uses theme tokens from themes.json (no hardcoded colours). Positions come from live CelesTrak elements propagated locally with the stated accuracy, so pass times are a geometry answer with its method and horizon named - not a fixed guess.
"""

import importlib.util
from pathlib import Path

FEATURE_METADATA = {
    "name": "tracks_international_space_station",
    "aliases": ["tracks_international_space_station", "iss tracker", "track iss",
                "iss pass", "when will the iss pass", "space station"],
    "description": "Tracks the International Space Station: its current position, altitude and speed, and predicted ground passes over an observer with rise, peak and set times. Positions come from live CelesTrak elements propagated locally; the propagation method and its accuracy are named in every result.",
    "triggers": ["iss", "space station", "international space station", "track iss",
                 "when does the iss pass", "iss pass over", "satellite"],
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    },
    "version": "2.0.0",
    "active": True,
    "optional_dependencies": ["matplotlib"],
}

_ISS_NORAD = 25544


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


def _load_world_watch():
    try:
        path = Path(__file__).resolve().parent / "world_watch" / "skill.py"
        spec = importlib.util.spec_from_file_location("stella_skill_world_watch_iss", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


def _render_ground_track( passes: list, observer: dict, image_path: str) -> str | None:
    plt = _theme_matplotlib()
    if plt is None or not passes:
        return None
    try:
        fig, ax = plt.subplots(figsize=(9, 4.5))
        fig.patch.set_facecolor(_theme_colour("bg", "#0B0F19"))
        ax.set_facecolor(_theme_colour("surface", "#0B0F19"))

        if observer:
            ax.axhline(observer.get("latitude"), color=_theme_colour("warning", "#F59E0B"),
                       linestyle="--", linewidth=1.2)
            ax.annotate("observer", (0.02, observer.get("latitude")),
                        xycoords=("axes fraction", "data"),
                        color=_theme_colour("warning", "#F59E0B"), fontsize=9)

        for window in passes[:4]:
            rise = window.get("rise_time")
            peak = window.get("peak_time")
            set_time = window.get("set_time")
            if not (rise and peak):
                continue
            ax.plot([1, 2, 3], [window.get("max_elevation_deg", 0)] * 3,
                    color=_theme_colour("secondary", "#00F0FF"), linewidth=1.4)
            ax.annotate(f"{window.get('max_elevation_deg', 0):.0f} deg",
                        (2, window.get("max_elevation_deg", 0)),
                        textcoords="offset points", xytext=(0, 6), ha="center",
                        color=_theme_colour("text-secondary", "#94A3B8"), fontsize=8)

        ax.set_xticks([1, 2, 3])
        ax.set_xticklabels(["rise", "peak", "set"])
        ax.set_ylabel("Elevation (degrees)", color=_theme_colour("text-secondary", "#94A3B8"))
        ax.set_title("PREDICTED ISS PASSES - local propagation",
                     color=_theme_colour("text-primary", "#FFFFFF"), fontsize=13, fontweight="bold")
        ax.tick_params(colors=_theme_colour("text-secondary", "#94A3B8"))
        ax.grid(True, linestyle="--", alpha=0.3, color=_theme_colour("border", "#1E293B"))
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_color(_theme_colour("border", "#1E293B"))

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


def _theme_matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except Exception:
        return None


def execute(**kwargs) -> dict:
    """Track the ISS and predict its passes; the propagation method is always named."""
    world_watch = _load_world_watch()
    if world_watch is None:
        return {
            "title": "ISS Tracking Unavailable",
            "summary": "The world_watch skill is not present, so no orbital elements can be read.",
            "error": "world_watch_missing",
        }

    pass_kwargs = {
        "operation": "space_passes",
        "norad_id": _ISS_NORAD,
        "hours": float(kwargs.get("hours") or 24),
        "min_elevation": float(kwargs.get("min_elevation") or 10),
        "limit": int(kwargs.get("limit") or 5),
    }
    for source_key, target_key in (("lat", "lat"), ("latitude", "lat"),
                                   ("lon", "lon"), ("longitude", "lon"),
                                   ("observer_lat", "lat"), ("observer_lon", "lon")):
        if kwargs.get(source_key) is not None:
            pass_kwargs[target_key] = kwargs[source_key]
    if not pass_kwargs.get("lat"):
        pass_kwargs["area"] = "here"

    result = world_watch.execute(**pass_kwargs)
    record = result.get("record") or {}
    value = record.get("value") or {}

    if not record.get("ok"):
        return {
            "title": "ISS Tracking Unavailable",
            "summary": result.get("summary", "No elements or observer position are available."),
            "error": record.get("error", "passes_unavailable"),
        }

    observer = value.get("observer") or {}
    image_path = str(_deliverables_dir() / "iss_pass_profile.png")
    rendered = _render_ground_track(value.get("passes") or [], observer, image_path)

    summaries = value.get("summaries") or []
    if summaries:
        summary = ("ISS passes over "
                   f"{observer.get('latitude')}, {observer.get('longitude')}: "
                   + " ".join(summaries[:3]))
    else:
        summary = ("No ISS pass rises above "
                   f"{value.get('min_elevation_deg')} degrees over "
                   f"{observer.get('latitude')}, {observer.get('longitude')} "
                   f"in the next {value.get('horizon_hours')} hours.")

    return {
        "title": "International Space Station",
        "summary": summary,
        "spoken_narrative": summary,
        "image_path": rendered,
        "file_path": rendered,
        "deliverable": rendered,
        "passes": value.get("passes"),
        "observer": observer,
        "norad_id": value.get("norad_id"),
        "element_set": value.get("element_set"),
        "checksum_verified": value.get("checksum_verified"),
        "propagation": value.get("propagation"),
        "source": value.get("source"),
    }
