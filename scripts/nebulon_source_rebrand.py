#!/usr/bin/env python3
"""Bulk-replace user-visible Open WebUI strings in frontend/backend sources."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIR_PARTS = {
    'node_modules',
    '.git',
    'pyodide',
    'emojis',
    'docs',
    '.github',
    'test',
    'tests',
    '__pycache__',
}

SKIP_FILES = {'CHANGELOG.md', 'LICENSE', 'BRANDING.md', 'README.md'}


def should_skip(path: Path) -> bool:
    if path.name in SKIP_FILES:
        return True
    return any(part in SKIP_DIR_PARTS for part in path.parts)


REPLACEMENTS = [
    ('Open WebUI Community', 'Nebulon AI'),
    ('Open WebUI: Server Connection Error', 'Nebulon AI: Server Connection Error'),
    ('Open WebUI', 'Nebulon AI'),
    ('OpenWebUI', 'Nebulon AI'),
]

TEXT_SUFFIXES = {
    '.py',
    '.ts',
    '.svelte',
    '.html',
    '.xml',
    '.json',
    '.sh',
    '.webmanifest',
    '.css',
    '.js',
}


SKIP_LINE = re.compile(
    r'Copyright|copyright|LICENSE covers|github\.com/open-webui|docs\.openwebui\.com|open-webui/open-webui'
    r'|OpenWebUI|open_webui|X-OpenWebUI|isOpenWebUI',
    re.I,
)


def transform(content: str) -> str:
    lines = []
    for line in content.splitlines(keepends=True):
        if SKIP_LINE.search(line):
            lines.append(line)
            continue
        new_line = line
        for old, new in REPLACEMENTS:
            new_line = new_line.replace(old, new)
        lines.append(new_line)
    return ''.join(lines)


def main() -> None:
    changed_files = []
    for path in ROOT.rglob('*'):
        if not path.is_file() or should_skip(path):
            continue
        if path.suffix not in TEXT_SUFFIXES and path.name not in ('site.webmanifest', 'Dockerfile'):
            continue
        if path.match('src/lib/i18n/locales/*/translation.json'):
            continue  # handled by i18n script
        if 'scripts/nebulon_' in str(path):
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        new_text = transform(text)
        if new_text != text:
            path.write_text(new_text, encoding='utf-8')
            changed_files.append(path.relative_to(ROOT))
    print(f'Modified {len(changed_files)} files')


if __name__ == '__main__':
    main()