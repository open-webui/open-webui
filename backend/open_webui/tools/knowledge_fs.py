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
# FILE RESOLUTION & ACCESS CONTROL
# =============================================================================


async def _get_accessible_files(user: dict, model_knowledge: list[dict] | None,
                                 knowledge_id: str | None = None) -> list[dict]:
    """Get all files the user can access, with KB metadata."""
    from open_webui.models.access_grants import AccessGrants
    from open_webui.models.files import Files
    from open_webui.models.groups import Groups
    from open_webui.models.knowledge import Knowledges

    user_id = user.get('id')
    user_role = user.get('role', 'user')
    user_group_ids = [g.id for g in await Groups.get_groups_by_member_id(user_id)]

    files = []  # list of {id, filename, size, type, updated_at, knowledge_id, knowledge_name, file_obj}

    if model_knowledge:
        attached_kb_ids = set()
        attached_file_ids = set()

        for item in model_knowledge:
            t, i = item.get('type'), item.get('id')
            if t == 'collection':
                attached_kb_ids.add(i)
            elif t == 'file':
                attached_file_ids.add(i)

        if knowledge_id:
            if knowledge_id not in attached_kb_ids:
                return []
            attached_kb_ids = {knowledge_id}

        for kb_id in attached_kb_ids:
            knowledge = await Knowledges.get_knowledge_by_id(kb_id)
            if not knowledge:
                continue
            if not (user_role == 'admin' or knowledge.user_id == user_id
                    or await AccessGrants.has_access(
                        user_id=user_id, resource_type='knowledge',
                        resource_id=knowledge.id, permission='read',
                        user_group_ids=set(user_group_ids))):
                continue

            kb_files = await Knowledges.get_files_by_id(kb_id)
            if kb_files:
                for f in kb_files:
                    files.append({
                        'id': f.id, 'filename': f.filename,
                        'size': f.meta.get('size') if f.meta else None,
                        'type': f.meta.get('content_type') if f.meta else None,
                        'updated_at': f.updated_at,
                        'knowledge_id': kb_id,
                        'knowledge_name': knowledge.name,
                    })

        for fid in attached_file_ids:
            f = await Files.get_file_by_id(fid)
            if f:
                files.append({
                    'id': f.id, 'filename': f.filename,
                    'size': f.meta.get('size') if f.meta else None,
                    'type': f.meta.get('content_type') if f.meta else None,
                    'updated_at': f.updated_at,
                    'knowledge_id': None, 'knowledge_name': None,
                })

    elif knowledge_id:
        knowledge = await Knowledges.get_knowledge_by_id(knowledge_id)
        if not knowledge:
            return []
        if not (user_role == 'admin' or knowledge.user_id == user_id
                or await AccessGrants.has_access(
                    user_id=user_id, resource_type='knowledge',
                    resource_id=knowledge.id, permission='read',
                    user_group_ids=set(user_group_ids))):
            return []

        kb_files = await Knowledges.get_files_by_id(knowledge_id)
        if kb_files:
            for f in kb_files:
                files.append({
                    'id': f.id, 'filename': f.filename,
                    'size': f.meta.get('size') if f.meta else None,
                    'type': f.meta.get('content_type') if f.meta else None,
                    'updated_at': f.updated_at,
                    'knowledge_id': knowledge_id,
                    'knowledge_name': knowledge.name,
                })
    else:
        result = await Knowledges.search_knowledge_bases(
            user_id, filter={'query': '', 'user_id': user_id, 'group_ids': user_group_ids},
            skip=0, limit=50,
        )
        for kb in result.items:
            kb_files = await Knowledges.get_files_by_id(kb.id)
            if kb_files:
                for f in kb_files:
                    files.append({
                        'id': f.id, 'filename': f.filename,
                        'size': f.meta.get('size') if f.meta else None,
                        'type': f.meta.get('content_type') if f.meta else None,
                        'updated_at': f.updated_at,
                        'knowledge_id': kb.id, 'knowledge_name': kb.name,
                    })

    return files


async def _resolve_file(ref: str, user: dict, model_knowledge: list[dict] | None) -> dict | None:
    """Resolve a file reference (ID or filename) to a file info dict with content."""
    from open_webui.models.files import Files

    # Try direct ID lookup first
    f = await Files.get_file_by_id(ref)
    if f and f.data:
        return {'id': f.id, 'filename': f.filename, 'content': f.data.get('content', ''),
                'meta': f.meta, 'updated_at': f.updated_at, 'created_at': f.created_at}

    # Try filename match within accessible files
    accessible = await _get_accessible_files(user, model_knowledge)
    matches = [fi for fi in accessible if fi['filename'] == ref]

    if len(matches) == 1:
        f = await Files.get_file_by_id(matches[0]['id'])
        if f and f.data:
            return {'id': f.id, 'filename': f.filename, 'content': f.data.get('content', ''),
                    'meta': f.meta, 'updated_at': f.updated_at, 'created_at': f.created_at,
                    'knowledge_id': matches[0].get('knowledge_id'),
                    'knowledge_name': matches[0].get('knowledge_name')}
    elif len(matches) > 1:
        return {'error': f'Ambiguous filename "{ref}". Matches:\n' +
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
    """List files with metadata."""
    knowledge_id = args[0] if args else None
    files = await _get_accessible_files(user, model_knowledge, knowledge_id)

    if not files:
        return 'No files found.'

    # Group by KB
    by_kb: dict[str, list[dict]] = {}
    for f in files:
        key = f.get('knowledge_name') or 'Direct Files'
        by_kb.setdefault(key, []).append(f)

    lines = []
    for kb_name, kb_files in by_kb.items():
        kb_id = kb_files[0].get('knowledge_id', '')
        if kb_id:
            lines.append(f'Knowledge Base: {kb_name} ({kb_id})')
        else:
            lines.append(f'{kb_name}')

        for f in kb_files:
            size_str = f'{f["size"]:,} bytes' if f.get('size') else 'unknown size'
            type_str = f.get('type') or 'unknown type'
            date_str = ''
            if f.get('updated_at'):
                from datetime import datetime, timezone
                dt = datetime.fromtimestamp(f['updated_at'], tz=timezone.utc)
                date_str = dt.strftime('%Y-%m-%d')
            lines.append(f'  {f["id"]}  {f["filename"]}  {size_str}  {type_str}  {date_str}')

        lines.append('')

    return '\n'.join(lines).rstrip()


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

    for arg in args[1:]:
        if '*' in arg or arg.startswith('.'):
            ext_filter = arg.lstrip('*').lstrip('.')
        else:
            file_ref = arg

    case_insensitive = 'i' in flags
    filenames_only = 'l' in flags
    count_only = 'c' in flags
    use_regex = 'E' in flags

    # Auto-detect regex: models commonly use \| for alternation (POSIX BRE style),
    # .* / .+ for wildcards, \d \w \s for character classes, or [...] brackets.
    # If any of these are present, auto-promote to regex mode.
    if not use_regex and ('\\|' in pattern or '.*' in pattern or '.+' in pattern
                          or '.?' in pattern or '\\d' in pattern or '\\w' in pattern
                          or '\\s' in pattern or re.search(r'\[.+\]', pattern)):
        use_regex = True

    # Build matcher
    if use_regex:
        # Normalize \| to | (models trained on POSIX grep use \| for alternation)
        normalized = pattern.replace('\\|', '|').replace('\|', '|')
        try:
            re_flags = re.IGNORECASE if case_insensitive else 0
            compiled = re.compile(normalized, re_flags)
        except re.error as e:
            return f'Invalid regex: {e}'
        def _matches(line: str) -> bool:
            return bool(compiled.search(line))
    else:
        search_pattern = pattern.lower() if case_insensitive else pattern
        def _matches(line: str) -> bool:
            s = line.lower() if case_insensitive else line
            return search_pattern in s

    # Grep on piped input
    if piped_input is not None:
        lines = piped_input.split('\n')
        matched = []
        for i, line in enumerate(lines, 1):
            if _matches(line):
                matched.append(f'{i}: {line}')
        return '\n'.join(matched) if matched else f'No matches for "{pattern}"'

    # Single file grep
    if file_ref:
        resolved = await _resolve_file(file_ref, user, model_knowledge)
        if not resolved:
            return f'File not found: {file_ref}'
        if 'error' in resolved:
            return resolved['error']

        lines = resolved['content'].split('\n')
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
        return '\n'.join(matched)

    # Cross-file grep
    accessible = await _get_accessible_files(user, model_knowledge)

    if ext_filter:
        accessible = [f for f in accessible if f['filename'].endswith(f'.{ext_filter}')]

    if len(accessible) > MAX_GREP_FILES:
        return (f'Too many files ({len(accessible)}). '
                f'Scope your search: grep "{pattern}" <knowledge_id> or grep "{pattern}" *.py')

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
    """Find files by name/glob pattern."""
    if not args:
        return 'Usage: find "*.md" or find "config*"'

    pattern = args[0]
    accessible = await _get_accessible_files(user, model_knowledge)

    # Simple glob matching
    import fnmatch
    matched = [f for f in accessible if fnmatch.fnmatch(f['filename'], pattern)]

    if not matched:
        return f'No files matching "{pattern}"'

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
      ls                              — list all files
      cat -n <file>                   — read file with line numbers
      head -20 <file>                 — first 20 lines
      tail -10 <file>                 — last 10 lines
      sed -n '40,60p' <file>          — view lines 40-60
      grep "text" <file>              — exact text search (auto-detects regex)
      grep -i "text"                  — case-insensitive
      grep -l "text"                  — filenames-only
      grep -c "text"                  — match counts
      grep "error|warn" <file>        — regex alternation (auto-detected)
      grep "text" *.py                — filter by extension
      find "*.md"                     — find files by glob
      wc <file>                       — line/word/char counts
      stat <file>                     — file metadata

    Pipes:  grep "auth" | head -5
    Files:  reference by filename or file ID from ls

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
