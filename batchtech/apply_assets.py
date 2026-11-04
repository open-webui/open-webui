"""Regenerate BatchTechUI icons/splash from batchtech/assets/BT_mark.png (square mark)."""

import base64, io
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parent.parent
mark = Image.open(root / 'batchtech/assets/BT_mark.png').convert('RGBA')
mark = mark.crop(mark.getbbox())


def square(size, pad=0.12, bg=None):
    canvas = Image.new('RGBA', (size, size), bg or (0, 0, 0, 0))
    inner = int(size * (1 - 2 * pad))
    m = mark.copy()
    m.thumbnail((inner, inner), Image.LANCZOS)
    canvas.alpha_composite(m, ((size - m.width) // 2, (size - m.height) // 2))
    return canvas


out = {
    'static/favicon.png': square(512),
    'static/static/favicon.png': square(512),
    'static/static/favicon-96x96.png': square(96, 0.06),
    'static/static/apple-touch-icon.png': square(180, 0.12, (255, 255, 255, 255)),
    'static/static/logo.png': square(500),
    'static/static/splash.png': square(500),
    'static/static/splash-dark.png': square(500),
    'static/static/web-app-manifest-192x192.png': square(192, 0.18, (255, 255, 255, 255)),
    'static/static/web-app-manifest-512x512.png': square(512, 0.18, (255, 255, 255, 255)),
}
for rel, im in out.items():
    im.save(root / rel)
square(32, 0.04).save(root / 'static/static/favicon.ico', sizes=[(32, 32)])
buf = io.BytesIO()
square(500).save(buf, 'PNG')
b64 = base64.b64encode(buf.getvalue()).decode()
(root / 'static/static/favicon.svg').write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="500" height="500" '
    f'viewBox="0 0 500 500"><image width="500" height="500" xlink:href="data:image/png;base64,{b64}"/></svg>'
)
print('assets written')
