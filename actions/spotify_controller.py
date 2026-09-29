"""
Universal Spotify Controller for Brahma AI.
Powered by Spotify Model Context Protocol (MCP) Server (https://github.com/marcelmarais/spotify-mcp-server).

Provides full official Spotify Web API playback control, search, playlists,
queue management, volume control, and device handover via MCP JSON-RPC stdio.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.user_paths import get_user_data_dir

logger = logging.getLogger("SpotifyMCPController")

BASE_DIR = Path(__file__).resolve().parent.parent
MCP_SERVER_DIR = Path(__file__).resolve().parent / "spotify_mcp_server"
MCP_BUILD_INDEX = MCP_SERVER_DIR / "build" / "index.js"
MCP_BUILD_AUTH = MCP_SERVER_DIR / "build" / "auth.js"

APPDATA_CONFIG_PATH = get_user_data_dir() / "config" / "spotify-config.json"
LOCAL_CONFIG_PATH = MCP_SERVER_DIR / "spotify-config.json"

PLUGIN = {
    "name": "spotify_controller",
    "description": (
        "Controls Spotify playback, searches tracks/albums/playlists, manages queue, "
        "adjusts volume, and inspects now-playing status via Spotify MCP Server. "
        "Supports actions: 'search_play' (play track/artist/album/playlist), 'play', 'pause', "
        "'resume', 'next', 'previous', 'set_volume', 'volume_up', 'volume_down', 'get_now_playing', "
        "'get_playlists', 'get_queue', 'get_devices', 'auth', 'open_spotify'."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": (
                    "search_play | play | pause | resume | next | previous | set_volume | "
                    "volume_up | volume_down | get_now_playing | get_playlists | get_queue | "
                    "get_devices | auth | open_spotify (default: search_play)"
                ),
            },
            "query": {
                "type": "STRING",
                "description": "Song title, artist name, album, or playlist to search and play.",
            },
            "volume": {
                "type": "NUMBER",
                "description": "Volume percentage from 0 to 100 (optional).",
            },
            "device_id": {
                "type": "STRING",
                "description": "Target Spotify device ID to transfer or play to (optional).",
            },
        },
        "required": ["action"],
    },
}


def get_active_config_path() -> Path:
    """Finds or initializes the spotify-config.json path."""
    if APPDATA_CONFIG_PATH.exists():
        return APPDATA_CONFIG_PATH
    if LOCAL_CONFIG_PATH.exists():
        return LOCAL_CONFIG_PATH
    return APPDATA_CONFIG_PATH


def is_spotify_configured() -> bool:
    """Checks if Spotify client credentials and tokens exist."""
    path = get_active_config_path()
    if not path.exists():
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return bool(data.get("clientId") and data.get("clientSecret"))
    except Exception:
        return False


def save_spotify_credentials(client_id: str, client_secret: str, redirect_uri: str = "http://127.0.0.1:8888/callback") -> bool:
    """Saves or updates Spotify credentials in both AppData and local MCP server configs."""
    try:
        config_data = {}
        for p in (APPDATA_CONFIG_PATH, LOCAL_CONFIG_PATH):
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        config_data.update(json.load(f))
                except Exception:
                    pass

        config_data["clientId"] = client_id.strip()
        config_data["clientSecret"] = client_secret.strip()
        config_data["redirectUri"] = redirect_uri.strip()

        APPDATA_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(APPDATA_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)

        with open(LOCAL_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)

        return True
    except Exception as e:
        logger.error(f"[SpotifyMCP] Failed to save credentials: {e}")
        return False


class SpotifyMCPClient:
    """
    Subprocess JSON-RPC 2.0 client for spotify-mcp-server.
    Connects to Node.js MCP server over stdio.
    """

    _instance: Optional["SpotifyMCPClient"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._req_id = 0
        self._req_lock = threading.Lock()
        self._initialized = False

    @classmethod
    def get_instance(cls) -> "SpotifyMCPClient":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _ensure_running(self) -> bool:
        """Starts or restarts the Node.js MCP process if dead."""
        if self._proc is not None and self._proc.poll() is None:
            return True

        if not MCP_BUILD_INDEX.exists():
            logger.error(f"[SpotifyMCP] Server script not found at {MCP_BUILD_INDEX}")
            return False

        config_file = get_active_config_path()
        env = os.environ.copy()
        if config_file.exists():
            env["SPOTIFY_CONFIG_PATH"] = str(config_file.resolve())

        try:
            self._proc = subprocess.Popen(
                ["node", str(MCP_BUILD_INDEX.resolve())],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,
                cwd=str(MCP_SERVER_DIR.resolve()),
                env=env,
            )

            # Perform MCP Handshake
            init_req = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "brahma-ai-spotify", "version": "1.0.0"},
                },
            }
            resp = self._send_raw(init_req)
            if not resp or "result" not in resp:
                logger.warning(f"[SpotifyMCP] Unexpected init handshake response: {resp}")

            # Send initialized notification
            notify = {"jsonrpc": "2.0", "method": "notifications/initialized"}
            self._send_notification(notify)

            self._initialized = True
            logger.info("[SpotifyMCP] Spotify MCP Server successfully connected via stdio.")
            return True
        except Exception as e:
            logger.error(f"[SpotifyMCP] Failed to launch node process: {e}")
            self._proc = None
            return False

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _send_notification(self, payload: Dict[str, Any]):
        if not self._proc or self._proc.poll() is not None:
            return
        try:
            line = json.dumps(payload) + "\n"
            self._proc.stdin.write(line)
            self._proc.stdin.flush()
        except Exception as e:
            logger.warning(f"[SpotifyMCP] Failed to send notification: {e}")

    def _send_raw(self, payload: Dict[str, Any], timeout: float = 12.0) -> Optional[Dict[str, Any]]:
        with self._req_lock:
            if not self._proc or self._proc.poll() is not None:
                return None
            try:
                line = json.dumps(payload) + "\n"
                self._proc.stdin.write(line)
                self._proc.stdin.flush()

                # Read response line
                resp_line = self._proc.stdout.readline()
                if resp_line:
                    return json.loads(resp_line.strip())
            except Exception as e:
                logger.error(f"[SpotifyMCP] JSON-RPC communication error: {e}")
                self._proc = None
            return None

    def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Calls a tool exposed by the Spotify MCP server."""
        if not self._ensure_running():
            return {"error": "Spotify MCP server could not be started."}

        req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {},
            },
        }

        resp = self._send_raw(req)
        if not resp:
            return {"error": f"No response received from Spotify MCP for '{tool_name}'"}

        if "error" in resp:
            err_msg = resp["error"].get("message", str(resp["error"]))
            return {"error": err_msg}

        result = resp.get("result", {})
        content_items = result.get("content", [])
        text_outputs = []
        for item in content_items:
            if isinstance(item, dict) and item.get("type") == "text":
                text_outputs.append(item.get("text", ""))

        output_text = "\n".join(text_outputs) if text_outputs else ""
        return {
            "success": not result.get("isError", False),
            "output": output_text,
            "raw": result,
        }

    def close(self):
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None


def _get_spotify_app_path() -> Optional[str]:
    """Checks if Spotify desktop app is installed on Windows."""
    candidates = [
        os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Spotify\Spotify.exe"),
        r"C:\Program Files\Spotify\Spotify.exe",
        shutil.which("spotify"),
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None


def _open_spotify_fallback() -> str:
    """Launches Spotify desktop app or browser player."""
    app = _get_spotify_app_path()
    if app:
        try:
            subprocess.Popen([app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "Opened Spotify desktop application."
        except Exception:
            pass

    import webbrowser
    webbrowser.open("https://open.spotify.com")
    return "Opened Spotify Web Player in your default browser."


def launch_auth_flow() -> str:
    """Spawns the Spotify OAuth authorization flow in the user's browser."""
    if not MCP_BUILD_AUTH.exists():
        return "Error: Spotify auth script not found. Please compile the server first."

    config_path = get_active_config_path()
    env = os.environ.copy()
    if config_path.exists():
        env["SPOTIFY_CONFIG_PATH"] = str(config_path.resolve())

    try:
        subprocess.Popen(
            ["node", str(MCP_BUILD_AUTH.resolve())],
            cwd=str(MCP_SERVER_DIR.resolve()),
            env=env,
        )
        return (
            "Initiated Spotify authentication flow. A browser tab has opened for you to log in to Spotify "
            "and authorize Brahma AI. Tokens will be automatically saved upon approval."
        )
    except Exception as e:
        return f"Failed to start authentication flow: {e}"


def spotify_controller(
    parameters: dict,
    response: Optional[str] = None,
    player=None,
    session_memory=None,
    speak=None,
) -> str:
    """
    Main entry point for Spotify control via Spotify MCP Server.
    """
    p = parameters or {}
    action = p.get("action", "search_play").lower().strip()
    query = p.get("query", "").strip()
    volume = p.get("volume")
    device_id = p.get("device_id")

    client = SpotifyMCPClient.get_instance()

    # 1. Authorization action
    if action in ("auth", "login", "authenticate", "setup"):
        return launch_auth_flow()

    # 2. Open desktop app or web player fallback
    if action in ("open", "open_spotify", "launch"):
        return _open_spotify_fallback()

    # Check config existence
    if not is_spotify_configured():
        return (
            "Spotify MCP is not yet configured with credentials. "
            "Please add your Spotify 'clientId' and 'clientSecret' to your configuration, "
            "then say 'authenticate Spotify' to connect your account."
        )

    # 3. Search and Play / Play
    if action in ("search_play", "play_song", "play", "play_music", "start"):
        if query:
            # Search for the track first using MCP searchSpotify tool
            search_res = client.call_tool("searchSpotify", {
                "query": query,
                "type": "track",
                "limit": 3,
            })
            if not search_res.get("success"):
                err = search_res.get("error") or search_res.get("output")
                if "No access token" in str(err) or "expired" in str(err).lower():
                    return f"Spotify authentication required: {err}. Say 'authenticate Spotify' to log in."
                return f"Spotify search error: {err}"

            # Parse search results
            output = search_res.get("output", "")
            track_uri = None
            track_name = query
            artist_name = ""

            # Try to extract URI from JSON or formatted text
            try:
                data = json.loads(output)
                items = data.get("tracks", {}).get("items", []) or data.get("items", [])
                if items:
                    track_uri = items[0].get("uri")
                    track_name = items[0].get("name", query)
                    artists = items[0].get("artists", [])
                    if artists:
                        artist_name = artists[0].get("name", "")
            except Exception:
                import re
                m_uri = re.search(r"spotify:track:[a-zA-Z0-9]+", output)
                if m_uri:
                    track_uri = m_uri.group(0)

            # Play the track via MCP playMusic tool
            args: Dict[str, Any] = {}
            if track_uri:
                args["uri"] = track_uri
            else:
                args["uri"] = f"spotify:search:{query}"

            if device_id:
                args["deviceId"] = device_id

            play_res = client.call_tool("playMusic", args)
            if play_res.get("success"):
                artist_disp = f" by {artist_name}" if artist_name else ""
                msg = f"Playing '{track_name}'{artist_disp} on Spotify."
                if speak:
                    speak(msg)
                return msg
            else:
                err = play_res.get("error") or play_res.get("output")
                return f"Could not start playback: {err}"
        else:
            # Resume playback
            resume_res = client.call_tool("resumePlayback", {"deviceId": device_id} if device_id else {})
            if resume_res.get("success"):
                return "Resumed Spotify playback."
            # Fallback to playMusic with empty args
            play_res = client.call_tool("playMusic", {"deviceId": device_id} if device_id else {})
            return play_res.get("output") or "Resumed playback."

    # 4. Pause Playback
    elif action in ("pause", "stop", "hold"):
        res = client.call_tool("pausePlayback", {"deviceId": device_id} if device_id else {})
        if res.get("success"):
            return "Paused Spotify playback."
        return res.get("output") or res.get("error") or "Paused playback."

    # 5. Resume Playback
    elif action in ("resume", "unpause"):
        res = client.call_tool("resumePlayback", {"deviceId": device_id} if device_id else {})
        if res.get("success"):
            return "Resumed Spotify playback."
        return res.get("output") or res.get("error") or "Resumed playback."

    # 6. Skip / Next Track
    elif action in ("next", "skip", "next_track"):
        res = client.call_tool("skipToNext", {"deviceId": device_id} if device_id else {})
        if res.get("success"):
            return "Skipped to next song on Spotify."
        return res.get("output") or res.get("error") or "Skipped to next song."

    # 7. Previous Track
    elif action in ("previous", "prev", "back", "previous_track"):
        res = client.call_tool("skipToPrevious", {"deviceId": device_id} if device_id else {})
        if res.get("success"):
            return "Playing previous song on Spotify."
        return res.get("output") or res.get("error") or "Playing previous song."

    # 8. Volume Controls
    elif action in ("set_volume", "volume"):
        vol_pct = int(volume if volume is not None else 50)
        vol_pct = max(0, min(100, vol_pct))
        args = {"volumePercent": vol_pct}
        if device_id:
            args["deviceId"] = device_id
        res = client.call_tool("setVolume", args)
        if res.get("success"):
            return f"Set Spotify volume to {vol_pct}%."
        return res.get("output") or res.get("error") or f"Volume set to {vol_pct}%."

    elif action in ("volume_up", "vol_up"):
        res = client.call_tool("adjustVolume", {"volumeDelta": 10})
        if res.get("success"):
            return "Increased Spotify volume."
        return res.get("output") or "Increased volume."

    elif action in ("volume_down", "vol_down"):
        res = client.call_tool("adjustVolume", {"volumeDelta": -10})
        if res.get("success"):
            return "Decreased Spotify volume."
        return res.get("output") or "Decreased volume."

    # 9. Now Playing Status
    elif action in ("get_now_playing", "now_playing", "current_song", "current_track", "status"):
        res = client.call_tool("getNowPlaying", {})
        if res.get("success") and res.get("output"):
            output = res["output"]
            return f"Spotify Now Playing:\n{output}"
        return res.get("output") or res.get("error") or "No active track currently playing on Spotify."

    # 10. Playlists
    elif action in ("get_playlists", "my_playlists", "playlists", "list_playlists"):
        res = client.call_tool("getMyPlaylists", {"limit": 10})
        if res.get("success") and res.get("output"):
            return f"Your Spotify Playlists:\n{res['output']}"
        return res.get("output") or res.get("error") or "Could not retrieve Spotify playlists."

    # 11. Queue
    elif action in ("get_queue", "queue"):
        res = client.call_tool("getQueue", {"limit": 5})
        if res.get("success") and res.get("output"):
            return f"Upcoming Spotify Queue:\n{res['output']}"
        return res.get("output") or res.get("error") or "Could not fetch Spotify queue."

    # 12. Devices
    elif action in ("get_devices", "devices", "available_devices"):
        res = client.call_tool("getAvailableDevices", {})
        if res.get("success") and res.get("output"):
            return f"Available Spotify Connect Devices:\n{res['output']}"
        return res.get("output") or res.get("error") or "No Spotify devices detected."

    # Fallback search
    if query:
        return spotify_controller({"action": "search_play", "query": query}, speak=speak)

    return f"Unsupported Spotify action: '{action}'. Try 'play [song]', 'pause', 'next', 'now playing', or 'volume'."
