"""
main.py — Stella Python backend entry point.

Bootstraps the Stella engine and exposes it to frontends via a WebSocket IPC
server on localhost. Supports two wire protocols on the same port:

  1. Electron IPC (desktop):  {id, endpoint, payload}  →  {id, endpoint, ok, payload}
  2. Android StellaProtocol:  {type, request_id, timestamp, payload}
                                →  {type, request_id, timestamp, payload}

Follows Mark-LVI's main() pattern:
  1. Create WebSocket server (the "UI")
  2. Start StellaLive engine (asyncio task)
  3. Run the event loop on the main thread

The engine talks to all frontends through exactly one callback: emit().
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set, Set

import websockets

# Ensure repo root is on sys.path for imports
_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.backend.core.engine import StellaEngine  # noqa: E402
from src.backend.memory.config_manager import config_manager  # noqa: E402

logger = logging.getLogger("stella.main")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


# ── Android StellaProtocol constants (mirror AppModels.StellaProtocol) ──
class StellaProtocol:
    HELLO = "hello"
    PAIR_REQUEST = "pair_request"
    PAIR_APPROVED = "pair_approved"
    AUTHENTICATE = "authenticate"
    DEVICE_ONLINE = "device_online"
    DEVICE_OFFLINE = "device_offline"
    CAPABILITIES = "capabilities"
    EXECUTE = "execute"
    RESULT = "result"
    EVENT = "event"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"
    CHAT_MESSAGE = "chat_message"
    HANDOFF = "handoff"
    DEVICE_LINK = "device_link"
    DEVICE_STATUS = "device_status"

    @staticmethod
    def envelope(type_: str, payload: dict = None, request_id: str = None) -> dict:
        return {
            "type": type_,
            "request_id": request_id or uuid.uuid4().hex.replace("-", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload or {},
        }


# ── Client protocol tracking ──
# Tracks which connected clients speak which protocol so we can reply in kind.
_CLIENT_PROTOCOL: Dict[Any, str] = {}  # websocket -> "electron" | "android"

# ── Device link tracking ──
# Tracks peer-to-peer device links: any device can link to any other device
# (mobile↔mobile, PC↔PC, mobile↔PC, PC→mobile). Each device reports its
# capabilities; the PC link layer routes handoffs to a capable peer.
_LINKED_DEVICES: Dict[str, dict] = {}  # device_id -> {platform, capabilities, connected_at, last_seen, linked_by}
_LINK_GRAPH: Dict[str, Set[str]] = {}  # device_id -> set of linked device_ids


class StellaBackend:
    """
    Stella backend host: wraps StellaEngine + WebSocket IPC server.

    Accepts connections from Electron (desktop) and Android (mobile) frontends.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self._server = None
        self._clients: Set[Any] = set()
        self._engine: Optional[StellaEngine] = None
        self._running = False

    # ── emit callback (engine → all frontends) ──
    # This is the ONE frontend touchpoint — engine never touches UI directly.

    def _emit(self, event_type: str, payload: Any) -> None:
        """Broadcast an event to all connected clients in their native protocol."""
        if not self._clients:
            return
        for client in list(self._clients):
            proto = _CLIENT_PROTOCOL.get(client, "electron")
            try:
                if proto == "android":
                    message = json.dumps(
                        StellaProtocol.envelope(event_type, payload),
                        ensure_ascii=False,
                    )
                else:
                    message = json.dumps(
                        {"type": "event", "endpoint": event_type, "payload": payload},
                        ensure_ascii=False,
                    )
                asyncio.ensure_future(client.send(message))
            except Exception:
                self._clients.discard(client)
                _CLIENT_PROTOCOL.pop(client, None)

    # ── IPC message handling (frontend → engine) ──

    async def _handle_message(self, websocket, message: str) -> None:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            await self._send_error(websocket, "invalid_json", "Could not parse JSON")
            return

        # Detect protocol: Android uses "type", Electron uses "endpoint"
        msg_type = data.get("type")
        endpoint = data.get("endpoint")

        if msg_type and not endpoint:
            # Android StellaProtocol format
            _CLIENT_PROTOCOL[websocket] = "android"
            await self._handle_android_message(websocket, data)
        elif endpoint:
            # Electron IPC format
            _CLIENT_PROTOCOL[websocket] = "electron"
            await self._handle_electron_message(websocket, data)
        else:
            await self._send_error(websocket, "unknown_format", "Cannot determine message format")

    # ── Electron IPC handler ──

    async def _handle_electron_message(self, websocket, data: dict) -> None:
        endpoint = data.get("endpoint")
        payload = data.get("payload", {})
        msg_id = data.get("id")
        print("DEBUG: _handle_electron_message called, endpoint=%s" % endpoint, flush=True)

        if not endpoint:
            await self._send_error(websocket, "missing_endpoint", "No endpoint specified", msg_id)
            return

        try:
            result = await self._dispatch(endpoint, payload)
            # Debug: check JSON serializability
            import json as _json
            try:
                _json.dumps(result)
            except Exception as _je:
                logger.error("JSON serialize error for %s: %s", endpoint, _je)
                if isinstance(result, list):
                    for i, d in enumerate(result):
                        try:
                            _json.dumps(d)
                        except Exception as _de:
                            logger.error("  Declaration %d (%s) not serializable: %s", i, d.get('name', 'unknown') if isinstance(d, dict) else 'not-dict', _de)
                await self._send_electron_error(websocket, msg_id, "serialize_error", str(_je))
                return
            await self._send_electron_response(websocket, msg_id, endpoint, result)
        except Exception as e:
            logger.error("IPC handler error for %s: %s", endpoint, e)
            await self._send_electron_error(websocket, msg_id, "handler_error", str(e))

    # ── Android StellaProtocol handler ──

    async def _handle_android_message(self, websocket, data: dict) -> None:
        msg_type = data.get("type")
        payload = data.get("payload", {})
        request_id = data.get("request_id")

        try:
            if msg_type == StellaProtocol.HELLO:
                result = await self._android_hello(payload)
                await self._send_android_response(websocket, request_id, StellaProtocol.DEVICE_ONLINE, result)

            elif msg_type == StellaProtocol.AUTHENTICATE:
                result = await self._android_authenticate(payload)
                await self._send_android_response(websocket, request_id, StellaProtocol.DEVICE_ONLINE, result)

            elif msg_type == StellaProtocol.CHAT_MESSAGE:
                result = await self._android_chat_message(payload)
                await self._send_android_response(websocket, request_id, StellaProtocol.CHAT_MESSAGE, result)

            elif msg_type == StellaProtocol.EXECUTE:
                result = await self._android_execute(payload)
                await self._send_android_response(websocket, request_id, StellaProtocol.RESULT, result)

            elif msg_type == StellaProtocol.PING:
                await self._send_android_response(websocket, request_id, StellaProtocol.PONG, {"status": "ok"})

            elif msg_type == StellaProtocol.PAIR_REQUEST:
                await self._send_android_response(
                    websocket, request_id, StellaProtocol.PAIR_APPROVED,
                    {"status": "awaiting_approval", "device_id": "stella-desktop"},
                )

            elif msg_type == StellaProtocol.CAPABILITIES:
                await self._send_android_response(
                    websocket, request_id, StellaProtocol.CAPABILITIES,
                    {"synced": True},
                )

            elif msg_type == StellaProtocol.HANDOFF:
                result = await self._android_handoff(payload)
                await self._send_android_response(websocket, request_id, StellaProtocol.RESULT, result)

            elif msg_type == StellaProtocol.DEVICE_LINK:
                result = await self._android_device_link(payload)
                await self._send_android_response(websocket, request_id, StellaProtocol.DEVICE_ONLINE, result)

            elif msg_type == StellaProtocol.DEVICE_STATUS:
                result = await self._android_device_status(payload)
                await self._send_android_response(websocket, request_id, StellaProtocol.RESULT, result)

            else:
                await self._send_android_error(websocket, request_id, "unknown_type", f"Unknown Android message type: {msg_type}")

        except Exception as e:
            logger.error("Android handler error for %s: %s", msg_type, e)
            await self._send_android_error(websocket, request_id, "handler_error", str(e))

    # ── Android protocol handlers ──

    async def _android_hello(self, payload: dict) -> dict:
        """Android sends HELLO with device snapshot. Respond with device_online."""
        engine = self._engine
        if engine:
            engine.state["connected"] = True
            engine._emit_state()
        return {
            "device_id": "stella-desktop",
            "device_name": "Stella Desktop",
            "platform": "desktop",
            "status": "online",
        }

    async def _android_authenticate(self, payload: dict) -> dict:
        """Android authenticates with device credentials."""
        engine = self._engine
        if engine:
            engine.state["connected"] = True
            engine._emit_state()
        return {
            "authenticated": True,
            "device_id": "stella-desktop",
            "token": "stella-session",
        }

    async def _android_chat_message(self, payload: dict) -> dict:
        """Android sends a chat message. Route through agent integration."""
        text = payload.get("text", "")
        engine = self._engine
        if not engine:
            return {"reply": "Engine not available"}
        context = {"source": "android", "platform": "android"}
        result = engine.integration.send(text, context)
        return {
            "reply": result,
            "honesty": engine.integration.get_honesty_summary(),
        }

    async def _android_execute(self, payload: dict) -> dict:
        """Android requests a tool/command execution."""
        action = payload.get("action", "")
        parameters = payload.get("parameters", {})
        engine = self._engine
        if not engine:
            return {"success": False, "error": "Engine not available"}
        context = {"source": "android"}
        result = engine.integration.executor.execute(action, parameters, context)
        return {
            "success": True,
            "action": action,
            "result": result,
        }

    # ── PC Link / Device Connection Bridge ──
    # Peer-to-peer device linking: any device can link to any other device
    # (mobile↔mobile, PC↔PC, mobile↔PC, PC→mobile). The PC link layer routes
    # handoffs to a capable peer.

    async def _android_device_link(self, payload: dict) -> dict:
        """Any device registers as a linked peer for PC link / handoff.

        Payload: {device_id, platform, capabilities, link_to}
        - device_id: unique id of the linking device
        - platform: "android", "ios", "desktop", "web"
        - capabilities: list of capability strings (e.g. ["coding", "web_search"])
        - link_to: optional target device_id to create a bidirectional link
        """
        device_id = payload.get("device_id") or "unknown-device"
        platform = payload.get("platform") or "unknown"
        capabilities = payload.get("capabilities") or []
        link_to = payload.get("link_to")

        _LINKED_DEVICES[device_id] = {
            "platform": platform,
            "capabilities": capabilities,
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "linked_by": link_to,
        }

        # Ensure graph entries exist
        _LINK_GRAPH.setdefault(device_id, set())

        # Create bidirectional link if link_to is specified
        if link_to:
            _LINK_GRAPH.setdefault(link_to, set()).add(device_id)
            _LINK_GRAPH[device_id].add(link_to)
            _LINKED_DEVICES.setdefault(link_to, {})

        engine = self._engine
        if engine:
            engine.state["connected"] = True
            engine._emit_state()

        return {
            "device_id": device_id,
            "platform": "desktop",
            "status": "linked",
            "linked_devices": sorted(_LINK_GRAPH.get(device_id, set())),
            "message": "Device linked. Peer-to-peer handoff available between linked devices.",
        }

    async def _android_device_status(self, payload: dict) -> dict:
        """A linked device reports its status/capabilities to the PC link."""
        device_id = payload.get("device_id") or "unknown-device"
        if device_id in _LINKED_DEVICES:
            _LINKED_DEVICES[device_id]["last_seen"] = datetime.now(timezone.utc).isoformat()
            _LINKED_DEVICES[device_id]["capabilities"] = payload.get("capabilities", [])
        else:
            # First-time registration via status
            _LINKED_DEVICES[device_id] = {
                "platform": payload.get("platform") or "unknown",
                "capabilities": payload.get("capabilities") or [],
                "connected_at": datetime.now(timezone.utc).isoformat(),
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "linked_by": None,
            }
            _LINK_GRAPH.setdefault(device_id, set())

        return {
            "device_id": device_id,
            "linked_devices": sorted(_LINK_GRAPH.get(device_id, set())),
            "all_devices": _LINKED_DEVICES,
            "pc_can_handle_coding": True,
        }

    async def _android_handoff(self, payload: dict) -> dict:
        """A device hands off a task to a capable peer.

        Payload: {action, parameters, goal, context, from_device, to_device}
        - from_device: the device handing off (defaults to caller)
        - to_device: target device_id (defaults to desktop/PC if capable)
        The PC executes via the agent executor if it is the target, or routes
        to another capable peer.
        """
        action = payload.get("action", "")
        parameters = payload.get("parameters", {})
        goal = payload.get("goal", "")
        context = payload.get("context", {})
        from_device = payload.get("from_device") or "unknown"
        to_device = payload.get("to_device")

        context["source"] = "device_handoff"
        context["platform"] = "peer"
        context["from_device"] = from_device

        engine = self._engine

        # Determine the target device for the handoff
        target = to_device
        if not target:
            # Prefer a peer that lists "coding" capability, else desktop
            for did, info in _LINKED_DEVICES.items():
                if did != from_device and "coding" in (info.get("capabilities") or []):
                    target = did
                    break
            if not target and engine:
                target = "desktop"

        # If the target is this desktop/PC, execute locally
        if target == "desktop" or (target is None and engine):
            if not engine:
                return {
                    "success": False,
                    "error": "No engine available to execute handoff",
                    "handed_off_to": None,
                    "from_device": from_device,
                }
            try:
                result = engine.integration.executor.execute(action, parameters, context)
                return {
                    "success": True,
                    "action": action,
                    "result": result,
                    "handed_off_to": "desktop",
                    "from_device": from_device,
                    "goal": goal,
                }
            except Exception as e:
                logger.error("Handoff execution failed: %s", e)
                return {
                    "success": False,
                    "error": str(e),
                    "handed_off_to": None,
                    "from_device": from_device,
                }

        # Target is another peer — the PC cannot execute it directly here,
        # but it can record the intent and report which peer is capable.
        target_info = _LINKED_DEVICES.get(target, {})
        return {
            "success": True,
            "action": action,
            "result": f"Handoff queued for peer {target} (capabilities: {target_info.get('capabilities', [])}). Peer-to-peer execution requires the target device to pull pending handoffs.",
            "handed_off_to": target,
            "from_device": from_device,
            "goal": goal,
            "peer_capabilities": target_info.get("capabilities", []),
        }

    # ── Dispatch (shared between protocols) ──

    async def _dispatch(self, endpoint: str, payload: dict) -> Any:
        engine = self._engine
        if not engine:
            raise RuntimeError("Engine not started")

        logger.info("DISPATCH: %s", endpoint)

        if endpoint == "backend.ping":
            return {"status": "pong"}

        if endpoint == "config.read":
            return config_manager.load_api_keys()

        if endpoint == "config.write":
            config_manager.save_api_keys(payload)
            return {"ok": True}

        if endpoint == "config.provider.mode":
            return config_manager.get_provider_mode()

        if endpoint == "agent.tool.declarations":
            logger.info("DISPATCH: calling engine._build_config()")
            result = engine._build_config()
            logger.info("DISPATCH: _build_config returned %d items", len(result) if isinstance(result, list) else type(result))
            import json as _json
            try:
                _json.dumps(result)
                logger.info("DISPATCH: _build_config result is JSON serializable")
            except Exception as _je:
                logger.error("DISPATCH: _build_config result NOT JSON serializable: %s", _je)
            return result

        if endpoint == "agent.run":
            text = payload.get("text", "")
            context = payload.get("context", {})
            result = engine.integration.send(text, context)
            return {"result": result, "honesty": engine.integration.get_honesty_summary()}

        if endpoint == "agent.tool.list":
            return engine.integration.get_tools()

        if endpoint == "agent.skill.list":
            return engine.skill_loader.list_skills()

        if endpoint == "action.list":
            return [engine.action_registry.get_tool(n) for n in engine.action_registry.names()]

        if endpoint == "plugin.list":
            return engine.plugin_registry.list_for_ui(config_manager.get_plugin_enabled)

        if endpoint == "plugin.toggle":
            name = payload.get("name")
            enabled = payload.get("enabled", True)
            config_manager.save_plugin_enabled(name, enabled)
            return {"ok": True, "name": name, "enabled": enabled}

        if endpoint == "memory.read":
            from src.backend.memory.memory_manager import load_memory
            return load_memory()

        if endpoint == "session.start":
            engine.state["connected"] = True
            engine._emit_state()
            return {"ok": True}

        if endpoint == "evolution.summary":
            return engine.evolution.get_summary()

        if endpoint == "device.link.list":
            return {
                "devices": _LINKED_DEVICES,
                "links": {k: sorted(v) for k, v in _LINK_GRAPH.items()},
            }

        if endpoint == "device.link.handoff":
            action = payload.get("action", "")
            parameters = payload.get("parameters", {})
            goal = payload.get("goal", "")
            context = payload.get("context", {})
            context["source"] = "pc_link"
            context["platform"] = "desktop"
            engine = self._engine
            if not engine:
                return {"success": False, "error": "PC engine not available"}
            try:
                result = engine.integration.executor.execute(action, parameters, context)
                return {"success": True, "action": action, "result": result}
            except Exception as e:
                return {"success": False, "error": str(e)}

        if endpoint == "device.link.create":
            device_id = payload.get("device_id") or "desktop-device"
            platform = payload.get("platform") or "desktop"
            capabilities = payload.get("capabilities") or ["coding", "web_search", "file_ops"]
            link_to = payload.get("link_to")
            _LINKED_DEVICES[device_id] = {
                "platform": platform,
                "capabilities": capabilities,
                "connected_at": datetime.now(timezone.utc).isoformat(),
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "linked_by": link_to,
            }
            _LINK_GRAPH.setdefault(device_id, set())
            if link_to:
                _LINK_GRAPH.setdefault(link_to, set()).add(device_id)
                _LINK_GRAPH[device_id].add(link_to)
            return {
                "device_id": device_id,
                "status": "linked",
                "linked_devices": sorted(_LINK_GRAPH.get(device_id, set())),
            }

        raise ValueError(f"Unknown endpoint: {endpoint}")

    # ── Response helpers ──

    async def _send_electron_response(self, websocket, msg_id: Any, endpoint: str, result: Any) -> None:
        message = json.dumps(
            {"id": msg_id, "endpoint": endpoint, "ok": True, "payload": result},
            ensure_ascii=False,
        )
        await websocket.send(message)

    async def _send_electron_error(self, websocket, msg_id: Any, code: str, message: str) -> None:
        data = {"id": msg_id, "ok": False, "error": {"code": code, "message": message}}
        await websocket.send(json.dumps(data, ensure_ascii=False))

    async def _send_android_response(self, websocket, request_id: Optional[str], type_: str, payload: dict) -> None:
        message = json.dumps(
            StellaProtocol.envelope(type_, payload, request_id),
            ensure_ascii=False,
        )
        await websocket.send(message)

    async def _send_android_error(self, websocket, request_id: Optional[str], code: str, message: str) -> None:
        data = StellaProtocol.envelope(
            StellaProtocol.ERROR,
            {"code": code, "message": message},
            request_id,
        )
        await websocket.send(json.dumps(data, ensure_ascii=False))

    async def _send_error(self, websocket, code: str, message: str, msg_id: Any = None) -> None:
        # Fallback: assume electron format
        data = {"id": msg_id, "ok": False, "error": {"code": code, "message": message}}
        await websocket.send(json.dumps(data, ensure_ascii=False))

    # ── WebSocket handler ──

    async def _ws_handler(self, websocket) -> None:
        self._clients.add(websocket)
        logger.info("Frontend connected (clients: %d)", len(self._clients))
        try:
            async for message in websocket:
                await self._handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._clients.discard(websocket)
            _CLIENT_PROTOCOL.pop(websocket, None)
            logger.info("Frontend disconnected (clients: %d)", len(self._clients))

    # ── Lifecycle ──

    async def start(self) -> None:
        """Start WebSocket server and Stella engine."""
        self._server = await websockets.serve(self._ws_handler, self.host, self.port)
        logger.info("WebSocket IPC server listening on %s:%d", self.host, self.port)

        # Create and start engine
        self._engine = StellaEngine(emit=self._emit)
        self._engine.start()

        # Run engine loop
        self._running = True
        await self._engine.run()

    async def stop(self) -> None:
        """Stop engine and WebSocket server."""
        self._running = False
        if self._engine:
            self._engine.stop()
        if self._server:
            self._server.close()
            await self._server.wait_closed()


async def _async_main(host: str, port: int) -> None:
    backend = StellaBackend(host=host, port=port)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Received shutdown signal")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass  # Windows may not support all signals

    # Run backend until stop signal
    backend_task = asyncio.create_task(backend.start())
    await stop_event.wait()
    await backend.stop()
    backend_task.cancel()
    try:
        await backend_task
    except asyncio.CancelledError:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Stella AI Backend")
    parser.add_argument("--host", default="0.0.0.0", help="WebSocket host (use 0.0.0.0 to accept connections from Android via USB/LAN)")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    args = parser.parse_args()

    logging.getLogger().setLevel(args.log_level.upper())

    logger.info("Starting Stella backend...")
    logger.info("Repo root: %s", _REPO_ROOT)

    try:
        asyncio.run(_async_main(args.host, args.port))
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    logger.info("Stella backend stopped")


if __name__ == "__main__":
    main()
