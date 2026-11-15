"""Generate GCAT compatibility icons from the supplied brand artwork.

Usage: python scripts/brand-assets.py (from the repository root).
"""

from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent
TARGETS = (ROOT / 'static' / 'static', ROOT / 'backend' / 'open_webui' / 'static')


def generate():
    with Image.open(SOURCE / 'gcat.png') as source:
        artwork = source.convert('RGBA')
    svg = (SOURCE / 'gcat.svg').read_text(encoding='utf-8')
    # Keep the supplied white cat visible on both light and dark surfaces.
    svg = svg.replace('<title id="title">Cat icon</title>', '<title id="title">GCAT</title>')
    svg = svg.replace(
        '  <g fill="#FFFFFF">', '  <rect width="440" height="456" rx="88" fill="#111111"/>\n  <g fill="#FFFFFF">', 1
    )
    sizes = {
        'favicon.png': 512,
        'gcat.png': 512,
        'favicon-96x96.png': 96,
        'apple-touch-icon.png': 180,
        'web-app-manifest-192x192.png': 192,
        'web-app-manifest-512x512.png': 512,
        'logo.png': 512,
        'splash.png': 512,
        'splash-dark.png': 512,
    }
    for target in TARGETS:
        target.mkdir(parents=True, exist_ok=True)
        (target / 'THIRD_PARTY_LICENSE.txt').write_bytes((ROOT / 'LICENSE').read_bytes())
        (target / 'gcat.svg').write_text(svg, encoding='utf-8')
        (target / 'favicon.svg').write_text(svg, encoding='utf-8')
        for name, size in sizes.items():
            # 20% safe inset also keeps maskable launcher icons within the safe zone.
            icon = Image.new('RGBA', (size, size), '#111111')
            cat = artwork.copy()
            cat.thumbnail((round(size * 0.8), round(size * 0.8)), Image.Resampling.LANCZOS)
            icon.alpha_composite(cat, ((size - cat.width) // 2, (size - cat.height) // 2))
            temporary = target / f'{name}.tmp'
            icon.save(temporary, format='PNG')
            temporary.replace(target / name)
        with Image.open(target / 'favicon.png') as favicon:
            favicon.save(target / 'favicon.ico', sizes=[(16, 16), (32, 32), (48, 48)])
    (ROOT / 'static' / 'favicon.png').write_bytes((TARGETS[0] / 'favicon.png').read_bytes())


if __name__ == '__main__':
    generate()
