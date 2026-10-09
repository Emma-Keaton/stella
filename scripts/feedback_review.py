#!/usr/bin/env python3
"""
scripts/feedback_review.py — the human gate over anonymous update requests.

The webhook receiver (stella_connect/gateway/feedback_webhook.py) collects
suggestions into feedback/inbox/pending/. Nobody but YOU decides what ships:
list them, read one, approve (moves to approved/ for the build loop) or
reject (moves to rejected/ for the record). Run on the creator's machine.

Usage:
    python scripts/feedback_review.py list
    python scripts/feedback_review.py show <id>
    python scripts/feedback_review.py approve <id>
    python scripts/feedback_review.py reject <id> [--reason "..."]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def _dirs() -> dict[str, Path]:
    try:
        from core.user_paths import get_user_data_dir
        base = get_user_data_dir() / "feedback" / "inbox"
    except Exception:
        base = Path.home() / ".stella" / "feedback" / "inbox"
    return {k: base / k for k in ("pending", "approved", "rejected")}


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _save(p: Path, obj: dict) -> None:
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    tmp.replace(p)


def cmd_list() -> int:
    dirs = _dirs()
    items = sorted(dirs["pending"].glob("*.json"))
    if not items:
        print("Inbox empty — no pending requests.")
        return 0
    print(f"{len(items)} pending request(s):")
    for p in items:
        try:
            e = _load(p)
            r = e.get("report", {})
            app = r.get("app_version", "?")
            need = str(r.get("need", ""))[:70].replace("\n", " ")
            print(f"  {e.get('id', p.stem)}  v{app}  {need}")
        except Exception as ex:
            print(f"  {p.stem}  (unreadable: {ex})")
    return 0


def _find(rid: str) -> tuple[str, Path] | tuple[None, None]:
    dirs = _dirs()
    for status, d in dirs.items():
        p = d / f"{rid}.json"
        if p.exists():
            return status, p
    # prefix match inside pending
    cands = list(dirs["pending"].glob(f"{rid}*.json"))
    if len(cands) == 1:
        return "pending", cands[0]
    return None, None


def cmd_show(rid: str) -> int:
    status, p = _find(rid)
    if p is None:
        print(f"No request '{rid}'.", file=sys.stderr)
        return 1
    print(json.dumps(_load(p), indent=2))
    return 0


def _move(rid: str, to: str, reviewer: str, reason: str = "") -> int:
    dirs = _dirs()
    src_status, src = _find(rid)
    if src is None:
        print(f"No request '{rid}'.", file=sys.stderr)
        return 1
    if src_status == to:
        print(f"Already {to}.")
        return 0
    obj = _load(src)
    obj["status"] = to
    obj["reviewed_utc"] = datetime.now(timezone.utc).isoformat()
    obj["reviewed_by"] = reviewer
    if reason:
        obj["review_note"] = reason
    dest = dirs[to] / src.name
    _save(dest, obj)
    src.unlink(missing_ok=True)
    print(f"{obj.get('id', rid)}: {src_status} -> {to}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Review anonymous feedback requests")
    ap.add_argument("--reviewer", default="creator")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    p_show = sub.add_parser("show")
    p_show.add_argument("id")
    p_appr = sub.add_parser("approve")
    p_appr.add_argument("id")
    p_rej = sub.add_parser("reject")
    p_rej.add_argument("id")
    p_rej.add_argument("--reason", default="")
    args = ap.parse_args()
    if args.cmd == "list":
        return cmd_list()
    if args.cmd == "show":
        return cmd_show(args.id)
    if args.cmd == "approve":
        return _move(args.id, "approved", args.reviewer)
    if args.cmd == "reject":
        return _move(args.id, "rejected", args.reviewer, args.reason)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
