#!/usr/bin/env python3
"""
Overlay Georgian text onto an image using a specified TTF font.

Usage example:
  python scripts/overlay_georgian_text.py \
    --input input.png --output output.png \
    --text "ქართული ტექსტი" \
    --font /path/to/NotoSansGeorgian-Regular.ttf --size 72 --color "#ffffff"

Requires: Pillow
"""
from __future__ import annotations
import argparse
from pathlib import Path
import logging
from PIL import Image, ImageDraw, ImageFont
import os
import sys


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Overlay Georgian text on an image")
    p.add_argument("--input", required=True, help="Input image path")
    p.add_argument("--output", required=True, help="Output image path")
    p.add_argument("--text", required=False, help="Text to render (UTF-8, e.g. Georgian). Beware shell encoding on Windows; use --text-file to pass UTF-8 file.")
    p.add_argument("--text-file", required=False, help="Path to a UTF-8 text file containing the text to render. This is recommended on Windows/PowerShell to avoid encoding issues.")
    p.add_argument("--font", required=False, help="Path to a TTF font that supports Georgian (e.g. NotoSansGeorgian). If omitted, uses scripts/fonts/NotoSansGeorgian-Regular.ttf in the repo.")
    p.add_argument("--size", type=int, default=48, help="Font size in px")
    p.add_argument("--color", default="#FFFFFF", help="Text color (hex, e.g. #FFFFFF)")
    p.add_argument("--x", type=int, help="X coordinate for text origin (overrides centering)")
    p.add_argument("--y", type=int, help="Y coordinate for text origin (overrides centering)")
    p.add_argument("--anchor", choices=["lt","mm","rm","lb","rb"], default="mm", help="Anchor: lt left-top, mm center, rm right-middle, lb left-bottom, rb right-bottom")
    p.add_argument("--stroke", type=int, default=0, help="Stroke width for outline")
    return p.parse_args()


def hex_to_rgba(hexcolor: str, alpha: float = 1.0):
    hexcolor = hexcolor.lstrip("#")
    if len(hexcolor) == 3:
        hexcolor = ''.join([c*2 for c in hexcolor])
    if len(hexcolor) != 6:
        raise ValueError("Invalid hex color")
    r = int(hexcolor[0:2], 16)
    g = int(hexcolor[2:4], 16)
    b = int(hexcolor[4:6], 16)
    a = int(alpha * 255)
    return (r, g, b, a)


def main() -> int:
    args = parse_args()

    if not os.path.isfile(args.input):
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 2

    # If font not provided, require the bundled repo font path to exist (deterministic behavior)
    # Resolve repo root reliably so FastAPI or other servers with different CWDs still find the font
    BASE_DIR = Path(__file__).resolve().parents[1]  # open-webui root
    FONT_PATH = BASE_DIR / 'scripts' / 'fonts' / 'NotoSansGeorgian-Bold.ttf'

    # Startup check: require committed font to exist at the repo path
    if not FONT_PATH.exists():
        raise RuntimeError("Georgian font missing: NotoSansGeorgian-Bold.ttf")

    # Enforce deterministic font usage: always use committed Bold font (no fallbacks)
    font_path = FONT_PATH

    try:
        img = Image.open(args.input).convert("RGBA")
    except Exception as e:
        print(f"Failed to open image: {e}", file=sys.stderr)
        return 4

    draw = ImageDraw.Draw(img)

    # Debug: log which font path we will use and whether it exists (critical for FastAPI runtime)
    logging.info(f"[PY_PHOTO] Using font path: {FONT_PATH.resolve()}")
    logging.info(f"[PY_PHOTO] Font exists: {FONT_PATH.exists()}")

    # Load font without catching errors — fail hard if font cannot be loaded
    font_size = args.size

    # Attempt to load with RAQM layout engine for proper complex script (Georgian) rendering
    try:
        from PIL.ImageFont import Layout
        logging.info("[PY_PHOTO] Attempting RAQM layout engine...")
        font = ImageFont.truetype(str(FONT_PATH), font_size, layout_engine=Layout.RAQM)
        logging.info(f"[PY_PHOTO] RAQM layout engine available. Font name: {font.getname()}")
    except (AttributeError, ValueError) as e:
        # Fallback: RAQM not available, use default layout (less ideal for Georgian)
        logging.warning(f"[PY_PHOTO] RAQM not available ({e}), using default layout engine")
        font = ImageFont.truetype(str(FONT_PATH), font_size)
        logging.info(f"[PY_PHOTO] Loaded font (default layout). Font name: {font.getname()}")

    # Read text from file if provided (recommended on Windows to avoid shell encoding issues)
    if args.text_file:
        if not os.path.isfile(args.text_file):
            print(f"Text file not found: {args.text_file}", file=sys.stderr)
            return 7
        with open(args.text_file, 'r', encoding='utf-8') as f:
            text = f.read().strip()
    else:
        if not args.text:
            print("No text provided. Use --text or --text-file.", file=sys.stderr)
            return 8
        text = args.text

    # Quick heuristic: if text looks like question marks, warn about shell encoding
    if '?' in text and any(ord(c) > 127 for c in text.replace('?', '')) is False:
        print("Warning: text contains question marks — this may indicate shell encoding problems.\nConsider using --text-file with a UTF-8 encoded file or set PowerShell to UTF-8 (chcp 65001).", file=sys.stderr)

    # Use textbbox for proper width/height calculation (textsize is deprecated)
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]

    # Determine anchor position
    if args.x is not None and args.y is not None:
        x, y = args.x, args.y
    else:
        img_w, img_h = img.size
        if args.anchor == 'mm':
            x = img_w // 2
            y = img_h // 2
        elif args.anchor == 'lt':
            x = 10
            y = 10
        elif args.anchor == 'lb':
            x = 10
            y = img_h - 10 - h
        elif args.anchor == 'rm':
            x = img_w - 10 - w
            y = img_h // 2
        elif args.anchor == 'rb':
            x = img_w - 10 - w
            y = img_h - 10 - h
        else:
            x = img_w // 2
            y = img_h // 2

    # If anchor is center-ish, adjust to draw text from its center
    if args.anchor == 'mm':
        x = x - w // 2
        y = y - h // 2

    fill = hex_to_rgba(args.color)

    # Optional stroke (outline)
    if args.stroke and args.stroke > 0:
        outline_color = (0, 0, 0, fill[3])
        for dx in range(-args.stroke, args.stroke+1):
            for dy in range(-args.stroke, args.stroke+1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x+dx, y+dy), text, font=font, fill=outline_color)

    draw.text((x, y), text, font=font, fill=fill)

    try:
        img.save(args.output)
    except Exception as e:
        print(f"Failed to save output image: {e}", file=sys.stderr)
        return 6

    print(f"Saved: {args.output}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
