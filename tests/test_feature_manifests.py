"""Every feature manifest must parse. (Phase K Step 1/7b)

The skill registry loads a feature package only when its manifest is valid JSON,
and it reports the failure as a warning - so a single trailing comma silently
removes a whole skill from Stella's toolset. Three skills were lost that way
before this test existed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FEATURES_DIR = Path(__file__).resolve().parents[1] / "features"


@pytest.mark.parametrize("name", [
    "rea", "system_time", "device_cleanup", "system_monitor_ascii", "show_gif",
    "world_watch", "media_streams", "nvidia_api", "wireless_audit", "hash_cracker",
    "sound_check",
])
def test_manifest_is_valid_json(name):
    manifest_path = FEATURES_DIR / name / "manifest.json"
    assert manifest_path.exists(), f"{name}/manifest.json is missing"
    try:
        json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        pytest.fail(f"{name}/manifest.json is not valid JSON: {exc}")


def test_every_package_directory_has_a_valid_manifest():
    checked = []
    for entry in sorted(FEATURES_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith((".", "_")):
            continue
        manifest = entry / "manifest.json"
        if not manifest.exists():
            continue
        checked.append(entry.name)
        try:
            json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            pytest.fail(f"features/{entry.name}/manifest.json is not valid JSON: {exc}")
    assert "world_watch" in checked and "wireless_audit" in checked


def test_manifest_and_skill_metadata_agree():
    import importlib.util

    for entry in sorted(FEATURES_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith((".", "_")):
            continue
        manifest_path = entry / "manifest.json"
        skill_path = entry / "skill.py"
        if not manifest_path.exists() or not skill_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        spec = importlib.util.spec_from_file_location(f"stella_skill_{entry.name}", skill_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        metadata = module.FEATURE_METADATA

        assert manifest["name"] == metadata["name"], entry.name
        assert set(manifest["parameters"]["properties"]) == set(
            metadata["parameters"]["properties"]), entry.name
        assert manifest.get("surface") in ("desktop", "android", "both"), entry.name


def test_no_manifest_trailing_commas_anywhere():
    """The exact bug that cost three skills: a comma before a closing bracket.

    A closing bracket followed by a comma is only a problem when the bracket
    closes the outermost level - inside an array of arrays it is legal. The scan
    therefore tracks depth and flags a comma only at the point where the
    container itself ends.
    """
    for entry in sorted(FEATURES_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith((".", "_")):
            continue
        manifest_path = entry / "manifest.json"
        if not manifest_path.exists():
            continue
        text = manifest_path.read_text(encoding="utf-8")
        stack: list = []
        in_string = False
        escaped = False
        for index, char in enumerate(text):
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
                continue
            if char in "[{":
                stack.append(char)
                continue
            if char in "]}":
                stack.pop()
                continue
            if char == ",":
                tail = text[index + 1:index + 64].lstrip()
                if tail.startswith(("]", "}")):
                    closing = tail[0]
                    wanted = "]" if stack and stack[-1] == "[" else "}"
                    if closing != wanted:
                        context = text[max(0, index - 40):index + 8].replace("\n", "\\n")
                        pytest.fail(
                            f"{entry.name}: trailing comma before {closing}: ...{context}")
                    continue
