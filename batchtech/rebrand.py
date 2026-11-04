"""Rename user-visible "Open WebUI" to "BatchTechUI". Safe to re-run after every upstream merge.

Leaves alone: code comments about the LICENSE, URLs/package names (open-webui), and anything that refers to the
upstream *Community* site (sharing/leaderboard), which really is Open WebUI's.
"""

import json, re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
NEW = 'BatchTechUI'
OLD = 'Open WebUI'


def keep(line):
    # Also keep: copyright attribution, the gate that shows it, and upstream's own marketing/community copy.
    skip = [
        'LICENSE covers',
        'Community',
        'docs.openwebui',
        'github.com',
        'Inc.',
        'WEBUI_NAME.includes',
        'Open WebUI team',
        'Help us translate',
        'sponsorship',
        'free to use as-is',
    ]
    return any(s in line for s in skip)


changed = 0
for p in list((root / 'src').rglob('*.svelte')) + list((root / 'src').rglob('*.ts')) + [root / 'src/app.html']:
    text = p.read_text()
    if OLD not in text:
        continue
    lines = text.split('\n')
    new = [l if keep(l) else l.replace(OLD, NEW) for l in lines]
    if new != lines:
        p.write_text('\n'.join(new))
        changed += 1

# English strings double as i18n keys: rename them in every locale, keeping existing translations (the product name
# stays in Latin letters in translations), so the i18n parser finds nothing to change.
for tp in sorted((root / 'src/lib/i18n/locales').glob('*/translation.json')):
    data = json.loads(tp.read_text())
    out = {}
    for k, v in data.items():
        nk = k if (OLD not in k or keep(k)) else k.replace(OLD, NEW)
        # only touch the translation when the English key was renamed; translations also write it as "Open-WebUI"
        nv = re.sub(r'Open[ -]?WebUI', NEW, v) if (nk != k and isinstance(v, str)) else v
        out[nk] = nv
    if out != data:
        tp.write_text(json.dumps(out, indent='\t', ensure_ascii=False) + '\n')

for rel in ['static/static/site.webmanifest', 'static/opensearch.xml']:
    p = root / rel
    t = p.read_text().replace('"short_name": "WebUI"', '"short_name": "BatchTechUI"').replace(OLD, NEW)
    p.write_text(t)

env = root / 'backend/open_webui/env.py'
t = env.read_text()
t = t.replace("os.getenv('WEBUI_NAME', 'Open WebUI')", "os.getenv('WEBUI_NAME', 'BatchTechUI')").replace(
    "if WEBUI_NAME != 'Open WebUI':\n    WEBUI_NAME += ' (Open WebUI)'",
    "if False:  # BatchTechUI: no ' (Open WebUI)' suffix\n    pass",
)
env.write_text(t)

m = root / 'backend/open_webui/main.py'
t = m.read_text().replace("title='Open WebUI',", "title='BatchTechUI',")
m.write_text(t)
print('rebranded', changed, 'files')
