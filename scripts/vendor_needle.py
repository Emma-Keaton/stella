#!/usr/bin/env python3
"""Vendor the cactus-needle tool-calling runtime into Stella (copies, not links).

Needle is Apache-2.0, so vendoring is permitted provided the licence and a
notice of our changes travel with the copy. This script copies only the
runtime subset Stella actually uses - the ctypes engine, the tool-schema
builder, and the smart-object environments. The training/export/playground
modules are deliberately left out: they pull torch and hundreds of megabytes
for functionality that has nothing to do with running tools on a phone.

What we change on purpose:
  * `_telemetry.py` is replaced with a no-op. Needle phones home on every
    call unless opted out, which directly contradicts Stella's air-gapped
    offline mode. No user data leaves the device, ever.
  * `__pycache__`, `.cache`, and the tokenizer/model blobs are skipped.

Re-run this after bumping Needle; it is idempotent.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

# The upstream package root (the directory that *contains* `needle/`).
# Override with --src when the layout differs.
SRC = Path(r"E:\Projects\needle\needle_repo")
PKG = "needle"
# `vendor/` is what goes on sys.path, so the package lands at vendor/needle/.
DST = Path(__file__).resolve().parent.parent / "vendor"

# (dir under needle/, dir under DST/needle, files to copy)
COPY: list[tuple[str, str, tuple[str, ...]]] = [
    ("", "", ("__init__.py", "_worker.py")),
    ("agent", "agent", ("__init__.py", "tools.py")),
    ("environments", "environments", (
        "__init__.py", "_harness.py", "smart_home.py", "wearable.py",
        "media_player.py", "kitchen_appliance.py", "productivity.py",
        "data_capture.py",
    )),
]

NOTICE = """Stella bundles a modified copy of cactus-needle.

Upstream  : https://github.com/cactus-compute/needle
Licence   : Apache License 2.0 (see LICENSE-APACHE-2.0.txt)
Copied by : scripts/vendor_needle.py

Modifications made by Stella
----------------------------
1. needle/_telemetry.py is a deliberate no-op. Upstream reports anonymous
   usage counts to a remote endpoint on every call unless the user opts out.
   Stella ships an air-gapped offline mode, so no telemetry is collected or
   transmitted from this copy at all. `track()` is kept as a stub because
   needle/__init__.py imports it.

2. Only the runtime subset is vendored. Omitted: cli.py, mcp_server.py,
   openai_server.py, playground/, platform.py, and model/ (training, export,
   quantisation, tokenizer). Those pull torch and a tokenizer blob and are
   not needed to run tool calls.

3. No source file in this copy has been edited otherwise; the files here are
   byte-identical to upstream except where noted above.

The full unmodified upstream sources remain the authoritative reference.
"""

# A telemetry stub that keeps needle/__init__.py's `from ._telemetry import
# track as _track` import working while guaranteeing nothing is ever sent.
TELEMETRY_STUB = '''"""Telemetry stub - vendored by Stella.

Upstream needle reports anonymous usage counts over the network on every
call. Stella ships an air-gapped offline mode, so this module is a deliberate
no-op: nothing is collected, buffered, or transmitted.

Kept as a stub because needle/__init__.py does
`from ._telemetry import track as _track` at import time.
"""

from __future__ import annotations


def _enabled() -> bool:
    return False


def track(event: str, props=None) -> None:
    """No-op. Stella never phones home."""
    return


def _send(event: str, props=None) -> None:
    return
'''



def main() -> int:
    if not SRC.is_dir():
        print(f"error: needle source not found at {SRC}", file=sys.stderr)
        print("pass --src to point at a different checkout", file=sys.stderr)
        return 1

    # Idempotent: rebuild from scratch so a removed upstream file cannot linger.
    if DST.exists():
        shutil.rmtree(DST)
    (DST / PKG).mkdir(parents=True, exist_ok=True)

    copied, missing = [], []
    upstream = SRC / PKG
    for src_rel, dst_rel, names in COPY:
        src_dir = upstream / src_rel if src_rel else upstream
        dst_dir = DST / PKG / dst_rel if dst_rel else DST / PKG
        dst_dir.mkdir(parents=True, exist_ok=True)
        for name in names:
            s, d = src_dir / name, dst_dir / name
            if not s.is_file():
                missing.append(str(s.relative_to(upstream)))
                continue
            shutil.copy2(s, d)
            copied.append(str(d.relative_to(DST)))

    # Our one real modification: the telemetry no-op.
    (DST / PKG / "_telemetry.py").write_text(TELEMETRY_STUB, encoding="utf-8")
    copied.append(f"{PKG}/_telemetry.py  (replaced with no-op)")

    # Apache-2.0 requires the licence to travel with the copy.
    lic = SRC / "LICENSE"
    if lic.is_file():
        shutil.copy2(lic, DST / "LICENSE-APACHE-2.0.txt")
        copied.append("LICENSE-APACHE-2.0.txt")
    else:
        missing.append("LICENSE")

    (DST / "NOTICE.md").write_text(NOTICE, encoding="utf-8")
    copied.append("NOTICE.md")

    print(f"vendored {len(copied)} files -> {DST}")
    for f in copied:
        print(f"  {f}")
    if missing:
        print("\nwarning: not found upstream:", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
