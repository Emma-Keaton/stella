"""
src/backend/starnet/api_auth.py — API auth / security (StarNet apiauth.js port).

Per-launch secret token required on every API call. Origin allow-list defends
against malicious websites driving the agent via fetch()/EventSource.
Token-exempt routes: /api/health, /api/key, /api/channels/token,
/api/spotify/callback, /api/connectors/oauth/callback.
"""

from __future__ import annotations

import secrets


class ApiAuthManager:
    """Per-launch token authentication and origin allow-listing."""

    def __init__(self) -> None:
        self.launch_token: str = secrets.token_hex(32)
        self._token_exempt: set[str] = {
            "/api/key",
            "/api/channels/token",
            "/api/health",
            "/api/spotify/callback",
            "/api/connectors/oauth/callback",
        }
        self._allowed_origins: set[str] = {
            "http://127.0.0.1",
            "http://localhost",
            "app://stella.local",
        }

    def requires_token(self, path: str) -> bool:
        if not path.startswith("/api/") and path != "/api":
            return False
        return path not in self._token_exempt

    def is_origin_allowed(self, origin: str | None) -> bool:
        if origin is None or origin == "":
            return True
        if origin == "null":
            return False
        return origin in self._allowed_origins

    def verify_token(self, token: str | None) -> bool:
        if not token:
            return False
        if len(token) != len(self.launch_token):
            return False
        result = 0
        for a, b in zip(token, self.launch_token):
            result |= ord(a) ^ ord(b)
        return result == 0