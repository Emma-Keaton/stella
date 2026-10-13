"""stella_connect.joiner - the outbound half of pairing.

The gateway (``stella_connect.gateway``) is the *host*: it advertises itself,
accepts websockets and approves peers. This module is the *joiner*: given a
:class:`~stella_connect.pairing_flow.PairingTarget` - however it was found (QR,
discovery or a typed address) - it runs the same handshake against a host:

    connect -> PAIR_REQUEST -> PAIR_APPROVED -> AUTHENTICATE -> DEVICE_ONLINE

because every target is identical once resolved, the desktop, the phone and the
public build share this one code path. It is deliberately blocking and stdlib
friendly so it can be called from a Qt worker thread or a script.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .pairing_flow import PairingTarget, PairingError
from .gateway.protocol import ProtocolTypes, build_message

# Sent alongside a pairing request so the host can label the peer in its UI.
DEFAULT_CAPABILITIES = ["chat", "notifications", "clipboard", "files"]


@dataclass(slots=True)
class JoinResult:
    success: bool
    device: dict[str, Any] = field(default_factory=dict)
    device_secret: str = ""
    capabilities: list[str] = field(default_factory=list)
    error: str = ""
    error_code: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "device": dict(self.device),
            "device_secret": self.device_secret,
            "capabilities": list(self.capabilities),
            "error": self.error,
            "error_code": self.error_code,
        }


def _identity_payload(identity: dict[str, Any] | None) -> dict[str, Any]:
    identity = dict(identity or {})
    return {
        "device_name": str(identity.get("name") or identity.get("device_name") or "Stella Device"),
        "platform": str(identity.get("platform") or "unknown"),
        "os_version": str(identity.get("os_version") or ""),
        "agent_version": str(identity.get("agent_version") or ""),
        "capabilities": list(identity.get("capabilities") or DEFAULT_CAPABILITIES),
        "permissions": list(identity.get("permissions") or []),
        "metadata": dict(identity.get("metadata") or {}),
    }


class PairingClient:
    """Blocking outbound pairing client for a single target."""

    def __init__(self, target: PairingTarget, identity: dict[str, Any] | None = None,
                 *, open_timeout: float = 5.0, reply_timeout: float = 30.0) -> None:
        self.target = target
        self.identity = _identity_payload(identity)
        self.open_timeout = open_timeout
        self.reply_timeout = reply_timeout

    def _pair_payload(self) -> dict[str, Any]:
        payload = dict(self.identity)
        if self.target.pairing_token:
            payload["pairing_token"] = self.target.pairing_token
        if self.target.pairing_code:
            payload["pairing_code"] = self.target.pairing_code
        return payload

    def join(self) -> JoinResult:
        try:
            from websockets.sync.client import connect
        except Exception as exc:  # pragma: no cover - dependency guard
            return JoinResult(False, error=f"websocket client unavailable: {exc}",
                              error_code="NO_CLIENT")

        try:
            with connect(self.target.ws_url, open_timeout=self.open_timeout) as ws:
                # 1. Ask to pair. The host either approves immediately (QR/code)
                #    or queues the request for a human to approve in its UI.
                pair = build_message(ProtocolTypes.PAIR_REQUEST, self._pair_payload())
                ws.send(json.dumps(pair))
                approved = self._await(ws, {ProtocolTypes.PAIR_APPROVED, ProtocolTypes.ERROR,
                                            ProtocolTypes.PAIR_REQUEST})
                if approved is None:
                    return JoinResult(False, error="No response from host.",
                                      error_code="TIMEOUT")
                if approved["type"] == ProtocolTypes.ERROR:
                    return JoinResult(False, error=self._err(approved),
                                      error_code="PAIR_REJECTED")
                if approved["type"] == ProtocolTypes.PAIR_REQUEST:
                    # Host is waiting for local approval; keep listening.
                    approved = self._await(ws, {ProtocolTypes.PAIR_APPROVED, ProtocolTypes.ERROR})
                    if approved is None:
                        return JoinResult(False, error="Pairing not approved on the host in time.",
                                          error_code="TIMEOUT")
                    if approved["type"] == ProtocolTypes.ERROR:
                        return JoinResult(False, error=self._err(approved),
                                          error_code="PAIR_REJECTED")

                body = dict(approved.get("payload") or {})
                device = dict(body.get("device") or {})
                secret = str(body.get("device_secret") or "")
                if not device.get("device_id") or not secret:
                    return JoinResult(False, error="Host did not return credentials.",
                                      error_code="BAD_RESPONSE")

                # 2. Authenticate the fresh credentials so we are a live peer.
                auth = build_message(ProtocolTypes.AUTHENTICATE, {
                    "device_id": device.get("device_id"),
                    "device_secret": secret,
                })
                ws.send(json.dumps(auth))
                online = self._await(ws, {ProtocolTypes.DEVICE_ONLINE, ProtocolTypes.ERROR,
                                          ProtocolTypes.CAPABILITIES})
                if online is None or online["type"] == ProtocolTypes.ERROR:
                    msg = "Authentication failed." if online else "No response from host."
                    return JoinResult(False, device=device, error=msg,
                                      error_code="AUTH_FAILED")

                capabilities = list(dict(online.get("payload") or {}).get("capabilities") or [])
                if not capabilities:
                    extra = self._await(ws, {ProtocolTypes.CAPABILITIES}, optional=True)
                    if extra is not None:
                        capabilities = list(dict(extra.get("payload") or {}).get("capabilities") or [])

                return JoinResult(True, device=device, device_secret=secret,
                                  capabilities=capabilities)
        except PairingError as exc:
            return JoinResult(False, error=str(exc), error_code="BAD_TARGET")
        except Exception as exc:
            return JoinResult(False, error=f"Could not reach {self.target.label()}: {exc}",
                              error_code="UNREACHABLE")

    def _await(self, ws, types: set[str], *, optional: bool = False) -> dict[str, Any] | None:
        while True:
            try:
                raw = ws.recv(timeout=self.reply_timeout if not optional else min(2.0, self.reply_timeout))
            except Exception:
                return None
            try:
                msg = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                continue
            msg_type = str(msg.get("type") or "").strip().lower()
            if msg_type in types:
                return msg
            if optional and msg_type:
                return None

    @staticmethod
    def _err(msg: dict[str, Any]) -> str:
        return str(dict(msg.get("payload") or {}).get("error") or "Pairing rejected.")


def join(target: PairingTarget | dict[str, Any], identity: dict[str, Any] | None = None) -> JoinResult:
    """Convenience wrapper accepting either a target or its dict form."""
    if isinstance(target, dict):
        target = PairingTarget(
            host=str(target.get("host") or ""),
            port=int(target.get("port") or 8765),
            pairing_token=str(target.get("pairing_token") or ""),
            pairing_code=str(target.get("pairing_code") or ""),
            name=str(target.get("name") or ""),
            platform=str(target.get("platform") or ""),
            method=str(target.get("method") or "manual"),
        )
    if not target.host:
        return JoinResult(False, error="No host address.", error_code="BAD_TARGET")
    return PairingClient(target, identity).join()
