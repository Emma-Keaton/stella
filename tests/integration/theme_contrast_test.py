"""WCAG contrast + completeness validation for themes.json.

Run: python scripts/theme_contrast_test.py
Exit 0 = all themes pass. Exit 1 = violations (printed).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEMES = ROOT / "themes.json"

# (fg_token, bg_token, min_ratio, role)
BODY, UI = 4.5, 3.0
PAIRS = [
    ("text-primary", "bg", BODY, "body"),
    ("text-primary", "surface", BODY, "body"),
    ("text-primary", "surface-raised", BODY, "body"),
    ("text-secondary", "bg", BODY, "body"),
    ("text-secondary", "surface", BODY, "body"),
    ("text-secondary", "surface-raised", BODY, "body"),
    ("text-muted", "bg", BODY, "body"),
    ("text-muted", "surface", BODY, "body"),
    ("text-muted", "surface-raised", BODY, "body"),
    ("text-primary", "bubble-user", BODY, "body"),
    ("text-primary", "bubble-stella", BODY, "body"),
    ("bubble-user-text", "bubble-user", BODY, "body"),
    ("bubble-stella-text", "bubble-stella", BODY, "body"),
    ("on-primary", "primary", BODY, "body"),
    ("on-secondary", "secondary", BODY, "body"),
    ("on-tertiary", "tertiary", BODY, "body"),
    ("on-success", "success", BODY, "body"),
    ("on-warning", "warning", BODY, "body"),
    ("on-error", "error", BODY, "body"),
    ("button-content", "primary", BODY, "body"),
    ("primary", "bg", UI, "ui"),
    ("secondary", "bg", UI, "ui"),
    ("tertiary", "bg", UI, "ui"),
    ("success", "bg", UI, "ui"),
    ("warning", "bg", UI, "ui"),
    ("error", "bg", UI, "ui"),
    ("focus-ring", "bg", UI, "ui"),
    ("border-strong", "bg", UI, "ui"),
]

HEX_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
RGBA_RE = re.compile(
    r"rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)(?:[\s,/]+([\d.]+))?\s*\)"
)


def parse_color(value: str) -> tuple[float, float, float, float] | None:
    """Return (r, g, b, a) with channels 0-255 and a 0-1. None = not a color."""
    if value is None:
        return None
    v = value.strip()
    if v.lower() == "none":
        return None
    m = HEX_RE.match(v)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) == 8:
            return (
                int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16),
                int(h[6:8], 16) / 255.0,
            )
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0
    m = RGBA_RE.match(v)
    if m:
        r, g, b = float(m.group(1)), float(m.group(2)), float(m.group(3))
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        return r, g, b, a if a <= 1.0 else a / 255.0
    return None


def _lin(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple[float, float, float]) -> float:
    r, g, b = rgb
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(fg: tuple[float, float, float, float],
             bg: tuple[float, float, float, float]) -> float:
    """WCAG contrast, compositing fg alpha over bg first."""
    fa = fg[3]
    comp = tuple(fg[i] * fa + bg[i] * (1 - fa) for i in range(3))
    l1, l2 = luminance(comp), luminance(bg[:3])
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def main() -> int:
    data = json.loads(THEMES.read_text(encoding="utf-8"))
    required = data["tokens"]
    themes = data["themes"]
    failures: list[str] = []
    notes: list[str] = []

    ids = [t["id"] for t in themes]
    if len(set(ids)) != len(ids):
        failures.append(f"duplicate theme ids: {ids}")

    for t in themes:
        tid, toks = t["id"], t.get("tokens", {})
        missing = [k for k in required if k not in toks]
        if missing:
            failures.append(f"[{tid}] missing tokens: {missing}")
            continue
        extra = [k for k in toks if k not in required]
        if extra:
            notes.append(f"[{tid}] extra tokens (ignored): {extra}")

        parsed: dict[str, tuple | None] = {}
        for k, v in toks.items():
            c = parse_color(v) if not isinstance(v, str) or k not in ("glow", "elevation-shadow") else None
            if k in ("glow", "elevation-shadow"):
                continue
            if c is None:
                failures.append(f"[{tid}] token '{k}' is not a color: {v!r}")
            parsed[k] = c

        mode = t.get("mode")
        if mode == "light" and toks.get("glow") not in (None, "", "none"):
            failures.append(f"[{tid}] light theme must not define a glow")
        if mode == "dark" and toks.get("glow") in (None, "", "none"):
            notes.append(f"[{tid}] dark theme glow is 'none' (allowed)")

        for fg_k, bg_k, minimum, role in PAIRS:
            fg, bg = parsed.get(fg_k), parsed.get(bg_k)
            if not fg or not bg:
                continue
            ratio = contrast(fg, bg)
            if ratio < minimum:
                failures.append(
                    f"[{tid}] {role} contrast {fg_k}({ratio:.2f}) on "
                    f"{bg_k} < {minimum}:1"
                )

    for n in notes:
        print(f"note: {n}")
    if failures:
        print(f"\nFAIL — {len(failures)} violation(s):")
        for f in failures:
            print(f"  x {f}")
        return 1
    print(f"PASS — {len(themes)} themes × {len(required)} tokens, "
          f"{len(PAIRS)} contrast pairs each")
    return 0


if __name__ == "__main__":
    sys.exit(main())
