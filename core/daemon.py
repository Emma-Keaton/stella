"""core/daemon.py - unified core daemon (HTTP + WebSocket) on port 8000."""

import asyncio
import json
import os
import signal

from aiohttp import web

PORT = int(os.environ.get("STELLA_DAEMON_PORT", "8000"))
TOKEN = os.environ.get("STELLA_DAEMON_TOKEN", "").strip()


def _auth_ok(request):
    if not TOKEN:
        return True
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):].strip() == TOKEN
    return request.query.get("token", "") == TOKEN


async def health(request):
    if not _auth_ok(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    return web.json_response({"status": "ok", "port": PORT})


async def list_tools(request):
    if not _auth_ok(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    try:
        from core.tool_registry import registry
        names = registry.list()
        err = None
    except Exception as exc:
        names = []
        err = str(exc)
    payload = {"tools": names}
    if err:
        payload["error"] = err
    return web.json_response(payload)


async def ws_handler(request):
    if not _auth_ok(request):
        raise web.HTTPUnauthorized()
    ws = web.WebSocketResponse(heartbeat=30.0)
    await ws.prepare(request)
    from core.node_protocol import validate_message, build_message
    await ws.send_str(build_message("hello", {"port": PORT}))
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    obj = validate_message(msg.data)
                except ValueError as exc:
                    await ws.send_str(build_message("error", {"error": str(exc)}))
                    continue
                await ws.send_str(build_message("ack", {"echo": obj}, request_id=obj["request_id"]))
            elif msg.type == web.WSMsgType.ERROR:
                break
    finally:
        await ws.close()
    return ws


def create_app():
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/tools", list_tools)
    app.router.add_get("/ws", ws_handler)
    return app


async def _run():
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print("[daemon] listening on http://0.0.0.0:%d" % PORT)
    stop = asyncio.get_event_loop().create_future()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            asyncio.get_event_loop().add_signal_handler(sig, stop.set_result, None)
        except NotImplementedError:
            pass
    try:
        await stop
    finally:
        await runner.cleanup()
        print("[daemon] shutdown complete")


def main():
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

import json
from aiohttp import web

PORT = 8000

async def health(request):
    return web.json_response({"status": "ok"})

async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            await ws.send_str(json.dumps({"echo": msg.data}))
    return ws

def create_app():
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/ws", ws_handler)
    return app

def main():
    app = create_app()
    web.run_app(app, port=PORT)

if __name__ == "__main__":
    main()