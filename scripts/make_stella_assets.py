#!/usr/bin/env python3
"""Generate the Stella asset pack from assets/logo.jpg (star mark).

Outputs (all under assets/stella/ unless noted):
  stella_logo.png            512px master (void background)
  stella_logo_transparent.png  512px transparent-background star
  favicon.ico                16/32/48 multi-size icon
  stella_loading.png         1024x600 splash screen
  spinner/frame_00..11.png   12-frame rotating transparent spinner (128px)
  stella_og.png              1200x630 social card
  ic_stella_launcher.png     Android launcher (192px, also copied to res/)

Re-runnable: python scripts/make_stella_assets.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "assets" / "logo.jpg"
OUT = BASE / "assets" / "stella"

VOID = (12, 13, 20)
IRIS = (124, 110, 230)
MINT = (56, 226, 184)
ALABASTER = (244, 243, 239)


def key_out_background(img: Image.Image, thresh: int = 28) -> Image.Image:
    """Knock near-black background to transparent (luminance key)."""
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r < thresh and g < thresh and b < thresh:
                px[x, y] = (r, g, b, 0)
    return img


def crop_star(img: Image.Image) -> Image.Image:
    """Trim the dark margins around the star."""
    gray = img.convert("L")
    bbox = gray.point(lambda v: 255 if v > 24 else 0).getbbox()
    if bbox:
        pad = 20
        l, t, r, b = bbox
        img = img.crop((max(0, l - pad), max(0, t - pad),
                        min(img.width, r + pad), min(img.height, b + pad)))
    return img


def text(draw: ImageDraw.ImageDraw, xy, s: str, size: int, fill, anchor="mm"):
    try:
        font = ImageFont.truetype("arial.ttf", size)
    except Exception:
        font = ImageFont.load_default()
    draw.text(xy, s, font=font, fill=fill, anchor=anchor)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "spinner").mkdir(exist_ok=True)

    src = Image.open(SRC).convert("RGB")
    star = crop_star(src)

    master = star.resize((512, 512), Image.LANCZOS)
    bg = Image.new("RGB", (512, 512), VOID)
    bg.paste(master, (0, 0), master if master.mode == "RGBA" else None)
    bg.save(OUT / "stella_logo.png")

    transparent = key_out_background(master.resize((512, 512), Image.LANCZOS))
    transparent.save(OUT / "stella_logo_transparent.png")

    master.save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])

    # Top-level aliases expected by app + installer specs
    bg.save(BASE / "assets" / "stella_logo.png")
    master.save(BASE / "assets" / "stella_logo.ico",
                sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])

    # Loading splash
    splash = Image.new("RGB", (1024, 600), VOID)
    d = ImageDraw.Draw(splash)
    logo = star.resize((280, 280), Image.LANCZOS)
    splash.paste(logo, (372, 90))
    text(d, (512, 420), "S T E L L A", 64, ALABASTER)
    text(d, (512, 480), "Built to assist. Engineered to evolve. Yours to shape.",
         22, (134, 137, 159))
    text(d, (512, 540), "loading ...", 20, IRIS)
    splash.save(OUT / "stella_loading.png")

    # Spinner frames (transparent rotating star)
    spin_src = key_out_background(star.resize((128, 128), Image.LANCZOS))
    for i in range(12):
        frame = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        rot = spin_src.rotate(-i * 30, resample=Image.BICUBIC, expand=False)
        frame.alpha_composite(rot)
        frame.save(OUT / "spinner" / f"frame_{i:02d}.png")

    # OG social card
    og = Image.new("RGB", (1200, 630), VOID)
    d = ImageDraw.Draw(og)
    logo = star.resize((300, 300), Image.LANCZOS)
    og.paste(logo, (120, 165))
    text(d, (700, 250), "STELLA", 96, ALABASTER)
    text(d, (700, 330), "Your Self-Evolving", 36, IRIS)
    text(d, (700, 375), "Autonomous Companion", 36, IRIS)
    text(d, (700, 450), "Meet Stella. The last personal assistant", 26, (134, 137, 159))
    text(d, (700, 485), "you'll ever need to train.", 26, (134, 137, 159))
    og.save(OUT / "stella_og.png")

    # Android launcher
    launcher = star.resize((192, 192), Image.LANCZOS)
    launcher.save(OUT / "ic_stella_launcher.png")
    and_res = (BASE / "stella-connect-android" / "app" / "src" / "main" /
               "res" / "drawable")
    if and_res.exists():
        launcher.save(and_res / "ic_stella_launcher.png")
        print("android launcher copied")

    print("assets written to", OUT)


if __name__ == "__main__":
    main()
