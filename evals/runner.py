"""evals/runner.py - execute the suite and record a comparable score.

Usage:
    python -m evals.runner                 # run everything
    python -m evals.runner --category files
    python -m evals.runner --task file.edit
    python -m evals.runner --compare       # diff against the stored baseline

Every run writes `evals/runs/<timestamp>.json`, and the most recent run is
copied to `evals/baseline.json`. Comparing two runs is the only honest way to
answer "did that change help".
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from evals.tasks import Task, default_suite, suite_manifest

EVALS = Path(__file__).resolve().parent
RUNS = EVALS / "runs"
BASELINE = EVALS / "baseline.json"


def _run_task(task: Task, workspace_root: Path, verbose: bool) -> dict:
    """Run one task in a private workspace and grade it."""
    from agent.integration import StellaAgent

    ws = Path(tempfile.mkdtemp(prefix=f"stella-eval-{task.id}-", dir=workspace_root))
    if task.fixture:
        task.fixture(ws)

    agent = StellaAgent(workspace=str(ws), max_turns=task.max_turns)
    backend = agent.backend.resolve()
    record: dict = {
        "task": task.id,
        "category": task.category,
        "backend": backend.name if backend else None,
        "max_turns": task.max_turns,
    }

    if backend is None:
        record.update(ok=False, passed=False, answer="", turns=0,
                      error="no LLM backend reachable", elapsed=0.0)
        shutil.rmtree(ws, ignore_errors=True)
        return record

    started = time.time()
    try:
        result = agent.run(task.goal, max_turns=task.max_turns)
        answer = result.answer or ""
        try:
            passed = bool(task.check(ws, answer))
        except Exception as exc:  # a broken checker is a suite bug, not a model failure
            passed = False
            record["checker_error"] = f"{type(exc).__name__}: {exc}"
        record.update(
            ok=result.ok,
            passed=passed,
            answer=answer[:1500],
            turns=result.turns,
            tool_calls=len(result.tool_calls),
            tools=[c["name"] for c in result.tool_calls],
            errors=result.errors[:5],
            stopped_because=result.stopped_because,
            elapsed=round(time.time() - started, 2),
        )
        if verbose:
            mark = "PASS" if passed else "FAIL"
            print(f"  [{mark}] {task.id:<28} {record['elapsed']:>6.2f}s  "
                  f"turns={record['turns']}")
    except Exception as exc:  # noqa: BLE001
        record.update(ok=False, passed=False, answer="", turns=0,
                      error=f"{type(exc).__name__}: {exc}",
                      elapsed=round(time.time() - started, 2))
        if verbose:
            print(f"  [ERR] {task.id:<28} {record['error']}")

    shutil.rmtree(ws, ignore_errors=True)
    return record


def run_suite(tasks: list[Task], verbose: bool = True) -> dict:
    RUNS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="stella-evals-") as tmp:
        records = [_run_task(t, Path(tmp), verbose) for t in tasks]

    by_cat: dict[str, dict] = {}
    for r in records:
        slot = by_cat.setdefault(r["category"], {"passed": 0, "total": 0})
        slot["total"] += 1
        slot["passed"] += 1 if r["passed"] else 0
    for slot in by_cat.values():
        slot["rate"] = round(slot["passed"] / slot["total"], 3) if slot["total"] else 0.0

    passed = sum(1 for r in records if r["passed"])
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "suite": suite_manifest(),
        "score": {
            "passed": passed,
            "total": len(records),
            "rate": round(passed / len(records), 3) if records else 0.0,
        },
        "by_category": by_cat,
        "turns_avg": round(
            sum(r.get("turns", 0) for r in records) / len(records), 2
        ) if records else 0.0,
        "elapsed_avg": round(
            sum(r.get("elapsed", 0.0) for r in records) / len(records), 2
        ) if records else 0.0,
        "results": records,
    }
    return report


def _print_summary(report: dict) -> None:
    s = report["score"]
    print()
    print("=" * 58)
    print(f"  {s['passed']}/{s['total']} passed  ({s['rate']*100:.0f}%)")
    print("=" * 58)
    for cat, stat in sorted(report["by_category"].items()):
        bar = "#" * int(stat["rate"] * 20)
        print(f"  {cat:<12} {stat['passed']}/{stat['total']}  {bar}")
    print(f"\n  avg turns   {report['turns_avg']}")
    print(f"  avg seconds {report['elapsed_avg']}")


def compare(current: dict) -> None:
    if not BASELINE.exists():
        print("No baseline yet - this run will become it.")
        return
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    b, c = base["score"], current["score"]
    delta = round(c["rate"] - b["rate"], 3)
    verb = "improved" if delta > 0 else ("REGRESSED" if delta < 0 else "unchanged")
    print()
    print(f"  baseline {b['rate']*100:.0f}%  ->  now {c['rate']*100:.0f}%   "
          f"({delta*100:+.0f}pt) {verb}")
    for cat in sorted(set(base["by_category"]) | set(current["by_category"])):
        br = base["by_category"].get(cat, {}).get("rate", 0.0)
        cr = current["by_category"].get(cat, {}).get("rate", 0.0)
        if br != cr:
            print(f"    {cat:<12} {br*100:.0f}% -> {cr*100:.0f}%")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the Stella agent eval suite.")
    ap.add_argument("--category", help="only run one category")
    ap.add_argument("--task", help="only run one task id")
    ap.add_argument("--compare", action="store_true",
                    help="diff this run against the stored baseline")
    ap.add_argument("--set-baseline", action="store_true",
                    help="store this run as the new baseline")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    tasks = default_suite()
    if args.task:
        tasks = [t for t in tasks if t.id == args.task]
    elif args.category:
        tasks = [t for t in tasks if t.category == args.category]

    if not tasks:
        print("No tasks matched.")
        return 2

    if not args.quiet:
        print(f"Running {len(tasks)} task(s) against the local runtime...\n")

    report = run_suite(tasks, verbose=not args.quiet)
    if not args.quiet:
        _print_summary(report)

    RUNS.mkdir(parents=True, exist_ok=True)
    stamp = report["timestamp"].replace(":", "").replace("-", "")[:15]
    out = RUNS / f"run-{stamp}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not args.quiet:
        print(f"\n  saved: {out.relative_to(EVALS.parent)}")

    if args.compare:
        compare(report)
    if args.set_baseline:
        shutil.copyfile(out, BASELINE)
        if not args.quiet:
            print(f"  baseline set from {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())