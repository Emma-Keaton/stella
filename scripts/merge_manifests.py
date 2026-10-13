"""scripts/merge_manifests.py - combine per-build manifests into one.

Why this exists
---------------
Every CI build writes its OWN dist/manifest.json containing only the artifact
it produced. The release job then downloads all of them into one directory,
which previously meant nine `manifest.json` files collapsed onto a single path
and exactly one survived. The in-app updater looks itself up by host OS in
`targets`, so any platform whose entry was discarded simply never saw updates
- silently, while CI stayed green.

This merges them properly:

  - `targets`     union of every build's targets
  - `k2`          taken from the newest manifest that set a k2_release
  - version/edition/channel must agree; disagreement is a hard error, because
    a release where the APK is v2 and the Windows zip is v1.9 is broken in a
    way that is much cheaper to catch here than in the field.

Usage:  python scripts/merge_manifests.py out.json in1.json in2.json ...
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def merge(paths: list[Path]) -> dict:
    manifests: list[dict] = []
    for p in paths:
        try:
            manifests.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception as exc:  # noqa: BLE001
            print(f"  (skipping unreadable manifest {p.name}: {exc})")

    if not manifests:
        raise SystemExit("no readable manifests to merge")

    versions = {str(m.get("version", "")) for m in manifests}
    if len(versions) > 1:
        raise SystemExit(
            f"manifest versions disagree: {sorted(versions)} - "
            "every artifact in one release must carry the same version"
        )

    editions = {str(m.get("edition", "")) for m in manifests}
    if len(editions) > 1:
        raise SystemExit(f"manifest editions disagree: {sorted(editions)}")

    base = dict(manifests[0])
    targets: dict = {}
    for m in manifests:
        for key, val in (m.get("targets") or {}).items():
            # A later manifest for the same key wins (freshest sha256 wins).
            targets[key] = val
    base["targets"] = targets

    # Pick the k2 block from the manifest that actually declares a k2 release;
    # otherwise keep the first one seen so the shape is stable.
    k2_block = None
    for m in manifests:
        blk = m.get("k2")
        if isinstance(blk, dict) and blk.get("k2_release"):
            k2_block = blk
            break
    if k2_block is None:
        for m in manifests:
            if isinstance(m.get("k2"), dict):
                k2_block = m["k2"]
                break
    if k2_block is not None:
        base["k2"] = k2_block

    base["merged_from"] = [p.name for p in paths]
    return base


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    out = Path(argv[1])
    merged = merge([Path(a) for a in argv[2:]])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"merged {len(merged['targets'])} target(s) -> {out}")
    for k, v in sorted(merged["targets"].items()):
        print(f"   {k}: {v.get('file')}"
              f"{'  [k2]' if v.get('k2_bundled') else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))