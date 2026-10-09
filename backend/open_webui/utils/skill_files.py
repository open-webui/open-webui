"""Portable skill snapshots. Paths are virtual; packages are never extracted to disk."""

import base64
import io
import json
import re
import stat
import zipfile
from pathlib import PurePosixPath
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_SKILL_BYTES = 50 * 1024 * 1024
MAX_IMPORT_BYTES = 200 * 1024 * 1024
MAX_FILES = 1000


class SkillFile(BaseModel):
    model_config = ConfigDict(extra='forbid')
    path: str
    content: str
    encoding: Literal['base64'] | None = None


class SkillFileOperation(BaseModel):
    op: Literal['put', 'move', 'delete']
    path: str
    content: str | None = None
    encoding: Literal['base64'] | None = None
    destination: str | None = None


def validate_path(path: str) -> str:
    if not path or path.startswith('/') or '\\' in path or '\x00' in path or ':' in path:
        raise ValueError('File paths must be relative POSIX paths')
    if any(part in ('', '.', '..') for part in path.split('/')):
        raise ValueError('Invalid file path')
    return path


def file_bytes(file: dict) -> bytes:
    if file.get('encoding') == 'base64':
        return base64.b64decode(file['content'], validate=True)
    return file['content'].encode('utf-8')


def encode_file(path: str, data: bytes) -> dict:
    try:
        content = data.decode('utf-8')
        if '\x00' in content:
            raise UnicodeError()
        return {'path': path, 'content': content}
    except UnicodeError:
        return {'path': path, 'content': base64.b64encode(data).decode('ascii'), 'encoding': 'base64'}


def validate_files(files: list[dict], previous: list[dict] | None = None) -> list[dict]:
    result, paths, total = [], set(), 0
    previous = {f['path']: f for f in (previous or [])}
    if len(files) > max(MAX_FILES, len(previous)):
        raise ValueError(f'A skill may contain at most {MAX_FILES} files')
    for item in files:
        file = SkillFile.model_validate(item).model_dump(exclude_none=True)
        path = validate_path(file['path'])
        if path in paths:
            raise ValueError(f'Duplicate file: {path}')
        paths.add(path)
        size = len(file_bytes(file))
        old_size = len(file_bytes(previous[path])) if path in previous else 0
        if size > max(MAX_FILE_BYTES, old_size):
            raise ValueError(f'File exceeds 10 MiB: {path}')
        total += size
        result.append(file)
    if total > max(MAX_SKILL_BYTES, sum(len(file_bytes(f)) for f in previous.values())):
        raise ValueError('Skill exceeds 50 MiB')
    for path in paths:
        if any(str(parent) in paths for parent in PurePosixPath(path).parents if str(parent) != '.'):
            raise ValueError(f'A file is also used as a directory: {path}')
    root = next((f for f in result if f['path'] == 'SKILL.md'), None)
    if root is None or root.get('encoding'):
        raise ValueError('A skill requires a UTF-8 SKILL.md at its root')
    return sorted(result, key=lambda f: f['path'])


def apply_operations(files: list[dict], operations: list[dict]) -> list[dict]:
    result = {f['path']: dict(f) for f in files}
    for raw in operations:
        operation = SkillFileOperation.model_validate(raw)
        path = validate_path(operation.path)
        if operation.op == 'put':
            if operation.content is None:
                raise ValueError('put requires content')
            result[path] = {'path': path, 'content': operation.content}
            if operation.encoding:
                result[path]['encoding'] = operation.encoding
        else:
            if path == 'SKILL.md':
                raise ValueError('SKILL.md cannot be moved or deleted')
            matched = [p for p in result if p == path or p.startswith(path + '/')]
            if not matched:
                raise ValueError(f'File or directory not found: {path}')
            if operation.op == 'move':
                destination = validate_path(operation.destination or '')
                if destination.startswith(path + '/'):
                    raise ValueError('Cannot move a directory into itself')
                moved = {destination + p[len(path) :]: result[p] for p in matched}
                if any(p in result and p not in matched for p in moved):
                    raise ValueError('Move would overwrite an existing file')
                for p in matched:
                    del result[p]
                result.update({p: {**f, 'path': p} for p, f in moved.items()})
            else:
                for p in matched:
                    del result[p]
    return validate_files(list(result.values()), files)


def frontmatter(content: str) -> dict:
    match = re.match(r'\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)', content, re.DOTALL)
    if not match:
        return {}
    try:
        value = yaml.safe_load(match.group(1))
        return value if isinstance(value, dict) else {}
    except yaml.YAMLError:
        return {}


def file_summaries(files: list[dict]) -> list[dict]:
    return [{'path': f['path'], 'size': len(file_bytes(f)), 'encoding': f.get('encoding')} for f in files]


def parse_import(data: bytes, filename: str) -> list[dict]:
    if len(data) > MAX_IMPORT_BYTES:
        raise ValueError('Import exceeds 200 MiB')
    if filename.lower().endswith('.json'):
        value = json.loads(data)
        packages = value if isinstance(value, list) else [value]
    elif filename.lower().endswith('.zip'):
        entries = {}
        total = 0
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for info in archive.infolist():
                path = validate_path(info.filename.rstrip('/'))
                mode = info.external_attr >> 16
                if stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise ValueError('Archives cannot contain links or special files')
                if info.is_dir():
                    continue
                if path in entries:
                    raise ValueError(f'Duplicate archive path: {path}')
                total += info.file_size
                if info.file_size > MAX_FILE_BYTES or total > MAX_IMPORT_BYTES or len(entries) >= 10000:
                    raise ValueError('Archive exceeds import limits')
                entries[path] = archive.read(info)
        roots = (
            [''] if 'SKILL.md' in entries else sorted(p[: -len('SKILL.md')] for p in entries if p.endswith('/SKILL.md'))
        )
        if not roots:
            raise ValueError('Archive contains no SKILL.md')
        roots = [root for root in roots if not any(root != parent and root.startswith(parent) for parent in roots)]
        if any(not any(p.startswith(root) for root in roots) for p in entries):
            raise ValueError('Archive contains files outside skill directories')
        packages = [
            {'files': [encode_file(p[len(root) :], value) for p, value in entries.items() if p.startswith(root)]}
            for root in roots
        ]
    elif filename.lower().endswith('.md'):
        packages = [{'files': [encode_file('SKILL.md', data)]}]
    else:
        raise ValueError('Use JSON, ZIP, or Markdown')
    total = 0
    result = []
    for package in packages:
        if not isinstance(package, dict):
            raise ValueError('Each imported skill must be an object')
        files = validate_files(
            package['files'] if 'files' in package else [{'path': 'SKILL.md', 'content': package.get('content', '')}]
        )
        total += sum(len(file_bytes(f)) for f in files)
        if total > MAX_IMPORT_BYTES:
            raise ValueError('Import exceeds 200 MiB decoded')
        fm = frontmatter(next(f['content'] for f in files if f['path'] == 'SKILL.md'))
        name = package.get('name') or fm.get('name') or 'Imported skill'
        result.append(
            {
                'id': package.get('id')
                or re.sub(r'[^a-z0-9_-]+', '-', str(name).lower()).strip('-')
                or 'imported-skill',
                'name': str(name),
                'description': package.get('description', fm.get('description', '')),
                'meta': package.get('meta') or {},
                'is_active': package.get('is_active', True),
                'files': files,
            }
        )
    return result


def zip_export(packages: list[dict]) -> bytes:
    output, roots = io.BytesIO(), set()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for package in packages:
            root_file = next(f for f in package['files'] if f['path'] == 'SKILL.md')
            name = frontmatter(root_file['content']).get('name')
            root = name if isinstance(name, str) and re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name) else package['id']
            validate_path(root)
            if root in roots:
                raise ValueError('Selected skills have duplicate export directory names')
            roots.add(root)
            for file in package['files']:
                archive.writestr(root + '/' + validate_path(file['path']), file_bytes(file))
    return output.getvalue()
