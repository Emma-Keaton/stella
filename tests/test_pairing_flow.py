"""Tests for the shared, symmetric pairing model (stella_connect.pairing_flow).

The three pairing methods must all resolve to the same ``PairingTarget`` so the
desktop, the mobile app and the public edition behave identically no matter how
a peer was found.
"""

from __future__ import annotations

import json

import pytest

from stella_connect import pairing_flow as pf


def test_all_three_methods_resolve_to_the_same_target():
    qr = pf.from_qr(json.dumps({
        "stella": 1, "host": "192.168.1.20", "port": 8765,
        "pairing_token": "tok", "pairing_code": "123456", "name": "Studio PC",
    }))
    manual = pf.manual("192.168.1.20:8765", pairing_code="123456")
    assert (qr.host, qr.port) == (manual.host, manual.port) == ("192.168.1.20", 8765)
    assert qr.ws_url == manual.ws_url == "ws://192.168.1.20:8765/ws"
    assert qr.method == pf.METHOD_QR
    assert manual.method == pf.METHOD_MANUAL


def test_qr_round_trips_through_the_offer_shape():
    offer = {
        "service": "_STELLA._tcp.local.", "host": "10.0.0.7", "port": 8765,
        "pairing_token": "abc", "pairing_code": "654321", "expires": 300,
    }
    payload = pf.to_qr_payload(offer, name="Desk", platform="desktop")
    target = pf.from_qr(pf.qr_text(payload))
    assert target.host == "10.0.0.7"
    assert target.port == 8765
    assert target.pairing_code == "654321"
    assert target.pairing_token == "abc"
    assert target.platform == "desktop"


def test_newer_payload_version_is_refused():
    with pytest.raises(pf.PairingError):
        pf.from_qr(json.dumps({"stella": 999, "host": "1.2.3.4"}))


def test_garbage_qr_is_refused():
    with pytest.raises(pf.PairingError):
        pf.from_qr("definitely not json")


def test_manual_accepts_plain_host_and_hostport():
    assert pf.manual("192.168.0.5").port == pf.DEFAULT_PORT
    assert pf.manual("192.168.0.5:9000").port == 9000
    with pytest.raises(pf.PairingError):
        pf.manual("   ")


def test_discover_uses_injected_browser():
    class FakeBrowser(pf.HostBrowser):
        def browse(self, timeout):
            return [
                {"name": "Laptop", "host": "192.168.1.9", "port": 8765, "platform": "desktop"},
                {"name": "no address", "host": "", "port": 8765},
            ]

    targets = pf.discover(browser=FakeBrowser())
    assert len(targets) == 1
    assert targets[0].host == "192.168.1.9"
    assert targets[0].method == pf.METHOD_DISCOVER


def test_local_addresses_returns_a_list():
    addrs = pf.local_addresses()
    assert isinstance(addrs, list)


def test_qr_png_is_optional_dependency():
    png = pf.encode_qr_png({"stella": 1, "host": "1.2.3.4", "port": 8765})
    assert png is None or png[:8] == b"\x89PNG\r\n\x1a\n"
