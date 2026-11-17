#!/usr/bin/env python3
"""Generate placeholder Nebulon AI branding assets (PNG/ICO/SVG)."""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

NAVY = (0x0B, 0x1E, 0x3F, 255)
CYAN = (0x22, 0xD3, 0xEE, 255)
WHITE = (255, 255, 255, 255)

SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="Nebulon AI">
  <rect width="64" height="64" rx="12" fill="#0B1E3F"/>
  <text x="32" y="46" text-anchor="middle" font-family="system-ui,Segoe UI,Helvetica,Arial,sans-serif"
    font-size="40" font-weight="700" fill="#22D3EE">N</text>
</svg>
"""

SPLASH_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 120" role="img" aria-label="Nebulon AI">
  <rect width="320" height="120" fill="transparent"/>
  <text x="160" y="78" text-anchor="middle" font-family="system-ui,Segoe UI,Helvetica,Arial,sans-serif"
    font-size="56" font-weight="700" fill="{fill}">Nebulon AI</text>
</svg>
"""


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', crc)


def render_icon(size: int) -> bytes:
    """Simple raster: navy square with cyan N (no font deps)."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new('RGBA', (size, size), NAVY)
    draw = ImageDraw.Draw(img)
    font_size = int(size * 0.62)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', font_size)
    except OSError:
        font = ImageFont.load_default()
    text = 'N'
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) // 2 - bbox[0]
    y = (size - th) // 2 - bbox[1]
    draw.text((x, y), text, fill=CYAN, font=font)

    raw = img.tobytes()
    stride = size * 4
    filtered = b''.join(bytes([0]) + raw[i : i + stride] for i in range(0, len(raw), stride))
    compressed = zlib.compress(filtered, 9)
    ihdr = struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)
    return (
        b'\x89PNG\r\n\x1a\n'
        + _png_chunk(b'IHDR', ihdr)
        + _png_chunk(b'IDAT', compressed)
        + _png_chunk(b'IEND', b'')
    )


def write_ico(path: Path, png_data: bytes) -> None:
    # Minimal single-embedded-PNG ICO
    header = struct.pack('<HHH', 0, 1, 1)
    entry = struct.pack('<BBBBHHII', 32, 32, 0, 0, 1, 32, len(png_data), 22)
    path.write_bytes(header + entry + png_data)


def splash_png(width: int, height: int, dark: bool) -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    bg = (0, 0, 0, 0) if not dark else (0, 0, 0, 0)
    fill = (34, 211, 238, 255) if dark else (11, 30, 63, 255)
    img = Image.new('RGBA', (width, height), bg)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 42)
    except OSError:
        font = ImageFont.load_default()
    text = 'Nebulon AI'
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (width - tw) // 2 - bbox[0]
    y = (height - th) // 2 - bbox[1]
    draw.text((x, y), text, fill=fill, font=font)
    img.save(path := Path('/tmp/_splash_tmp.png'))
    return path.read_bytes()


def asset_targets() -> list[Path]:
    names = [
        'favicon.png',
        'favicon-96x96.png',
        'favicon.ico',
        'favicon.svg',
        'logo.png',
        'splash.png',
        'splash-dark.png',
        'apple-touch-icon.png',
        'web-app-manifest-192x192.png',
        'web-app-manifest-512x512.png',
    ]
    dirs = [
        Path('static'),
        Path('static/static'),
        Path('backend/open_webui/static'),
    ]
    out: list[Path] = []
    for d in dirs:
        for n in names:
            out.append(d / n)
    return out


def main() -> None:
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        import subprocess

        subprocess.check_call(['pip', 'install', '-q', 'pillow'])
        from PIL import Image  # noqa: F401

    sizes = {
        'favicon.png': 32,
        'favicon-96x96.png': 96,
        'logo.png': 512,
        'apple-touch-icon.png': 180,
        'web-app-manifest-192x192.png': 192,
        'web-app-manifest-512x512.png': 512,
    }
    png_by_size: dict[int, bytes] = {}

    for path in asset_targets():
        path.parent.mkdir(parents=True, exist_ok=True)
        name = path.name
        if name == 'favicon.svg':
            path.write_text(SVG, encoding='utf-8')
        elif name == 'favicon.ico':
            if 32 not in png_by_size:
                png_by_size[32] = render_icon(32)
            write_ico(path, png_by_size[32])
        elif name == 'splash.png':
            path.write_bytes(splash_png(640, 200, dark=False))
        elif name == 'splash-dark.png':
            path.write_bytes(splash_png(640, 200, dark=True))
        elif name in sizes:
            sz = sizes[name]
            if sz not in png_by_size:
                png_by_size[sz] = render_icon(sz)
            path.write_bytes(png_by_size[sz])
        else:
            if 96 not in png_by_size:
                png_by_size[96] = render_icon(96)
            path.write_bytes(png_by_size[96])

    print(f'Wrote branding assets to {len(set(p.parent for p in asset_targets()))} directories')


if __name__ == '__main__':
    main()