"""
Feature: Spotify MCP Controller
Description: High-fidelity Spotify playback, search, queue, and playlist manager powered by Spotify MCP Server.
Uses theme tokens from themes.json (no hardcoded colours). Gracefully degrades when the Spotify MCP server is not configured.
"""

FEATURE_METADATA = {
    "name": "spotify_mcp",
    "aliases": ["spotify", "spotify_player", "spotify_controller", "spotify_music"],
    "description": (
        "Controls official Spotify playback, searches songs/artists/albums, manages queue, "
        "adjusts volume, and checks now-playing status via Spotify MCP Server. "
        "Reports unavailability when Spotify is not configured."
    ),
    "triggers": [
        "play on spotify",
        "play music on spotify",
        "play song on spotify",
        "play track on spotify",
        "pause spotify",
        "resume spotify",
        "skip song on spotify",
        "next song on spotify",
        "previous song on spotify",
        "spotify volume",
        "what song is playing",
        "what is playing on spotify",
        "now playing on spotify",
        "spotify playlists",
        "my spotify playlists",
        "spotify queue",
        "spotify devices",
        "authenticate spotify",
        "connect spotify",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "search_play | play | pause | resume | next | previous | set_volume | volume_up | volume_down | get_now_playing | get_playlists | get_queue | get_devices | auth",
            },
            "query": {
                "type": "STRING",
                "description": "Song, artist, album, or playlist name to search and play",
            },
            "volume": {
                "type": "NUMBER",
                "description": "Volume percentage (0-100)",
            },
        },
    },
}


def _theme_colour(key: str, fallback: str | None = None) -> str | None:
    """Read a colour from the active theme, with an optional fallback."""
    try:
        from theme_tokens import theme_colour
        return theme_colour(key) or fallback
    except Exception:
        return fallback


def _load_spotify_controller():
    """Load the Spotify MCP controller defensively."""
    try:
        from actions.spotify_controller import spotify_mcp_controller, is_spotify_configured
        return spotify_mcp_controller, is_spotify_configured, None
    except Exception as exc:
        return None, None, exc


def execute(**kwargs) -> dict:
    """Executes Spotify MCP action and returns a formatted result."""
    spotify_mcp_controller, is_spotify_configured, load_error = _load_spotify_controller()

    if spotify_mcp_controller is None:
        return {
            "title": "Spotify MCP Controller",
            "summary": (
                "Spotify control is not available on this machine. "
                "The Spotify MCP controller could not be loaded. "
                "Install/configure the Spotify MCP integration to enable playback control."
            ),
            "spoken_narrative": "Spotify control is not available on this machine.",
            "configured": False,
            "error": str(load_error) if load_error else "controller not available",
        }

    # Determine action from parameters or kwargs
    action = kwargs.get("action", "search_play")
    query = kwargs.get("query", "")
    volume = kwargs.get("volume")

    if not query:
        for k in ("song", "track", "music", "title", "artist"):
            if k in kwargs and kwargs[k]:
                query = kwargs[k]
                break

    params = {
        "action": action,
        "query": query,
    }
    if volume is not None:
        params["volume"] = volume

    try:
        result_text = spotify_mcp_controller(parameters=params)
    except Exception as exc:
        return {
            "title": "Spotify MCP Controller",
            "summary": f"Spotify action '{action}' failed: {exc}",
            "spoken_narrative": f"Spotify action {action} failed.",
            "configured": bool(is_spotify_configured and is_spotify_configured()),
            "error": str(exc),
        }

    try:
        configured = bool(is_spotify_configured())
    except Exception:
        configured = False

    return {
        "title": "Spotify MCP Controller",
        "summary": result_text,
        "spoken_narrative": result_text,
        "configured": configured,
    }
