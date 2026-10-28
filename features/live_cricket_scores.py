"""
Feature: live_cricket_scores
Description: Fetches and displays live international cricket scores and match scorecards from the ESPNCricinfo live-scores RSS feed.
Uses theme tokens from themes.json (no hardcoded colours). Reports an explicit unavailable result with the reason when the feed cannot be read, and never invents scores.
"""

FEATURE_METADATA = {
    "name": "live_cricket_scores",
    "description": "Fetches and displays live international cricket scores and match scorecards. Useful for checking the current status of ongoing international cricket matches. Colours come from the active theme in themes.json.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "match_id": {
                "type": "STRING",
                "description": "Optional: The unique identifier for a specific cricket match. If not provided, the skill will attempt to fetch live scores for all ongoing international matches.",
            },
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "optional_dependencies": ["matplotlib"],
}


def _theme_colour(key: str, fallback: str | None = None) -> str | None:
    """Read a colour from the active theme, with an optional fallback."""
    try:
        from theme_tokens import theme_colour
        return theme_colour(key) or fallback
    except Exception:
        return fallback


def _matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except Exception:
        return None


def _deliverables_dir():
    try:
        from core.user_paths import get_user_data_dir
        return get_user_data_dir() / "deliverables"
    except Exception:
        import os
        from pathlib import Path
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "StellaAI" / "deliverables"


def execute(**kwargs):
    """Fetches and displays live international cricket scores."""
    import urllib.request
    import xml.etree.ElementTree as ET
    from datetime import datetime

    query = (kwargs.get("query") or kwargs.get("match_id") or kwargs.get("team") or "").lower().strip()
    rss_url = "https://static.cricinfo.com/rss/livescores.xml"

    matches = []
    try:
        req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=8) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        for item in root.findall("./channel/item"):
            title = item.find("title")
            link = item.find("link")
            desc = item.find("description")
            t_text = title.text.strip() if title is not None and title.text else ""
            l_text = link.text.strip() if link is not None and link.text else ""
            d_text = desc.text.strip() if desc is not None and desc.text else ""
            if t_text:
                matches.append({
                    "title": t_text,
                    "link": l_text,
                    "description": d_text,
                })
    except Exception as e:
        return {
            "title": "Live Cricket Scores Unavailable",
            "summary": (
                "The ESPNCricinfo live-scores RSS feed could not be read, so no live scores can be "
                "shown right now. Reason: "
                f"{type(e).__name__}: {e}. No scores are reported when the feed cannot be read."
            ),
            "error": "score_feed_unavailable",
            "details": f"{type(e).__name__}: {e}",
        }

    if not matches:
        return {
            "title": "No Live Cricket Matches",
            "summary": (
                "The ESPNCricinfo live-scores feed was read successfully and lists no matches currently "
                "in progress."
            ),
            "matches": [],
        }

    if query:
        filtered = [m for m in matches if query in m["title"].lower()]
        if filtered:
            matches = filtered

    num_matches = len(matches)
    summary_lines = [m["title"] for m in matches[:6]]
    summary_text = "\n".join(f"\u2022 {line}" for line in summary_lines) if summary_lines else "No live cricket matches currently in progress."
    spoken_narrative = (
        f"Tracked {num_matches} live cricket matches from Cricinfo. Top match: {summary_lines[0]}."
        if summary_lines else "No live cricket matches in progress right now."
    )

    image_path = None
    plt = _matplotlib()
    if plt is not None:
        try:
            plt.style.use("dark_background")
            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor(_theme_colour("bg", "#0B0F19"))
            ax.set_facecolor(_theme_colour("surface", "#0B0F19"))

            primary_colour = _theme_colour("primary", "#00F0FF")
            warning_colour = _theme_colour("warning", "#F59E0B")
            success_colour = _theme_colour("success", "#10B981")
            text_colour = _theme_colour("text-primary", "#FFFFFF")
            muted_colour = _theme_colour("text-secondary", "#94A3B8")
            border_colour = _theme_colour("border", "#1E293B")

            ax.text(0.05, 0.92, "LIVE CRICKET RADAR & SCORECARDS", color=primary_colour, fontsize=15, fontweight="bold")
            ax.text(
                0.05, 0.85,
                f"Source: ESPNCricinfo Live Stream | Updated: {datetime.now().strftime('%H:%M:%S')}",
                color=muted_colour, fontsize=9,
            )

            y_pos = 0.74
            for idx, m in enumerate(matches[:5]):
                ax.text(0.05, y_pos, f"MATCH {idx+1}", color=warning_colour, fontsize=10, fontweight="bold")
                ax.text(0.05, y_pos - 0.05, m["title"], color=text_colour, fontsize=11, fontweight="semibold")
                if m.get("description") and m["description"] != m["title"]:
                    ax.text(0.05, y_pos - 0.10, m["description"][:85], color=success_colour, fontsize=9)
                    y_pos -= 0.17
                else:
                    y_pos -= 0.13

            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_color(border_colour)

            output_dir = _deliverables_dir()
            output_dir.mkdir(parents=True, exist_ok=True)
            image_path = str(output_dir / "cricket_scores_output.png")
            plt.savefig(image_path, bbox_inches="tight", dpi=140)
            plt.close(fig)
        except Exception:
            try:
                plt.close("all")
            except Exception:
                pass

    return {
        "title": "Live International Cricket Scores",
        "summary": summary_text,
        "spoken_narrative": spoken_narrative,
        "matches": matches[:10],
        "image_path": image_path,
    }
