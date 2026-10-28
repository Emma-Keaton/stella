"""Step 7b/7c tests: wireless audit, hash cracker, skill surfaces, sound check."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_skill(name: str):
    path = REPO_ROOT / "features" / name / "skill.py"
    spec = importlib.util.spec_from_file_location(f"stella_skill_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def wireless():
    return _load_skill("wireless_audit")


@pytest.fixture()
def cracker():
    return _load_skill("hash_cracker")


@pytest.fixture()
def sound():
    return _load_skill("sound_check")


# --------------------------------------------------------------------- registry

@pytest.mark.parametrize("name", ["wireless_audit", "hash_cracker", "sound_check"])
def test_new_skills_are_discovered(name):
    from core.dynamic_registry import DynamicToolRegistry

    registry = DynamicToolRegistry()
    registry.initialize()
    names = [s.get("name") if isinstance(s, dict) else str(s) for s in registry.list_skills()]
    assert name in names


@pytest.mark.parametrize("name", ["wireless_audit", "hash_cracker", "sound_check"])
def test_manifests_are_valid_and_match_metadata(name):
    manifest = json.loads((REPO_ROOT / "features" / name / "manifest.json").read_text(encoding="utf-8"))
    skill = _load_skill(name)
    assert manifest["name"] == skill.FEATURE_METADATA["name"]
    assert set(manifest["parameters"]["properties"]) == set(
        skill.FEATURE_METADATA["parameters"]["properties"])
    assert manifest["surface"] in ("desktop", "android", "both")
    assert isinstance(manifest.get("requires", []), list)


def test_media_streams_surface_is_both():
    manifest = json.loads((REPO_ROOT / "features" / "media_streams" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["surface"] == "both"


# --------------------------------------------------------------- wireless audit

def test_wireless_read_only_operations_run_without_authorisation(wireless):
    for operation in ("tools", "interfaces", "monitor", "survey", "sources"):
        result = wireless.execute(operation=operation)
        assert "summary" in result
        assert isinstance(result["summary"], str)
        assert result["summary"], f"{operation} produced no summary"


def test_wireless_capture_is_refused_without_authorisation(wireless):
    result = wireless.execute(operation="capture_handshake", interface="wlan0",
                              bssid="aa:bb:cc:dd:ee:ff")
    assert result["ok"] is False
    assert "authorized" in result["record"]["error"]
    assert "confirm" in result["record"]["error"]


def test_wireless_capture_requires_a_bssid(wireless):
    result = wireless.execute(operation="capture_handshake", interface="wlan0",
                              authorized=True, confirm=True)
    assert result["ok"] is False
    assert "bssid" in result["record"]["error"]


def test_wireless_deauth_refuses_without_a_named_client(wireless):
    result = wireless.execute(operation="deauth", interface="wlan0", authorized=True, confirm=True)
    assert result["ok"] is False
    assert "client" in result["record"]["error"]


def test_wireless_rogue_ap_needs_an_essid_and_its_own_gate(wireless):
    result = wireless.execute(operation="rogue_ap", authorized=True, confirm=True)
    assert result["ok"] is False
    assert "essid" in result["record"]["error"]


def test_wireless_rogue_ap_names_the_interactive_tools(wireless, monkeypatch):
    from core.security import tools as tools_module

    monkeypatch.setattr(tools_module, "available",
                        lambda names=None: {name: {"present": True, "path": f"/usr/bin/{name}"}
                                            for name in (names or tools_module.INSTALL_HINTS)})
    result = wireless.execute(operation="rogue_ap", essid="Free Guest WiFi",
                              authorized=True, confirm=True)
    assert result["ok"] is False
    assert "airgeddon" in result["record"]["error"] or "interactive" in result["record"]["error"]


def test_wireless_capture_starts_a_tool_when_authorised(wireless, monkeypatch):
    from core.security import tools as tools_module

    monkeypatch.setattr(tools_module, "available", lambda names=None: {
        name: {"present": True, "path": f"/usr/bin/{name}"}
        for name in (names or ["airodump-ng"])})
    started = {"ok": True, "outcome": "started", "pid": 4242, "reason": "airodump-ng started"}
    monkeypatch.setattr(tools_module, "run_background", lambda argv, log: started)

    result = wireless.execute(operation="capture_handshake", interface="wlan0",
                              bssid="aa:bb:cc:dd:ee:ff", essid="Test",
                              authorized=True, confirm=True, duration_seconds="30")
    assert result["ok"] is True
    value = result["record"]["value"]
    assert value["outcome"] == "started"
    assert value["tool"] == "airodump-ng"
    assert value["duration_seconds"] == 30
    assert value["target"] == "aa:bb:cc:dd:ee:ff,Test,wlan0"


def test_wireless_capture_reports_a_missing_tool(wireless, monkeypatch):
    from core.security import tools as tools_module

    monkeypatch.setattr(tools_module, "available", lambda names=None: {
        name: {"present": False, "path": None, "install": f"install {name}"} for name in
        (names or ["airodump-ng", "wifite", "bettercap"])})
    result = wireless.execute(operation="capture_handshake", interface="wlan0",
                              bssid="aa:bb:cc:dd:ee:ff", authorized=True, confirm=True)
    assert result["ok"] is False
    assert "no capture tool is installed" in result["record"]["error"]
    assert "airodump-ng" in result["record"]["error"]


def test_wireless_unknown_operation_is_refused(wireless):
    result = wireless.execute(operation="jam_spectrum")
    assert result["ok"] is False
    assert "Unknown operation" in result["record"]["error"]


# ------------------------------------------------------------------ hash cracker

def test_identify_names_a_known_hash_shape(cracker):
    result = cracker.execute(operation="identify", hash="5f4dcc3b5aa765d61d8327deb882cf99")
    assert result["ok"] is True
    assert "MD5" in result["record"]["value"]["hash_type"] or "NTLM" in result["record"]["value"]["hash_type"]


def test_identify_reports_an_unknown_shape_honestly(cracker):
    result = cracker.execute(operation="identify", hash="zzz-not-a-hash")
    assert result["ok"] is False
    assert "not one the identifier knows" in result["record"]["error"]


def test_crack_requires_confirmation(cracker):
    result = cracker.execute(operation="crack", hash_file="C:/tmp/hashes.hc22000")
    assert result["ok"] is False
    assert "confirm" in result["record"]["error"]


def test_convert_needs_a_file(cracker):
    result = cracker.execute(operation="convert")
    assert result["ok"] is False
    assert "capture" in result["record"]["error"]


def test_crack_starts_with_hashcat_when_installed(cracker, monkeypatch):
    from core.security import hashcat as hashcat_module

    monkeypatch.setattr(hashcat_module, "tools", lambda names=None: {
        "hashcat": {"present": True, "path": "/usr/bin/hashcat"},
        "john": {"present": True, "path": "/usr/bin/john"},
    })

    started = {"ok": True, "outcome": "started", "pid": 99}

    def fake_start_crack(*args, **kwargs):
        return {**started,
                "hash_file": kwargs.get("hash_file") or (args[0] if args else "?"),
                "mode": kwargs.get("mode") or (args[1] if len(args) > 1 else "22000"),
                "wordlist": kwargs.get("wordlist") or "/usr/share/wordlists/rockyou.txt",
                "cracked_file": "C:/tmp/a.cracked.txt"}

    monkeypatch.setattr(hashcat_module, "start_crack", fake_start_crack)

    result = cracker.execute(operation="crack", hash_file="C:/tmp/a.hc22000",
                             wordlist="/usr/share/wordlists/rockyou.txt", confirm=True)
    assert result["ok"] is True
    value = result["record"]["value"]
    assert value["outcome"] == "started"
    assert value["mode"] == "22000"
    assert "started, not done" in result["summary"]


def test_crack_reports_a_missing_binary(cracker, monkeypatch):
    from core.security import hashcat as hashcat_module

    monkeypatch.setattr(hashcat_module, "tools", lambda names=None: {
        "hashcat": {"present": False, "path": None, "install": "apt install hashcat"},
        "john": {"present": False, "path": None, "install": "apt install john"},
    })
    monkeypatch.setattr(hashcat_module, "start_crack",
                        lambda *a, **kw: {"ok": False, "outcome": "failed",
                                          "reason": "hashcat is not installed on this machine (apt install hashcat). Nothing was run."})
    result = cracker.execute(operation="crack", hash_file="C:/tmp/a.hc22000", confirm=True)
    assert result["ok"] is False
    assert "hashcat" in result["record"]["error"]


def test_wordlists_reports_what_this_machine_has(cracker):
    result = cracker.execute(operation="wordlists")
    assert result["ok"] is True
    assert "wordlists" in result["record"]["value"]


# ----------------------------------------------------------------- skill surfaces

def test_surface_report_covers_every_skill():
    from core.skill_surfaces import skill_surfaces

    report = skill_surfaces()
    assert report["ok"] is True
    names = {skill["name"] for skill in report["skills"]}
    for expected in ("world_watch", "media_streams", "wireless_audit", "hash_cracker",
                     "sound_check", "nvidia_api"):
        assert expected in names, f"{expected} is missing from the surface report"


def test_every_skill_surface_is_declared():
    from core.skill_surfaces import skill_surfaces

    report = skill_surfaces()
    for skill in report["skills"]:
        assert skill["surface"] in ("desktop", "android", "both"), skill["name"]
        assert isinstance(skill["required"], list)
        assert isinstance(skill["missing"], list)


def test_a_skill_with_an_unmet_requirement_is_not_available(cracker, monkeypatch):
    from core.skill_surfaces import _unmet, skill_surfaces

    report = skill_surfaces()
    probe = report["probe"]
    for capability in list(probe["binaries"]):
        probe["binaries"][capability]["available"] = False
        probe["binaries"][capability]["present"] = []
    for capability in list(probe["modules"]):
        probe["modules"][capability]["present"] = False
    for capability in list(probe["keys"]):
        probe["keys"][capability]["configured"] = False

    missing = _unmet(["wireless_tools"], probe)
    assert missing and missing[0]["kind"] == "binary"
    assert "install one of" in missing[0]["fix"]

    module_missing = _unmet(["charts"], probe)
    assert module_missing[0]["kind"] == "module"
    assert "pip install" in module_missing[0]["fix"]


def test_android_skills_exclude_desktop_only_skills():
    from core.skill_surfaces import android_skills

    names = {skill["name"] for skill in android_skills()}
    assert "media_streams" in names
    assert "world_watch" in names


# ------------------------------------------------------------------ sound check

def test_sound_check_operations_are_reachable(sound):
    for operation in ("devices", "tone", "diagnosis"):
        result = sound.execute(operation=operation)
        assert "summary" in result
        assert isinstance(result["summary"], str)


def test_sound_check_volume_requires_a_level(sound):
    result = sound.execute(operation="volume")
    assert result["ok"] is False
    assert "percentage" in result["record"]["error"]


def test_sound_check_volume_is_read_back(sound, monkeypatch):
    from core.media import volume as volume_module

    monkeypatch.setattr(volume_module, "set_volume",
                        lambda level, device: {"outcome": "done",
                                               "detail": f"Volume is {level}% on Speakers."})
    monkeypatch.setattr(volume_module, "get_volume", lambda device: 42)
    result = sound.execute(operation="volume", volume=42)
    assert result["ok"] is True
    value = result["record"]["value"]
    assert value["requested"] == 42
    assert value["read_back"] == 42
    assert "Speakers" in result["summary"]


def test_sound_check_meter_reports_silence_honestly(sound, monkeypatch):
    import sys

    fake_np = type("np", (), {
        "abs": staticmethod(lambda values: [abs(v) for v in values]),
        "max": staticmethod(lambda values: max(values) if values else 0.0),
        "sqrt": staticmethod(lambda value: value ** 0.5),
        "mean": staticmethod(lambda values: sum(values) / len(values) if values else 0.0),
        "log10": staticmethod(lambda value: value),
        "power": staticmethod(lambda values, exponent: [v ** exponent for v in values]),
    })

    class FakeRecording(list):
        @property
        def size(self):
            return len(self)

    class FakeSD:
        @staticmethod
        def rec(*args, **kwargs):
            return FakeRecording([0.0] * 10)

        @staticmethod
        def wait():
            return None

    monkeypatch.setitem(sys.modules, "numpy", fake_np)
    monkeypatch.setitem(sys.modules, "sounddevice", FakeSD)

    result = sound.execute(operation="meter", seconds="1")
    assert result["ok"] is True, result["record"]["error"]
    value = result["record"]["value"]
    assert value["verdict"] == "silence"
    assert "muted microphone" in value["note"]


def test_sound_check_unknown_operation(sound):
    result = sound.execute(operation="echo_cancel")
    assert result["ok"] is False
    assert "Unknown operation" in result["record"]["error"]


# ---------------------------------------------------------- volume read-back unit

def test_volume_module_reads_back_what_it_set():
    from core.media import volume

    backend = volume.backend()
    if backend == "none":
        pytest.skip(f"no volume backend on this machine ({backend})")
    current = volume.get_volume("")
    assert current is None or 0 <= current <= 100

    result = volume.set_volume(current if current is not None else 50)
    assert result["outcome"] in ("done", "unverified")
    assert "Volume" in result["detail"]


def test_volume_module_reports_a_backend_by_name():
    from core.media import volume

    assert volume.backend() in ("windows-core-audio", "macos-applescript",
                               "pulseaudio-pactl", "alsa-amixer", "none")
