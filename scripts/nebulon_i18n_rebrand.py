#!/usr/bin/env python3
"""Replace user-visible Open WebUI strings in i18n locale files."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ROOT / 'src/lib/i18n/locales'

REPLACEMENTS = [
    ('Open WebUI Community', 'Nebulon AI'),
    ('Open WebUI', 'Nebulon AI'),
    ('OpenWebUI', 'Nebulon AI'),
    ('openwebui.com', 'nebulon.ai'),
]


def transform(text: str) -> str:
    if not isinstance(text, str):
        return text
    out = text
    for old, new in REPLACEMENTS:
        out = out.replace(old, new)
    return out


def main() -> None:
    count = 0
    for path in sorted(LOCALES.glob('*/translation.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        new_data = {}
        changed = False
        for key, value in data.items():
            new_key = transform(key)
            new_value = transform(value) if isinstance(value, str) else value
            if new_key != key or new_value != value:
                changed = True
            new_data[new_key] = new_value
        if changed:
            path.write_text(json.dumps(new_data, ensure_ascii=False, indent='\t') + '\n', encoding='utf-8')
            count += 1
    print(f'Updated {count} locale files')


if __name__ == '__main__':
    main()