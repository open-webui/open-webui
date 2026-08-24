#!/usr/bin/env python3
"""Real deed-entry concurrency test: N concurrent, multi-turn, human-
approval-gated deed-ingestion conversations through the real claude_cli
Pipe + ichirouganaim_mcp, simulating the actual production workflow
instead of concurrency_test.sh's single-turn "echo a token" proxy.

Why this exists as a separate script, not a concurrency_test.sh flag: the
real deed-entry workflow (docs/prompts/example.standard-deed-prompt.md in
the ichirouganaim_mcp repo) is multi-turn and stops for an explicit human
"yes" before creating identity links or finalizing -- concurrency_test.sh
sends one message and reads one response. Simulating the approval
back-and-forth needs per-turn response parsing a bash+curl script can't
do cleanly.

Uses a DUMMY volume/series (not the real RB 1/32 Barbados Archives
volume) so every record this creates is trivially identifiable and
removable afterward -- see DUMMY_VOLUME/DUMMY_SERIES/DUMMY_REPOSITORY
below.

Spends real, substantial Claude usage: each worker runs a full multi-step
tool-calling conversation (list_workflows, get_workflow, record/event/
party creation, finalize), not a single short reply. Start with
--workers 1 to validate the harness itself before any real concurrency.

Usage:
  export OPEN_WEBUI_API_KEY=sk-...
  python3 deed_concurrency_test.py --workers 1
  python3 deed_concurrency_test.py --workers 5 --base-url http://localhost:3000
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROMPT_FILE = Path(
    '/Users/IanBarrow/code/FULL-ICHI/ichirouganaim_mcp/docs/prompts/example.standard-deed-prompt.md'
)

# Deliberately fake -- never the real archival volume -- so every record
# this test creates is trivially identifiable and separable from real
# archival data.
DUMMY_SERIES = 'CONCURRENCY-TEST'
DUMMY_VOLUME = f'CONCURRENCY-TEST-VOL-{int(time.time())}'
DUMMY_REPOSITORY = 'Automated concurrency test -- not a real archive'

DEEDS = [
    (
        'My first deed has a date of March 1696. It recountes Gyles Duse and his wife '
        'Elizabeth selling for thirteen pounds sterling a piece of land that is 3/4 '
        'acres to James Ennis.'
    ),
    (
        'I have a January 1696 deed in which James Enis, Mary enis, and Sarah Gibbons '
        'sell 7 acres of land in St. George parish to Danby Hennis fo 135 pounds '
        'sterling. It\'s witnessed by Michael Mahon, Thomas Nash, and Robert Wye, and '
        'the notary is listed as C. Collins.'
    ),
    (
        'I see one William Hutchins (by profession a tailor) buying, from his father '
        '(also William Hutchins), for fifty pounds sterling, three acres of land off '
        'of his father\'s plantation. This plantation was in the parish of St. Peters '
        'and neighbored by lands owned by Edward Harrison, Scott Easse, Edward Scott, '
        'and Henry Baker. It was entered in the register on March 16, 1696. In this '
        'deed, the son is sometimes also referred to as "William Hutchins Jr." and '
        'the father as "William Hutchins Sr."'
    ),
]

APPROVAL_CUES = re.compile(
    r'(waiting for your|your approval|shall i proceed|please confirm|confirm before|'
    r'awaiting your|explicit yes|yes to finalize|do you approve|may i proceed|'
    r'ready to finalize|ready when you)',
    re.I,
)
DONE_CUES = re.compile(r'\*\*status\*\*\s*:', re.I)
MAX_TURNS_PER_DEED = 10


def build_standing_instructions() -> str:
    text = PROMPT_FILE.read_text(encoding='utf-8')
    text = text.replace('RB 1', DUMMY_SERIES).replace('RB 1/32', DUMMY_VOLUME)
    text = text.replace(
        'Barbados Department of Archives, St. Michael, Barbados', DUMMY_REPOSITORY
    )
    text += (
        f'\n\n---\nThis is an automated test run with dummy data, not a real archival '
        f'session. The volume/series above ({DUMMY_SERIES} / {DUMMY_VOLUME}) is a '
        f'deliberately fake placeholder so test records are identifiable and '
        f'removable afterward -- proceed as if a human operator had already reviewed '
        f'and approved it. You have blanket pre-approval for every confirmation this '
        f'workflow would normally stop for in this session, including identity links '
        f'and finalization -- proceed through the entire workflow for each deed '
        f'without pausing to ask, but still tell me what you did at each step per the '
        f'reporting format below.\n'
    )
    return text


def post_completion(base_url: str, api_key: str, payload: dict) -> tuple[str, bool]:
    """Reads the full response body via resp.read() rather than iterating
    line-by-line -- confirmed live this matters, not a style choice: a
    fast, no-tool-call response parsed fine either way, but a real
    multi-minute, tool-calling response consistently came back as zero
    parsed lines under line-iteration, with no exception raised (silently
    empty, not a caught error) -- reproducible, not a fluke. Reading the
    whole body first sidesteps whatever buffering assumption line
    iteration was making about a long, gappy chunked stream. See
    decisions.md for the live comparison.
    """
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        f'{base_url}/api/chat/completions',
        data=data,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    content = ''
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
        for line in raw.splitlines():
            line = line.strip()
            if not line.startswith('data:'):
                continue
            payload_str = line[len('data:') :].strip()
            if payload_str == '[DONE]':
                continue
            try:
                obj = json.loads(payload_str)
            except json.JSONDecodeError:
                continue
            choices = obj.get('choices', [])
            if choices:
                delta = choices[0].get('delta', {})
                content += delta.get('content') or ''
        return content, True
    except Exception as e:
        return f'[request error: {type(e).__name__}: {e}]', False


def send_turn(
    base_url: str,
    api_key: str,
    chat_id: str,
    assistant_id: str,
    user_message_id: str,
    parent_assistant_id: str | None,
    content: str,
    history: list[dict],
) -> tuple[str, bool]:
    history.append({'role': 'user', 'content': content})
    payload = {
        'model': 'claude_cli',
        'chat_id': chat_id,
        'id': assistant_id,
        'parent_id': parent_assistant_id,
        'user_message': {
            'id': user_message_id,
            'parentId': parent_assistant_id,
            'role': 'user',
            'content': content,
            'childrenIds': [],
        },
        'messages': history,
        'stream': True,
    }
    response_text, ok = post_completion(base_url, api_key, payload)
    history.append({'role': 'assistant', 'content': response_text})
    return response_text, ok


def create_chat(base_url: str, api_key: str, title: str) -> str:
    """Pre-create the chat via /api/v1/chats/new rather than letting
    /api/chat/completions auto-provision one on a chat_id-less first turn.
    Confirmed live this matters: providing our own chat_id on turn 1 (so
    later turns can reference it) makes main.py's own is_new_chat check
    False (it requires *no* chat_id present), routing turn 1 into the
    "existing chat" branch for a chat that doesn't exist yet -- silently
    no-ops (200 OK, empty response, chat never actually created). Pre-
    creating it here means every turn, including the first, consistently
    hits the "existing chat" branch for a chat that's genuinely there.
    """
    req = urllib.request.Request(
        f'{base_url}/api/v1/chats/new',
        data=json.dumps(
            {'chat': {'title': title, 'models': ['claude_cli'], 'history': {'messages': {}, 'currentId': None}, 'messages': []}}
        ).encode('utf-8'),
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))['id']


def run_conversation(base_url: str, api_key: str, worker_idx: int, deed_text: str) -> dict:
    chat_id = create_chat(base_url, api_key, f'deed-concurrency-test-worker-{worker_idx}')
    history: list[dict] = []
    transcript: list[dict] = []
    last_assistant_id: str | None = None

    def turn(content: str, label: str) -> str:
        nonlocal last_assistant_id
        assistant_id = str(uuid.uuid4())
        user_message_id = str(uuid.uuid4())
        text, ok = send_turn(
            base_url, api_key, chat_id, assistant_id, user_message_id, last_assistant_id, content, history
        )
        last_assistant_id = assistant_id
        transcript.append({'label': label, 'sent': content[:200], 'received': text, 'ok': ok})
        return text

    standing = build_standing_instructions()
    resp = turn(standing, 'standing_instructions')

    resp = turn(
        f'Yes, please use {DUMMY_VOLUME} (series {DUMMY_SERIES}) as confirmed -- proceed.',
        'confirm_volume',
    )

    resp = turn(deed_text, 'deed')

    turns_used = 0
    while APPROVAL_CUES.search(resp) and not DONE_CUES.search(resp) and turns_used < MAX_TURNS_PER_DEED:
        resp = turn('Yes, approved -- proceed.', f'approval_{turns_used}')
        turns_used += 1

    success = all(t['ok'] for t in transcript) and DONE_CUES.search(resp) is not None
    return {
        'worker': worker_idx,
        'chat_id': chat_id,
        'success': success,
        'turns': len(transcript),
        'transcript': transcript,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, required=True)
    parser.add_argument('--base-url', default=os.environ.get('OPEN_WEBUI_BASE_URL', 'http://localhost:3000'))
    parser.add_argument('--out', default=None, help='Write full transcripts JSON here')
    args = parser.parse_args()

    api_key = os.environ.get('OPEN_WEBUI_API_KEY')
    if not api_key:
        print('Error: OPEN_WEBUI_API_KEY not set', file=sys.stderr)
        sys.exit(1)

    print(f'=== Deed concurrency test: {args.workers} worker(s), dummy volume {DUMMY_VOLUME} ===')

    container = os.environ.get('OPEN_WEBUI_CONTAINER', 'open-webui')
    mem_samples: list[str] = []

    def sample_memory() -> None:
        try:
            out = subprocess.run(
                ['docker', 'stats', '--no-stream', '--format', '{{.MemUsage}} {{.MemPerc}} {{.PIDs}}', container],
                capture_output=True,
                text=True,
                timeout=5,
            )
            mem_samples.append(out.stdout.strip())
        except Exception as e:
            mem_samples.append(f'CONTAINER_UNREACHABLE ({e})')

    sample_memory()
    start = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(run_conversation, args.base_url, api_key, i, DEEDS[i % len(DEEDS)]): i
            for i in range(args.workers)
        }
        for fut in as_completed(futures):
            sample_memory()
            results.append(fut.result())
    sample_memory()
    elapsed = time.time() - start

    print(f'--> All {args.workers} conversation(s) finished in {elapsed:.0f}s')
    passed = sum(1 for r in results if r['success'])
    print(f'=== Result: {passed}/{args.workers} succeeded ===')
    for r in sorted(results, key=lambda r: r['worker']):
        status = 'OK' if r['success'] else 'FAIL'
        print(f"  worker {r['worker']}: {status} ({r['turns']} turns, chat_id={r['chat_id']})")

    print('--> Container memory samples during run:')
    for s in mem_samples:
        print(f'  {s}')

    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=2), encoding='utf-8')
        print(f'--> Full transcripts written to {args.out}')

    sys.exit(0 if passed == args.workers else 1)


if __name__ == '__main__':
    main()
