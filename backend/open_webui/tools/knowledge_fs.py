"""
Knowledge Base Filesystem Interface.

Provides a filesystem-like command interface (ls, cat, grep, find, etc.)
for AI models to interact with knowledge bases using commands they already know.

Re-exported through builtin.py for consistent imports.
"""

import json
import logging
import re
import shlex
import time
from typing import Optional

from fastapi import Request

log = logging.getLogger(__name__)

# Limits
MAX_CAT_CHARS = 100_000
DEFAULT_CAT_CHARS = 10_000
MAX_GREP_FILES = 200
DEFAULT_HEAD_LINES = 10
DEFAULT_TAIL_LINES = 10
MAX_GREP_MATCHES = 50


# =============================================================================
# SHARED REGEX UTILITIES — also used by builtin.py grep_knowledge_files
# =============================================================================


def is_regex_pattern(pattern: str) -> bool:
    """Detect if a pattern looks like regex (\|, .*, .+, \d, \w, \s, [...])."""
    return ('\|' in pattern or '.*' in pattern or '.+' in pattern
            or '.?' in pattern or '\d' in pattern or '\w' in pattern
            or '\s' in pattern or bool(re.search(r'\[.+\]', pattern)))


def normalize_regex(pattern: str) -> str:
    """Normalize POSIX BRE patterns to Python regex (\| → |)."""
    return pattern.replace('\\|', '|').replace('\|', '|')


def build_matcher(pattern: str, case_insensitive: bool = False,
                  use_regex: bool = False) -> tuple:
    """Build a matcher function. Returns (match_fn, error_str_or_None)."""
    if not use_regex and is_regex_pattern(pattern):
        use_regex = True

    if use_regex:
        normalized = normalize_regex(pattern)
        try:
            re_flags = re.IGNORECASE if case_insensitive else 0
            compiled = re.compile(normalized, re_flags)
        except re.error as e:
            return None, f'Invalid regex: {e}'
        return (lambda line: bool(compiled.search(line))), None
    else:
        sp = pattern.lower() if case_insensitive else pattern
        return (lambda line: sp in (line.lower() if case_insensitive else line)), None


# =============================================================================
# COMMAND PARSING
# =============================================================================


def _parse_pipeline(command: str) -> list[list[str]]:
    """Split command on pipes, then tokenize each segment."""
    # Split on | but not inside quotes
    segments = []
    current = []
    in_single = False
    in_double = False
    buf = []

    for ch in command:
        if ch == "'" and not in_double:
            in_single = not in_single
            buf.append(ch)
        elif ch == '"' and not in_single:
            in_double = not in_double
            buf.append(ch)
        elif ch == '|' and not in_single and not in_double:
            segments.append(''.join(buf).strip())
            buf = []
        else:
            buf.append(ch)

    remaining = ''.join(buf).strip()
    if remaining:
        segments.append(remaining)

    result = []
    for seg in segments:
        if not seg:
            continue
        try:
            tokens = shlex.split(seg)
        except ValueError:
            # Fallback for malformed quotes
            tokens = seg.split()
        if tokens:
            result.append(tokens)

    return result


def _extract_flags(tokens: list[str]) -> tuple[set[str], list[str]]:
    """Extract single-char flags (e.g. -i, -l, -c, -n, -la) from tokens.

    Returns (flags_set, remaining_args).
    """
    flags = set()
    args = []
    for token in tokens:
        if token.startswith('-') and len(token) > 1 and not token[1:].isdigit():
            # Could be -ilc (combined) or -20 (number, skip)
            for ch in token[1:]:
                flags.add(ch)
        else:
            args.append(token)
    return flags, args


def _extract_numeric_flag(tokens: list[str]) -> tuple[Optional[int], list[str]]:
    """Extract a numeric flag like -20 from tokens. Returns (number, remaining)."""
    num = None
    remaining = []
    for token in tokens:
        if num is None and re.match(r'^-\d+$', token):
            num = int(token[1:])
        else:
            remaining.append(token)
    return num, remaining


# =============================================================================
# DIRECTORY TREE & PATH RESOLUTION
# =============================================================================


async def _build_directory_tree(knowledge_id: str) -> dict:
    """Build an in-memory directory tree for a KB. Returns {dirs, files, path_to_dir_id, dir_id_to_path}."""
    from open_webui.models.knowledge import Knowledges

    all_dirs = await Knowledges.get_all_directories(knowledge_id)
    files_with_dirs = await Knowledges.get_files_with_directory_ids(knowledge_id)

    # Build dir_id -> dir info map
    dir_map = {}
    for d in all_dirs:
        dir_map[d.id] = {'name': d.name, 'parent_id': d.parent_id, 'id': d.id}

    # Compute full path for each directory
    dir_id_to_path = {}
    def _get_dir_path(dir_id):
        if dir_id in dir_id_to_path:
            return dir_id_to_path[dir_id]
        d = dir_map.get(dir_id)
        if not d:
            return ''
        if d['parent_id'] and d['parent_id'] in dir_map:
            parent_path = _get_dir_path(d['parent_id'])
            path = f"{parent_path}/{d['name']}" if parent_path else d['name']
        else:
            path = d['name']
        dir_id_to_path[dir_id] = path
        return path

    for d_id in dir_map:
        _get_dir_path(d_id)

    path_to_dir_id = {v: k for k, v in dir_id_to_path.items()}

    # Build file list with paths
    files = []
    for file_model, directory_id in files_with_dirs:
        if directory_id and directory_id in dir_id_to_path:
            file_path = f"{dir_id_to_path[directory_id]}/{file_model.filename}"
        else:
            file_path = file_model.filename
        files.append({
            'id': file_model.id, 'filename': file_model.filename,
            'path': file_path, 'directory_id': directory_id,
            'size': file_model.meta.get('size') if file_model.meta else None,
            'type': file_model.meta.get('content_type') if file_model.meta else None,
            'updated_at': file_model.updated_at,
        })

    return {
        'dirs': dir_map,
        'files': files,
        'path_to_dir_id': path_to_dir_id,
        'dir_id_to_path': dir_id_to_path,
    }


def _resolve_path(path: str, tree: dict) -> str | None:
    """Resolve a directory path string to a dir_id. Returns None if not found."""
    path = path.strip('/')
    return tree['path_to_dir_id'].get(path)


def _get_files_in_dir(tree: dict, dir_id: str | None) -> list[dict]:
    """Get files directly in a directory (None = root)."""
    return [f for f in tree['files'] if f['directory_id'] == dir_id]


def _get_subdirs(tree: dict, parent_id: str | None) -> list[dict]:
    """Get immediate child directories."""
    return sorted(
        [d for d in tree['dirs'].values() if d['parent_id'] == parent_id],
        key=lambda d: d['name']
    )


def _get_files_under_dir(tree: dict, dir_id: str) -> list[dict]:
    """Get all files recursively under a directory."""
    # Collect this dir + all descendant dir IDs
    target_ids = {dir_id}
    changed = True
    while changed:
        changed = False
        for d in tree['dirs'].values():
            if d['parent_id'] in target_ids and d['id'] not in target_ids:
                target_ids.add(d['id'])
                changed = True
    return [f for f in tree['files'] if f['directory_id'] in target_ids]


# =============================================================================
# FILE RESOLUTION & ACCESS CONTROL
# =============================================================================


async def _get_accessible_kb_ids(user: dict, model_knowledge: list[dict] | None,
                                  knowledge_id: str | None = None) -> list[tuple[str, str, str]]:
    """Get list of (kb_id, kb_name, kb_description) the user can access."""
    from open_webui.models.access_grants import AccessGrants
    from open_webui.models.groups import Groups
    from open_webui.models.knowledge import Knowledges

    user_id = user.get('id')
    user_role = user.get('role', 'user')
    user_group_ids = [g.id for g in await Groups.get_groups_by_member_id(user_id)]

    async def _has_access(kb):
        return (user_role == 'admin' or kb.user_id == user_id
                or await AccessGrants.has_access(
                    user_id=user_id, resource_type='knowledge',
                    resource_id=kb.id, permission='read',
                    user_group_ids=set(user_group_ids)))

    result = []

    if model_knowledge:
        attached_kb_ids = set()
        for item in model_knowledge:
            if item.get('type') == 'collection':
                attached_kb_ids.add(item.get('id'))
        if knowledge_id:
            if knowledge_id not in attached_kb_ids:
                return []
            attached_kb_ids = {knowledge_id}
        for kb_id in attached_kb_ids:
            kb = await Knowledges.get_knowledge_by_id(kb_id)
            if kb and await _has_access(kb):
                result.append((kb.id, kb.name, kb.description or ''))
    elif knowledge_id:
        kb = await Knowledges.get_knowledge_by_id(knowledge_id)
        if kb and await _has_access(kb):
            result.append((kb.id, kb.name, kb.description or ''))
    else:
        search = await Knowledges.search_knowledge_bases(
            user_id, filter={'query': '', 'user_id': user_id, 'group_ids': user_group_ids},
            skip=0, limit=50,
        )
        for kb in search.items:
            result.append((kb.id, kb.name, kb.description or ''))

    return result


async def _get_accessible_files(user: dict, model_knowledge: list[dict] | None,
                                 knowledge_id: str | None = None) -> list[dict]:
    """Get all files the user can access, with KB metadata and directory_id (no path computation)."""
    from open_webui.models.files import Files
    from open_webui.models.knowledge import Knowledges

    kb_ids = await _get_accessible_kb_ids(user, model_knowledge, knowledge_id)
    files = []

    for kb_id, kb_name, _ in kb_ids:
        kb_files = await Knowledges.get_files_with_directory_ids(kb_id)
        for file_model, dir_id in kb_files:
            files.append({
                'id': file_model.id, 'filename': file_model.filename,
                'directory_id': dir_id,
                'size': file_model.meta.get('size') if file_model.meta else None,
                'type': file_model.meta.get('content_type') if file_model.meta else None,
                'updated_at': file_model.updated_at,
                'knowledge_id': kb_id,
                'knowledge_name': kb_name,
            })

    # Also handle directly attached files (not in any KB)
    if model_knowledge:
        attached_file_ids = set()
        for item in model_knowledge:
            if item.get('type') == 'file':
                attached_file_ids.add(item.get('id'))
        for fid in attached_file_ids:
            f = await Files.get_file_by_id(fid)
            if f:
                files.append({
                    'id': f.id, 'filename': f.filename,
                    'directory_id': None,
                    'size': f.meta.get('size') if f.meta else None,
                    'type': f.meta.get('content_type') if f.meta else None,
                    'updated_at': f.updated_at,
                    'knowledge_id': None, 'knowledge_name': None,
                })

    return files


async def _resolve_dir_path(path: str, knowledge_id: str) -> str | None:
    """Walk a directory path one level at a time. Returns dir_id or None."""
    from open_webui.models.knowledge import Knowledges

    parts = path.strip('/').split('/')
    current_parent = None

    for part in parts:
        dirs = await Knowledges.get_directories(knowledge_id, parent_id=current_parent)
        match = next((d for d in dirs if d.name == part), None)
        if not match:
            return None
        current_parent = match.id

    return current_parent


async def _get_descendant_dir_ids(dir_id: str, knowledge_id: str) -> set[str]:
    """Collect all descendant directory IDs recursively."""
    from open_webui.models.knowledge import Knowledges

    result = {dir_id}
    queue = [dir_id]
    while queue:
        parent = queue.pop()
        children = await Knowledges.get_directories(knowledge_id, parent_id=parent)
        for child in children:
            if child.id not in result:
                result.add(child.id)
                queue.append(child.id)
    return result


async def _resolve_file(ref: str, user: dict, model_knowledge: list[dict] | None) -> dict | None:
    """Resolve a file reference (ID, path, or filename) to a file info dict with content."""
    from open_webui.models.files import Files

    # Get accessible file IDs (lightweight — no path computation)
    accessible = await _get_accessible_files(user, model_knowledge)
    accessible_ids = {fi['id'] for fi in accessible}

    # Try direct ID lookup first — but verify access
    f = await Files.get_file_by_id(ref)
    if f and f.data:
        if f.id not in accessible_ids:
            return None
        return {'id': f.id, 'filename': f.filename, 'content': f.data.get('content', ''),
                'meta': f.meta, 'updated_at': f.updated_at, 'created_at': f.created_at}

    # Try path match (e.g. "docs/api/auth.md") — lazy dir walk
    ref_clean = ref.strip('/')
    if '/' in ref_clean:
        dir_path, filename = ref_clean.rsplit('/', 1)
        # Try resolving in each accessible KB
        kb_ids = {fi['knowledge_id'] for fi in accessible if fi.get('knowledge_id')}
        for kb_id in kb_ids:
            dir_id = await _resolve_dir_path(dir_path, kb_id)
            if dir_id is None:
                continue
            # Find file with that name in that directory
            matches = [fi for fi in accessible
                       if fi['filename'] == filename and fi['directory_id'] == dir_id]
            if len(matches) == 1:
                f = await Files.get_file_by_id(matches[0]['id'])
                if f and f.data:
                    return {'id': f.id, 'filename': f.filename, 'content': f.data.get('content', ''),
                            'meta': f.meta, 'updated_at': f.updated_at, 'created_at': f.created_at,
                            'knowledge_id': matches[0].get('knowledge_id'),
                            'knowledge_name': matches[0].get('knowledge_name')}

    # Try filename match within accessible files
    matches = [fi for fi in accessible if fi['filename'] == ref]

    if len(matches) == 1:
        f = await Files.get_file_by_id(matches[0]['id'])
        if f and f.data:
            return {'id': f.id, 'filename': f.filename, 'content': f.data.get('content', ''),
                    'meta': f.meta, 'updated_at': f.updated_at, 'created_at': f.created_at,
                    'knowledge_id': matches[0].get('knowledge_id'),
                    'knowledge_name': matches[0].get('knowledge_name')}
    elif len(matches) > 1:
        return {'error': f'Ambiguous filename "{ref}". Use full path to disambiguate:\n' +
                '\n'.join(f"  {m['id']}  {m['filename']}  ({m.get('knowledge_name', 'direct')})" for m in matches)}

    return None


async def _get_file_content(file_id: str) -> str | None:
    """Get file content by ID."""
    from open_webui.models.files import Files
    f = await Files.get_file_by_id(file_id)
    if f and f.data:
        return f.data.get('content', '')
    return None


# =============================================================================
# COMMAND HANDLERS
# =============================================================================


async def _kb_ls(args: list[str], flags: set[str], user: dict,
                 model_knowledge: list[dict] | None) -> str:
    """List files and directories. Supports: ls, ls <path>, ls -a (flat)."""
    from open_webui.models.knowledge import Knowledges

    flat_mode = 'a' in flags
    path_arg = args[0] if args else None

    kb_ids = await _get_accessible_kb_ids(user, model_knowledge, knowledge_id=None)

    # If path_arg looks like a KB ID, scope to that KB
    target_kb_id = None
    dir_path = None
    if path_arg:
        for kb_id, kb_name, _ in kb_ids:
            if kb_id == path_arg:
                target_kb_id = kb_id
                break
        if not target_kb_id:
            dir_path = path_arg.strip('/')

    if target_kb_id:
        kb_ids = [(kid, kn, kd) for kid, kn, kd in kb_ids if kid == target_kb_id]

    if not kb_ids:
        return 'No knowledge bases found.'

    lines = []
    for kb_id, kb_name, kb_desc in kb_ids:
        header = f'Knowledge Base: {kb_name} ({kb_id})'
        if kb_desc:
            header += f'\n  {kb_desc}'
        lines.append(header)

        if flat_mode:
            # Flat mode: build full tree (legitimate use)
            tree = await _build_directory_tree(kb_id)
            for f in tree['files']:
                lines.append(f'  {f["id"]}  {f["path"]}  {_fmt_size(f)}  {_fmt_date(f)}')
            lines.append('')
            continue

        # Resolve target directory (lazy walk)
        target_dir_id = None
        if dir_path:
            target_dir_id = await _resolve_dir_path(dir_path, kb_id)
            if target_dir_id is None:
                lines.append(f'  Directory not found: {dir_path}')
                lines.append('')
                continue
            lines.append(f'  Path: {dir_path}/')

        # Show subdirectories (targeted query — only this level)
        subdirs = await Knowledges.get_directories(kb_id, parent_id=target_dir_id)
        for d in subdirs:
            lines.append(f'  📁 {d.name}/')

        # Show files at this level (filter from accessible files)
        accessible = await _get_accessible_files(user, model_knowledge, knowledge_id=kb_id)
        dir_files = [f for f in accessible if f['directory_id'] == target_dir_id]
        for f in dir_files:
            lines.append(f'  {f["id"]}  {f["filename"]}  {_fmt_size(f)}  {_fmt_date(f)}')

        if not subdirs and not dir_files:
            lines.append('  (empty)')
        lines.append('')

    return '\n'.join(lines).rstrip()


def _fmt_size(f: dict) -> str:
    return f'{f["size"]:,} bytes' if f.get('size') else ''


def _fmt_date(f: dict) -> str:
    if f.get('updated_at'):
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(f['updated_at'], tz=timezone.utc)
        return dt.strftime('%Y-%m-%d')
    return ''


async def _kb_cat(args: list[str], flags: set[str], user: dict,
                  model_knowledge: list[dict] | None) -> str:
    """Read file content. Use -n for line numbers."""
    if not args:
        return 'Usage: cat [-n] <file_id or filename>'

    resolved = await _resolve_file(args[0], user, model_knowledge)
    if not resolved:
        return f'File not found: {args[0]}'
    if 'error' in resolved:
        return resolved['error']

    content = resolved['content']
    show_numbers = 'n' in flags

    if len(content) > MAX_CAT_CHARS:
        content = content[:MAX_CAT_CHARS]
        truncated = True
    else:
        truncated = False

    if show_numbers:
        lines = content.split('\n')
        content = '\n'.join(f'{i}: {line}' for i, line in enumerate(lines, 1))

    if truncated:
        content += f'\n[truncated at {MAX_CAT_CHARS:,} chars — use head/tail/sed/grep to navigate]'

    return content


async def _kb_head(args: list[str], flags: set[str], user: dict,
                   model_knowledge: list[dict] | None,
                   piped_input: str | None = None) -> str:
    """First N lines of a file or piped input."""
    n, args = _extract_numeric_flag(args)
    if n is None:
        n = DEFAULT_HEAD_LINES

    if piped_input is not None:
        lines = piped_input.split('\n')
        return '\n'.join(lines[:n])

    if not args:
        return 'Usage: head [-N] <file>'

    resolved = await _resolve_file(args[0], user, model_knowledge)
    if not resolved:
        return f'File not found: {args[0]}'
    if 'error' in resolved:
        return resolved['error']

    lines = resolved['content'].split('\n')
    total = len(lines)
    result = '\n'.join(lines[:n])
    if total > n:
        result += f'\n[showing {n} of {total} lines]'
    return result


async def _kb_tail(args: list[str], flags: set[str], user: dict,
                   model_knowledge: list[dict] | None,
                   piped_input: str | None = None) -> str:
    """Last N lines of a file or piped input."""
    n, args = _extract_numeric_flag(args)
    if n is None:
        n = DEFAULT_TAIL_LINES

    if piped_input is not None:
        lines = piped_input.split('\n')
        return '\n'.join(lines[-n:])

    if not args:
        return 'Usage: tail [-N] <file>'

    resolved = await _resolve_file(args[0], user, model_knowledge)
    if not resolved:
        return f'File not found: {args[0]}'
    if 'error' in resolved:
        return resolved['error']

    lines = resolved['content'].split('\n')
    total = len(lines)
    result = '\n'.join(lines[-n:])
    if total > n:
        result += f'\n[showing last {n} of {total} lines]'
    return result


async def _kb_grep(args: list[str], flags: set[str], user: dict,
                   model_knowledge: list[dict] | None,
                   piped_input: str | None = None) -> str:
    """Text search across files or piped input. Supports -E for regex."""
    if not args:
        return 'Usage: grep [-E] [-i] [-l] [-c] "pattern" [file] [*.ext]'

    pattern = args[0]
    file_ref = None
    ext_filter = None
    dir_scope = None

    for arg in args[1:]:
        if '*' in arg or arg.startswith('.'):
            ext_filter = arg.lstrip('*').lstrip('.')
        elif arg.endswith('/'):
            dir_scope = arg.strip('/')
        else:
            file_ref = arg

    case_insensitive = 'i' in flags
    filenames_only = 'l' in flags
    count_only = 'c' in flags
    use_regex = 'E' in flags

    _matches, err = build_matcher(pattern, case_insensitive, use_regex)
    if err:
        return err

    # Grep on piped input
    if piped_input is not None:
        lines = piped_input.split('\\n')
        matched = []
        for i, line in enumerate(lines, 1):
            if _matches(line):
                matched.append(f'{i}: {line}')
        return '\\n'.join(matched) if matched else f'No matches for "{pattern}"'

    # Single file grep
    if file_ref and not dir_scope:
        resolved = await _resolve_file(file_ref, user, model_knowledge)
        if not resolved:
            # Maybe it's a directory path without trailing /
            dir_scope = file_ref
        elif 'error' in resolved:
            return resolved['error']
        else:
            lines = resolved['content'].split('\\n')
            matched = []
            for i, line in enumerate(lines, 1):
                if _matches(line):
                    matched.append(f'{i}: {line}')

            if count_only:
                return f'{resolved["id"]}  {resolved["filename"]}: {len(matched)}'
            if filenames_only:
                return f'{resolved["id"]}  {resolved["filename"]}' if matched else f'No matches for "{pattern}"'

            if not matched:
                return f'No matches for "{pattern}" in {resolved["filename"]}'
            return '\\n'.join(matched)

    # Cross-file grep (optionally scoped to directory)
    accessible = await _get_accessible_files(user, model_knowledge)

    if dir_scope:
        # Resolve directory and collect all descendant IDs
        kb_ids = {fi['knowledge_id'] for fi in accessible if fi.get('knowledge_id')}
        target_dir_ids = set()
        for kb_id in kb_ids:
            dir_id = await _resolve_dir_path(dir_scope, kb_id)
            if dir_id:
                desc = await _get_descendant_dir_ids(dir_id, kb_id)
                target_dir_ids.update(desc)
        if not target_dir_ids:
            return f'No files found under "{dir_scope}/"'
        accessible = [f for f in accessible if f.get('directory_id') in target_dir_ids]
        if not accessible:
            return f'No files found under "{dir_scope}/"'

    if ext_filter:
        accessible = [f for f in accessible if f['filename'].endswith(f'.{ext_filter}')]

    if len(accessible) > MAX_GREP_FILES:
        return (f'Too many files ({len(accessible)}). '
                f'Scope your search: grep "{pattern}" docs/ or grep "{pattern}" *.py')

    from open_webui.models.files import Files

    results = []
    file_match_counts = []
    files_with_matches = []
    total_matches = 0

    for file_info in accessible:
        f = await Files.get_file_by_id(file_info['id'])
        if not f or not f.data:
            continue

        content = f.data.get('content', '')
        if not content:
            continue

        lines = content.split('\n')
        file_matches = []
        for i, line in enumerate(lines, 1):
            if _matches(line):
                file_matches.append((i, line))

        if file_matches:
            files_with_matches.append(file_info)
            file_match_counts.append((file_info, len(file_matches)))
            total_matches += len(file_matches)

            if not count_only and not filenames_only:
                for line_num, line_text in file_matches:
                    if len(results) < MAX_GREP_MATCHES:
                        results.append(
                            f'{file_info["id"]}  {file_info["filename"]}:{line_num}: {line_text.rstrip()}'
                        )

    if count_only:
        if not file_match_counts:
            return f'No matches for "{pattern}"'
        lines = [f'{fi["id"]}  {fi["filename"]}: {cnt}' for fi, cnt in file_match_counts]
        lines.append(f'Total: {total_matches} matches in {len(file_match_counts)} files')
        return '\n'.join(lines)

    if filenames_only:
        if not files_with_matches:
            return f'No matches for "{pattern}"'
        return '\n'.join(f'{fi["id"]}  {fi["filename"]}' for fi in files_with_matches)

    if not results:
        return f'No matches for "{pattern}" across {len(accessible)} files'

    output = '\n'.join(results)
    if total_matches > MAX_GREP_MATCHES:
        output += f'\n[showing {MAX_GREP_MATCHES} of {total_matches} matches]'
    return output


async def _kb_find(args: list[str], flags: set[str], user: dict,
                   model_knowledge: list[dict] | None) -> str:
    """Find files by name/glob pattern, optionally scoped to a directory."""
    if not args:
        return 'Usage: find "*.md" or find docs/ "*.md"'

    import fnmatch

    # If two args and first looks like a dir scope
    dir_scope = None
    if len(args) >= 2 and ('/' in args[0] or not ('*' in args[0] or '?' in args[0])):
        dir_scope = args[0].strip('/')
        pattern = args[1]
    else:
        pattern = args[0]

    accessible = await _get_accessible_files(user, model_knowledge)

    if dir_scope:
        kb_ids = {fi['knowledge_id'] for fi in accessible if fi.get('knowledge_id')}
        target_dir_ids = set()
        for kb_id in kb_ids:
            dir_id = await _resolve_dir_path(dir_scope, kb_id)
            if dir_id:
                desc = await _get_descendant_dir_ids(dir_id, kb_id)
                target_dir_ids.update(desc)
        accessible = [f for f in accessible if f.get('directory_id') in target_dir_ids]

    matched = [f for f in accessible if fnmatch.fnmatch(f['filename'], pattern)]

    if not matched:
        scope_str = f' under "{dir_scope}/"' if dir_scope else ''
        return f'No files matching "{pattern}"{scope_str}'

    lines = []
    for f in matched:
        kb_info = f' ({f["knowledge_name"]})' if f.get('knowledge_name') else ''
        lines.append(f'{f["id"]}  {f["filename"]}{kb_info}')
    return '\n'.join(lines)


async def _kb_wc(args: list[str], flags: set[str], user: dict,
                 model_knowledge: list[dict] | None,
                 piped_input: str | None = None) -> str:
    """Word, line, character counts."""
    if piped_input is not None:
        lines = piped_input.count('\n') + (1 if piped_input and not piped_input.endswith('\n') else 0)
        words = len(piped_input.split())
        chars = len(piped_input)
        if 'l' in flags:
            return str(lines)
        return f'  {lines}  {words}  {chars}'

    if not args:
        return 'Usage: wc [-l] <file>'

    resolved = await _resolve_file(args[0], user, model_knowledge)
    if not resolved:
        return f'File not found: {args[0]}'
    if 'error' in resolved:
        return resolved['error']

    content = resolved['content']
    lines = content.count('\n') + (1 if content and not content.endswith('\n') else 0)
    words = len(content.split())
    chars = len(content)

    if 'l' in flags:
        return f'  {lines}  {resolved["filename"]}'
    return f'  {lines}  {words}  {chars}  {resolved["filename"]}'


async def _kb_stat(args: list[str], flags: set[str], user: dict,
                   model_knowledge: list[dict] | None) -> str:
    """File metadata."""
    if not args:
        return 'Usage: stat <file>'

    resolved = await _resolve_file(args[0], user, model_knowledge)
    if not resolved:
        return f'File not found: {args[0]}'
    if 'error' in resolved:
        return resolved['error']

    content = resolved['content']
    lines = content.count('\n') + (1 if content and not content.endswith('\n') else 0)
    words = len(content.split())
    chars = len(content)

    meta = resolved.get('meta') or {}
    size = meta.get('size', chars)
    content_type = meta.get('content_type', 'unknown')

    out = [
        f'  File: {resolved["filename"]}',
        f'    ID: {resolved["id"]}',
        f'  Size: {size:,} bytes',
        f'  Type: {content_type}',
        f' Lines: {lines:,}',
        f' Words: {words:,}',
        f' Chars: {chars:,}',
    ]

    if resolved.get('created_at'):
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(resolved['created_at'], tz=timezone.utc)
        out.append(f'  Created: {dt.strftime("%Y-%m-%d %H:%M:%S UTC")}')
    if resolved.get('updated_at'):
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(resolved['updated_at'], tz=timezone.utc)
        out.append(f'  Updated: {dt.strftime("%Y-%m-%d %H:%M:%S UTC")}')
    if resolved.get('knowledge_name'):
        out.append(f'      KB: {resolved["knowledge_name"]} ({resolved.get("knowledge_id", "")})')

    return '\n'.join(out)


async def _kb_sed(args: list[str], flags: set[str], user: dict,
                  model_knowledge: list[dict] | None,
                  piped_input: str | None = None) -> str:
    """Extract line range from a file. Usage: sed -n 'M,Np' <file>"""
    if piped_input is not None:
        # sed on piped input: parse range from args
        start, end = 1, None
        if 'n' in flags and args:
            m = re.match(r"^(\d+),(\d+)p?$", args[0])
            if m:
                start, end = int(m.group(1)), int(m.group(2))
                args = args[1:]
        lines = piped_input.split('\n')
        selected = lines[max(0, start - 1):(end or len(lines))]
        return '\n'.join(selected)

    # Parse: sed -n '40,60p' <file>
    range_str = None
    file_ref = None

    for arg in args:
        m = re.match(r"^'?(\d+),(\d+)p?'?$", arg)
        if m:
            range_str = arg
        else:
            file_ref = arg

    if not range_str or not file_ref:
        return "Usage: sed -n '40,60p' <file>"

    m = re.match(r"^'?(\d+),(\d+)p?'?$", range_str)
    start, end = int(m.group(1)), int(m.group(2))

    if start > end:
        return f'Invalid range: start ({start}) > end ({end})'

    resolved = await _resolve_file(file_ref, user, model_knowledge)
    if not resolved:
        return f'File not found: {file_ref}'
    if 'error' in resolved:
        return resolved['error']

    lines = resolved['content'].split('\n')
    total = len(lines)
    selected = lines[max(0, start - 1):end]
    result = '\n'.join(selected)
    result += f'\n[lines {start}-{min(end, total)} of {total}]'
    return result


# =============================================================================
# PIPE EXECUTOR
# =============================================================================


async def _kb_tree(args: list[str], flags: set[str], user: dict,
                   model_knowledge: list[dict] | None) -> str:
    """Show directory tree structure."""
    kb_ids = await _get_accessible_kb_ids(user, model_knowledge)
    if not kb_ids:
        return 'No knowledge bases found.'

    dir_scope = args[0].strip('/') if args else None
    output = []

    for kb_id, kb_name, kb_desc in kb_ids:
        tree = await _build_directory_tree(kb_id)
        header = f'Knowledge Base: {kb_name} ({kb_id})'
        if kb_desc:
            header += f'\n  {kb_desc}'
        output.append(header)

        # Find root to start from
        root_dir_id = None
        if dir_scope:
            root_dir_id = _resolve_path(dir_scope, tree)
            if root_dir_id is None:
                output.append(f'  Directory not found: {dir_scope}')
                output.append('')
                continue
            output.append(f'  {dir_scope}/')

        def _render_tree(parent_id, prefix='  '):
            items = []
            subdirs = _get_subdirs(tree, parent_id)
            files = _get_files_in_dir(tree, parent_id)
            entries = [('dir', d) for d in subdirs] + [('file', f) for f in files]

            for idx, (etype, entry) in enumerate(entries):
                is_last = idx == len(entries) - 1
                connector = '└── ' if is_last else '├── '
                child_prefix = prefix + ('    ' if is_last else '│   ')

                if etype == 'dir':
                    items.append(f'{prefix}{connector}📁 {entry["name"]}/')
                    items.extend(_render_tree(entry['id'], child_prefix))
                else:
                    items.append(f'{prefix}{connector}{entry["filename"]}')
            return items

        output.extend(_render_tree(root_dir_id))

        # Summary
        total_dirs = len(tree['dirs'])
        total_files = len(tree['files'])
        output.append(f'\n  {total_dirs} directories, {total_files} files')
        output.append('')

    return '\n'.join(output).rstrip()


COMMAND_MAP = {
    'ls': _kb_ls,
    'cat': _kb_cat,
    'head': _kb_head,
    'tail': _kb_tail,
    'grep': _kb_grep,
    'find': _kb_find,
    'wc': _kb_wc,
    'stat': _kb_stat,
    'sed': _kb_sed,
    'tree': _kb_tree,
}


async def _execute_pipeline(
    segments: list[list[str]],
    user: dict,
    model_knowledge: list[dict] | None,
) -> str:
    """Execute a pipeline of commands, passing text between them."""
    piped_input = None

    for tokens in segments:
        cmd_name = tokens[0].lower()
        rest = tokens[1:]

        handler = COMMAND_MAP.get(cmd_name)
        if not handler:
            return f'Unknown command: {cmd_name}. Available: {", ".join(sorted(COMMAND_MAP.keys()))}'

        flags, args = _extract_flags(rest)

        # Commands that accept piped input
        if piped_input is not None and cmd_name in ('head', 'tail', 'grep', 'wc', 'sed'):
            piped_input = await handler(args, flags, user, model_knowledge, piped_input=piped_input)
        else:
            piped_input = await handler(args, flags, user, model_knowledge)

    return piped_input or ''


# =============================================================================
# ENTRY POINT
# =============================================================================


async def kb_exec(
    command: str,
    __request__: Request = None,
    __user__: dict = None,
    __model_knowledge__: Optional[list[dict]] = None,
) -> str:
    """
    Run a filesystem command against the knowledge base.

    Commands:
      ls                              — list root files and directories
      ls docs/                        — list contents of a directory
      ls -a                           — flat list of all files with full paths
      tree                            — recursive directory tree view
      tree docs/                      — subtree from a directory
      cat -n <file>                   — read file with line numbers
      head -20 <file>                 — first 20 lines
      tail -10 <file>                 — last 10 lines
      sed -n '40,60p' <file>          — view lines 40-60
      grep "text" <file>              — exact text search (auto-detects regex)
      grep -i "text"                  — case-insensitive
      grep -l "text"                  — filenames-only
      grep -c "text"                  — match counts
      grep "text" docs/               — search within a directory
      grep "text" *.py                — filter by extension
      find "*.md"                     — find files by glob
      find docs/ "*.md"               — find within a directory
      wc <file>                       — line/word/char counts
      stat <file>                     — file metadata

    Pipes:  grep "auth" | head -5
    Files:  reference by path (docs/api/auth.md), filename, or file ID

    :param command: A filesystem command string
    :return: Command output as text
    """
    if not __user__:
        return 'Error: User context not available'

    if not command or not command.strip():
        return 'Usage: kb_exec("<command>"). Run kb_exec("ls") to start.'

    try:
        segments = _parse_pipeline(command.strip())
        if not segments:
            return 'Could not parse command. Run kb_exec("ls") to start.'

        return await _execute_pipeline(segments, __user__, __model_knowledge__)
    except Exception as e:
        log.exception(f'kb_exec error: {e}')
        return f'Error: {e}'
