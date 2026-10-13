"""Integration tests for the outbound pairing client.

A tiny in-process websocket server speaks just enough of the Stella protocol to
prove that QR / discovery / manual all funnel through the same handshake and
produce the same credentials.
"""

from __future__ import annotations

import json
import threading

import pytest

from stella_connect import pairing_flow as pf
from stella_connect import joiner


def _serve_once(handler, ready: threading.Event, result: dict):
    from websockets.sync.server import serve

    with serve(handler, "127.0.0.1", 0) as server:
        port = server.socket.getsockname()[1]
        result["port"] = port
        ready.set()
        server.serve_forever()


def _host_handler(ws):
    from stella_connect.gateway.protocol import ProtocolTypes, build_message

    for raw in ws:
        msg = json.loads(raw)
        mtype = str(msg.get("type", "")).lower()
        if mtype == ProtocolTypes.PAIR_REQUEST:
            ws.send(json.dumps(build_message(
                ProtocolTypes.PAIR_APPROVED,
                {"device": {"device_id": "dev-1", "name": "Host PC", "platform": "desktop"},
                 "device_secret": "s3cret"},
                request_id=msg["request_id"],
            )))
        elif mtype == ProtocolTypes.AUTHENTICATE:
            ws.send(json.dumps(build_message(
                ProtocolTypes.DEVICE_ONLINE,
                {"device": {"device_id": "dev-1"}}, request_id=msg["request_id"],
            )))
            ws.send(json.dumps(build_message(
                ProtocolTypes.CAPABILITIES,
                {"device_id": "dev-1", "capabilities": ["chat", "files"]},
                request_id=msg["request_id"],
            )))


@pytest.fixture()
def live_host():
    ready = threading.Event()
    result: dict = {}
    thread = threading.Thread(target=_serve_once, args=(_host_handler, ready, result), daemon=True)
    thread.start()
    if not ready.wait(10):
        pytest.skip("could not start local test server")
    yield result["port"]
    # server thread is a daemon; process exit cleans it up


def _target_for(port: int, **kw):
    return pf.PairingTarget(host="127.0.0.1", port=port, **kw)


def test_qr_manual_and_discover_all_pair_identically(live_host):
    port = live_host
    qr = pf.from_qr(json.dumps({"stella": 1, "host": "127.0.0.1", "port": port,
                                "pairing_token": "tok", "pairing_code": "111111"}))
    manual = pf.manual(f"127.0.0.1:{port}", pairing_code="111111")

    class FakeBrowser(pf.HostBrowser):
        def browse(self, timeout):
            return [{"host": "127.0.0.1", "port": port, "name": "Host PC"}]

    discovered = pf.discover(browser=FakeBrowser())[0]

    results = [joiner.join(t, {"name": "Peer", "platform": "desktop"})
               for t in (qr, manual, discovered)]
    for res in results:
        assert res.success is True, res.error
        assert res.device["device_id"] == "dev-1"
        assert res.device_secret == "s3cret"
        assert res.capabilities == ["chat", "files"]


def test_join_reports_unreachable_host():
    res = joiner.join({"host": "127.0.0.1", "port": 1})
    assert res.success is False
    assert res.error_code == "UNREACHABLE"


def test_join_rejects_missing_host():
    res = joiner.join({"host": "", "port": 8765})
    assert res.success is False
    assert res.error_code == "BAD_TARGET"
