#!/usr/bin/env python3
"""Sync a local Pipe function .py file into a running open-webui instance.

open-webui stores Pipe/Filter/Action function source as a DB row
(`Function.content`) and only offers admin-UI paste or a `/load/url` fetch
to populate it -- there's no "load .py files from a directory on startup"
mechanism in this version. This script is the missing piece: it POSTs the
file's contents to the admin Functions API so the actual dev loop is
"edit the .py file in this repo, run this script," with the diff living in
git instead of the admin UI's textarea.

Usage:
    python docs/ichirouganaim-integration/sync_pipe.py <path-to-pipe.py> [--id ID] [--name NAME]

Auth: reads OPEN_WEBUI_BASE_URL (default http://localhost:3000) and the
required OPEN_WEBUI_API_KEY (an admin account's API key, Settings > Account
> API Keys in the web UI -- API keys must be enabled for the instance under
Admin Settings first) from the environment.

Create-vs-update: tries POST /api/v1/functions/create first; if the id is
already taken, falls back to POST /api/v1/functions/id/{id}/update. (The
GET /api/v1/functions/id/{id} endpoint returns 401, not 404, for a missing
id in this version -- see backend/open_webui/routers/functions.py's
get_function_by_id -- so branching on create's "id already registered"
error is the more reliable signal.)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_BASE_URL = 'http://localhost:3000'


def extract_frontmatter(content: str) -> dict:
    """Mirror backend/open_webui/utils/plugin.py's extract_frontmatter.

    Not imported directly -- this script is meant to run with a bare
    python3 outside the backend's venv/import path. Kept in sync by hand;
    it's a small, stable parser (see plugin.py:151-181).
    """
    frontmatter = {}
    lines = content.splitlines()
    if not lines or lines[0].strip() != '"""':
        return frontmatter

    for line in lines[1:]:
        if '"""' in line:
            break
        match = re.match(r'^\s*([a-z_]+):\s*(.*)\s*$', line, re.IGNORECASE)
        if match:
            key, value = match.groups()
            frontmatter[key.strip()] = value.strip()

    return frontmatter


def api_request(base_url: str, api_key: str, method: str, path: str, payload: dict) -> tuple[int, dict]:
    url = f'{base_url.rstrip("/")}{path}'
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read()
            return resp.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {'detail': body.decode('utf-8', errors='replace')}


def sync_pipe(base_url: str, api_key: str, function_id: str, name: str, content: str) -> None:
    frontmatter = extract_frontmatter(content)
    payload = {
        'id': function_id,
        'name': name,
        'content': content,
        'meta': {
            'description': frontmatter.get('description', ''),
            'manifest': frontmatter,
        },
    }

    status, body = api_request(base_url, api_key, 'POST', '/api/v1/functions/create', payload)
    if status == 200:
        # New functions are created inactive (FunctionModel's is_active
        # default -- FunctionForm doesn't carry it, see
        # backend/open_webui/models/functions.py:43-56,98-102) and
        # get_function_models() only lists active_only=True pipes, so the
        # model wouldn't show up in the dropdown without this.
        toggle_status, toggle_body = api_request(
            base_url, api_key, 'POST', f'/api/v1/functions/id/{function_id}/toggle', {}
        )
        if toggle_status == 200:
            print(f'Created and activated function "{function_id}".')
        else:
            print(f'Created function "{function_id}", but activating it failed (HTTP {toggle_status}): '
                  f'{toggle_body.get("detail", toggle_body)}. Activate it manually in Admin > Functions.')
        return

    if status == 400 and 'already registered' in str(body.get('detail', '')):
        status, body = api_request(
            base_url, api_key, 'POST', f'/api/v1/functions/id/{function_id}/update', payload
        )
        if status == 200:
            print(f'Updated function "{function_id}".')
            return

    print(f'Sync failed (HTTP {status}): {body.get("detail", body)}', file=sys.stderr)
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('path', type=Path, help='Path to the Pipe function .py source file')
    parser.add_argument('--id', help='Function id (default: filename stem, must be a valid Python identifier)')
    parser.add_argument('--name', help='Display name shown in the model dropdown (default: same as id)')
    args = parser.parse_args()

    if not args.path.is_file():
        parser.error(f'No such file: {args.path}')

    base_url = os.environ.get('OPEN_WEBUI_BASE_URL', DEFAULT_BASE_URL)
    api_key = os.environ.get('OPEN_WEBUI_API_KEY')
    if not api_key:
        parser.error('OPEN_WEBUI_API_KEY environment variable is required (admin account API key)')

    function_id = args.id or args.path.stem
    if not function_id.isidentifier():
        parser.error(f'Function id "{function_id}" is not a valid identifier; pass --id explicitly')

    content = args.path.read_text(encoding='utf-8')
    sync_pipe(base_url, api_key, function_id, args.name or function_id, content)


if __name__ == '__main__':
    main()
