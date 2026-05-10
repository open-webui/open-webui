"""
title: Observability metrics (stream)
author: vigneshwarrvenkat
version: 0.1

Open WebUI **filter** (`type: filter`): streams timing hints using the existing
`status` event type (`event_emitter`), so **no frontend changes** are required.
Metrics appear under the assistant message status area like other tooling status.

Paste this file into Admin → Functions → New → type **Filter**.
Enable globally or attach via model filter IDs as usual.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Callable, Iterable, Mapping, MutableMapping
import asyncio
import logging
import time

log = logging.getLogger(__name__)

AEmitter = Callable[[dict], asyncio.Future | Any]


def _iter_text_from_delta(delta: Mapping[str, Any]) -> Iterable[str]:
    parts: list[Any] = []
    for key in ('content', 'reasoning_content', 'reasoning', 'thinking'):
        v = delta.get(key)
        if isinstance(v, str) and v:
            parts.append(v)
    audio = delta.get('audio')
    if isinstance(audio, Mapping):
        t = audio.get('transcript')
        if isinstance(t, str) and t:
            parts.append(t)
    return parts


def _stream_key(metadata: Mapping[str, Any] | None) -> tuple[str | None, str | None] | None:
    if not metadata:
        return None
    cid = metadata.get('chat_id')
    mid = metadata.get('message_id')
    return (cid if isinstance(cid, str) else None, mid if isinstance(mid, str) else None)


class Filter:
    class Valves(BaseModel):
        priority: int = Field(default=101, description='Run near the end so counts see normalized chunks.')

    def __init__(self):
        self.valves = self.Valves()
        # Per (chat_id, message_id): timing + token estimate.
        self._state: MutableMapping[tuple[str, str], MutableMapping[str, Any]] = {}

    def _purge(self, key: tuple[str, str]) -> None:
        self._state.pop(key, None)

    async def _emit(
        self,
        emitter: AEmitter | None,
        *,
        description: str,
        done: bool,
    ) -> None:
        if not emitter:
            return
        payload = {
            'type': 'status',
            'data': {
                'done': done,
                'action': 'observability_metrics',
                'description': description,
                'hidden': False,
            },
        }
        res = emitter(payload)
        if asyncio.iscoroutine(res):
            await res

    async def stream(
        self,
        event: dict,
        __metadata__: dict | None = None,
        __event_emitter__: AEmitter | None = None,
    ) -> dict:
        meta = dict(__metadata__ or {})
        emitter = __event_emitter__

        keys = _stream_key(meta)
        if keys is None or keys[0] is None or keys[1] is None:
            return event

        st = self._state.setdefault(keys, {})
        mono_now = time.perf_counter()

        if 'mono_start' not in st:
            st['mono_start'] = mono_now

        # Token-ish estimate from completion chunks (streaming usage may still override later).
        choices = event.get('choices')
        delta: dict | None = None
        finish_reason = None
        usage = event.get('usage')
        try:
            if isinstance(choices, list) and choices:
                ch0 = choices[0]
                delta = dict(ch0.get('delta')) if isinstance(ch0.get('delta'), dict) else None
                finish_reason = ch0.get('finish_reason')
        except Exception as e:
            log.debug('observability filter parse delta: %s', e)

        if isinstance(delta, dict):
            chars = ''.join(_iter_text_from_delta(delta)).strip()
            if chars:
                if 'mono_first_body' not in st:
                    st['mono_first_body'] = mono_now
                    first_ms = max(1, round((mono_now - st['mono_start']) * 1000))
                    await self._emit(
                        emitter,
                        description=f'Latency: first model text after ~{first_ms} ms (server/stream view).',
                        done=False,
                    )
                # Rough token estimate when provider does not stream usage.
                st['approx_tokens'] = st.get('approx_tokens', 0) + max(1, round(len(chars) / 4))

        if isinstance(usage, Mapping) and usage:
            ct = usage.get('completion_tokens')
            if isinstance(ct, (int, float)) and ct > 0:
                st['completion_tokens'] = int(ct)

        # Finish only on real stream end — not on usage-only chunks mid-stream.
        terminal = False

        raw_type = event.get('type')
        try:
            if isinstance(choices, list) and choices and choices[0].get('finish_reason'):
                terminal = True
        except Exception:
            pass

        if raw_type in ('DONE', '[DONE]', 'done') or event.get('done') or finish_reason == 'stop':
            terminal = True

        if terminal:
            total_ms = max(1, round((mono_now - st['mono_start']) * 1000))

            mono_first = st.get('mono_first_body')
            ttft_ms = None
            if isinstance(mono_first, (float, int)):
                ttft_ms = max(1, round((mono_first - float(st['mono_start'])) * 1000))

            tokens = (
                st.get('completion_tokens')
                if isinstance(st.get('completion_tokens'), int)
                else st.get('approx_tokens')
            )
            avg_tps = None
            if isinstance(tokens, int) and tokens > 0 and mono_first:
                gen_ms = max(1e-9, mono_now - float(mono_first))
                avg_tps = round(tokens / gen_ms)

            summary_parts = [f'Done in ~{total_ms} ms (stream view).']
            if ttft_ms is not None:
                summary_parts.append(f'First text ~{ttft_ms} ms.')
            if isinstance(avg_tps, int):
                summary_parts.append(f'Approx throughput ~{avg_tps} tok/s.')

            summary = ' '.join(summary_parts)
            await self._emit(emitter, description=summary, done=True)

            try:
                # Also push usage envelope so the regular ⓘ tooltip updates when present.
                if isinstance(usage, Mapping) and usage:
                    emitter_raw = emitter
                    if emitter_raw:
                        usage_payload = {
                            'type': 'chat:completion',
                            'data': {
                                'usage': dict(usage),
                                'done': True,
                            },
                        }
                        resp = emitter_raw(usage_payload)
                        if asyncio.iscoroutine(resp):
                            await resp
            except Exception as e:
                log.debug('observability filter usage emit: %s', e)

            self._purge(keys)

        return event
