# `reasoning_details` — the contract, the gotchas, the fix

> This document is the source of truth for how open-webui handles OpenRouter's
> `reasoning_details` field across capture, persistence, and outbound requests.
> If you're touching `messages.py`, the streaming handler in `middleware.py`,
> or the chat-history send path in `Chat.svelte`, read this first.
>
> Read top-to-bottom for full context, or jump:
> §11 if you're chasing a bug right now —
> §3 if you want concrete examples of what payloads look like on the wire —
> §16 if you're unsure what a term means.

---

## TL;DR — The One Hard Rule

**Every `rs_*` reasoning item id must appear in at most one assistant message in the
outbound conversation history.** Violate this and OpenAI Responses upstream rejects
with `"Duplicate item found with id rs_<id>. Remove duplicate items from your input
and try again."`, surfaced through OpenRouter as a generic `500 Internal Server
Error`. That's the whole rule. Everything else this document covers is
infrastructure to keep that invariant true.

The invariant is enforced in **one** place: `_dedup_reasoning_against` in
[`messages.py`](./messages.py), called from `_expand_assistant` and from the
legacy passthrough branch of `blocks_to_api_messages`. Every outbound chat
completion request funnels through that file.

---

## 1. The `reasoning_details` API contract

OpenRouter's reasoning-details field is a tagged-union array discriminated by the
`type` field. Three variants:

| `type` | Required payload | Common fields |
|---|---|---|
| `reasoning.summary` | `summary: string` | `id?`, `format`, `index` |
| `reasoning.encrypted` | `data: string` (base64 Fernet blob) | `id?`, `format`, `index` |
| `reasoning.text` | `text: string`, optional `signature: string` | `id?`, `format`, `index` |

`format` values seen in the wild: `openai-responses-v1`, `azure-openai-responses-v1`,
`xai-responses-v1`, `anthropic-claude-v1`, `google-gemini-v1`, `unknown`. We don't
parse `format` — it round-trips opaquely.

`id` is the OpenAI Responses item id (e.g. `rs_0df4800ca6234aeb016a049af38f48...`).
Encrypted items always have one; summary items frequently don't; text items vary.

`index` is the position of this item within the round's reasoning sequence. Used
internally by OpenRouter to keep order stable when chunks arrive interleaved.

**Official docs:** <https://openrouter.ai/docs/guides/best-practices/reasoning-tokens>
(read the "Preserving Reasoning" section in particular).

---

## 2. The streaming protocol (what the wire actually looks like)

The published docs describe a clean per-item structure. The wire reality for
`openai-responses-v1` is messier. Replaying a real round-2 stream from
`openai/gpt-5.4-mini` with `reasoning.effort=xhigh`:

```
data: {"choices":[{"delta":{"reasoning_details":[{"type":"reasoning.summary","summary":"**Crafting","index":0}]}}]}
data: {"choices":[{"delta":{"reasoning_details":[{"type":"reasoning.summary","summary":" a","index":0}]}}]}
data: {"choices":[{"delta":{"reasoning_details":[{"type":"reasoning.summary","summary":" weather","index":0}]}}]}
... 86 more summary fragments, all type=summary, all index=0, all no id ...
data: {"choices":[{"delta":{"reasoning_details":[{"type":"reasoning.summary","summary":" key!","index":0}]}}]}
data: {"choices":[{"delta":{"reasoning_details":[{"type":"reasoning.encrypted","data":"gAAAAAB...","id":"rs_X","index":0}]}}]}
```

**Key facts:**

1. **Summary streams in fragments.** The full summary string is assembled by
   concatenating `summary` from every chunk. Around 90 chunks for a medium-effort
   reasoning round is typical.
2. **Summary chunks have no `id`** and all share the same `index` (usually `0`).
3. **The encrypted item arrives as one chunk** with its full `data` blob, an
   `rs_*` id, and **the same `index` as the summary chunks** (also `0`).
4. **Summary and encrypted are separate items**, not chunks of the same item.
   They co-exist in the final `reasoning_details` array as two entries with the
   same index but different types.
5. **`data` and `text` also stream in fragments** (less common but documented),
   and must be concatenated like `summary`.

This shape directly drives the merge logic in `middleware.py` (see §6 Bug A).

---

## 3. Concrete examples (real captures)

Pulled from actual `openai/gpt-5.4-mini` traffic. Encrypted `data` blobs are
truncated to ~60 chars with `...`; in real traffic they're ~1300-3000 chars and
must be sent back byte-exact (see §13). The system/user content fields are
abbreviated where noted.

### 3.1 Trivial request, no reasoning needed

Some queries don't trigger reasoning even with `effort: high` set — the model
decides per turn.

Request:
```json
{
  "model": "openai/gpt-5.4-mini",
  "messages": [
    {"role": "user", "content": "What is 2+2? Just answer briefly."}
  ],
  "reasoning": {"effort": "low"}
}
```

Response (HTTP 200):
```json
{
  "id": "gen-1778686485-cDqfLFh00OXCkGLpZCqI",
  "model": "openai/gpt-5.4-mini-20260317",
  "choices": [{
    "index": 0,
    "finish_reason": "stop",
    "message": {"role": "assistant", "content": "4", "reasoning": null}
  }],
  "usage": {
    "prompt_tokens": 17,
    "completion_tokens": 5,
    "completion_tokens_details": {"reasoning_tokens": 0}
  }
}
```

`reasoning_details` is absent. `reasoning_tokens: 0` confirms the model didn't
think about it.

### 3.2 Reasoning + tool call (round 1)

Request:
```json
{
  "model": "openai/gpt-5.4-mini",
  "messages": [
    {"role": "system", "content": "You are an assistant. Think carefully before and after every tool call. Reason about what you learned and what to do next."},
    {"role": "user", "content": "Please look up the weather in Paris using the tool, think hard about it, then describe what to wear."}
  ],
  "reasoning": {"effort": "xhigh"},
  "tools": [{
    "type": "function",
    "function": {
      "name": "get_weather",
      "description": "Get weather for a city",
      "parameters": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"]
      }
    }
  }]
}
```

Response (HTTP 200):
```json
{
  "id": "gen-1778686496-2Jzf47Yuy5gr7iFKI4Lj",
  "choices": [{
    "finish_reason": "tool_calls",
    "message": {
      "role": "assistant",
      "content": null,
      "tool_calls": [{
        "id": "call_hbP2L7uhjPFHUao8i5kAcs2K",
        "type": "function",
        "index": 0,
        "function": {
          "name": "get_weather",
          "arguments": "{\"city\":\"Paris\"}"
        }
      }],
      "reasoning_details": [
        {
          "type": "reasoning.summary",
          "summary": "**Considering weather in Paris**\n\nI need to respond to the user about the current weather in Paris, and I should definitely use the weather tool for this. It makes sense to describe what they might want to wear based on the weather results...",
          "format": "openai-responses-v1",
          "index": 0
        },
        {
          "type": "reasoning.encrypted",
          "data": "gAAAAABqBJr1hfqgzqSmCPSKsG0_k3rbNoBzHJiMy-fuB5uqT3B1UqX7mFXF...",
          "format": "openai-responses-v1",
          "id": "rs_0df4800ca6234aeb016a049af38f488190b6a98cd37dd7f60d",
          "index": 1
        }
      ]
    }
  }],
  "usage": {
    "prompt_tokens": 53,
    "completion_tokens": 46,
    "completion_tokens_details": {"reasoning_tokens": 26}
  }
}
```

Things to notice:

- **Two reasoning items.** Summary at `index: 0` (no id), encrypted at `index: 1`
  (with `id`). They're independent items, not chunks of one item — both must
  ride along on follow-up requests if you want to preserve the reasoning chain.
- **`tool_calls[0].index: 0`** is a streaming-delta artifact. OpenRouter
  tolerates it on the way back (see §4). Don't strip.
- **`finish_reason: "tool_calls"`** is your cue to execute the tool and recurse.

### 3.3 Round 2 — sending the tool result back with preserved reasoning

This is the inflection point where preservation matters. The round-1 assistant
message must be sent back **exactly as received**, including its full
`reasoning_details` array. Then append the tool message and let the model
continue.

Request:
```json
{
  "model": "openai/gpt-5.4-mini",
  "reasoning": {"effort": "xhigh"},
  "messages": [
    {"role": "system", "content": "...same as round 1..."},
    {"role": "user", "content": "...same as round 1..."},
    {
      "role": "assistant",
      "content": null,
      "tool_calls": [{"id":"call_hbP2L7uhjPFHUao8i5kAcs2K","type":"function","index":0,"function":{"name":"get_weather","arguments":"{\"city\":\"Paris\"}"}}],
      "reasoning_details": [
        {"type":"reasoning.summary","summary":"**Considering weather in Paris**\n...","format":"openai-responses-v1","index":0},
        {"type":"reasoning.encrypted","data":"gAAAAABqBJr1hfqg...","format":"openai-responses-v1","id":"rs_0df4800ca6234aeb016a049af38f488190b6a98cd37dd7f60d","index":1}
      ]
    },
    {
      "role": "tool",
      "tool_call_id": "call_hbP2L7uhjPFHUao8i5kAcs2K",
      "content": "Sunny, 22C, light breeze"
    }
  ],
  "tools": [{"type":"function","function":{"name":"get_weather","description":"Get weather for a city","parameters":{"type":"object","properties":{"city":{"type":"string"}},"required":["city"]}}}]
}
```

Response (HTTP 200):
```json
{
  "choices": [{
    "finish_reason": "stop",
    "message": {
      "role": "assistant",
      "content": "The weather in Paris is sunny at 22C with a light breeze. Wear light layers — a t-shirt or light blouse, comfortable shoes, and bring a thin jacket for the breeze. Don't forget sunglasses.",
      "reasoning_details": [
        {"type":"reasoning.summary","summary":"**Providing weather advice**\n\nI need to respond with weather and clothing advice for Paris...","format":"openai-responses-v1","index":0},
        {"type":"reasoning.encrypted","data":"gAAAAABqBJsdt3O-...","format":"openai-responses-v1","id":"rs_0df4800ca6234aeb016a049b1b2a488190aa4a58ca83db5ca4","index":1}
      ]
    }
  }]
}
```

Note: round-2's encrypted item has a **different `rs_*` id** than round-1's
(`...049b1b2a...` vs `...049af38f...`). Each round mints fresh ids. Open-webui's
job on a subsequent turn (when the user replies with "thanks!") is to keep
BOTH the round-1 id AND the round-2 id in the history, each appearing exactly
once.

### 3.4 The duplicate-id 500 (production bug, pre-fix)

Before the fix in this PR, open-webui's `_expand_assistant` would emit the same
`rs_*` id on two assistant messages whenever round 2 didn't emit its own
reasoning (very common — short continuations like "Done." don't trigger
reasoning). The wire looked like:

```json
{
  "model": "openai/gpt-5.4-mini",
  "reasoning": {"effort": "xhigh"},
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {
      "role": "assistant",
      "content": null,
      "tool_calls": [{"id":"call_X","type":"function","function":{...}}],
      "reasoning_details": [
        {"type":"reasoning.summary","summary":"**Considering...**","index":0},
        {"type":"reasoning.encrypted","data":"gAAAAABqBJr1...","id":"rs_0df4800c...","index":1}
      ]
    },
    {"role": "tool", "tool_call_id": "call_X", "content": "Sunny, 22C"},
    {
      "role": "assistant",
      "content": "Done.",
      "reasoning_details": [
        {"type":"reasoning.summary","summary":"**Considering...**","index":0},
        {"type":"reasoning.encrypted","data":"gAAAAABqBJr1...","id":"rs_0df4800c...","index":1}
      ]
    },
    {"role": "user", "content": "thanks!"}
  ],
  "tools": [{...}]
}
```

`rs_0df4800c...` appears in BOTH the third message (tool-call assistant) and
the fifth message (final-text assistant). Response:

```json
{"error":{"message":"Internal Server Error","code":500}}
```

Upstream (visible only in OpenRouter's own logs): `Duplicate item found with id
rs_0df4800c.... Remove duplicate items from your input and try again.`

### 3.5 The same scenario, post-fix

Open-webui's patched `blocks_to_api_messages` strips the duplicate at the
output gate. The wire payload becomes:

```json
{
  "model": "openai/gpt-5.4-mini",
  "reasoning": {"effort": "xhigh"},
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {
      "role": "assistant",
      "content": null,
      "tool_calls": [{"id":"call_X","type":"function","function":{...}}],
      "reasoning_details": [
        {"type":"reasoning.summary","summary":"**Considering...**","index":0},
        {"type":"reasoning.encrypted","data":"gAAAAABqBJr1...","id":"rs_0df4800c...","index":1}
      ]
    },
    {"role": "tool", "tool_call_id": "call_X", "content": "Sunny, 22C"},
    {"role": "assistant", "content": "Done."},
    {"role": "user", "content": "thanks!"}
  ],
  "tools": [{...}]
}
```

The fifth message lost its duplicated `reasoning_details` array. (If round 2
HAD emitted its own reasoning with a fresh id, the fifth message would carry
just that fresh id — the duplicate of round 1's id would still be stripped.)

Response (HTTP 200):
```json
{
  "choices": [{
    "finish_reason": "stop",
    "message": {"role": "assistant", "content": "You're welcome!"}
  }]
}
```

### 3.6 Streaming round 2 — SSE chunk replay

For completeness, here's the same round-2 response delivered as an SSE stream
(`stream: true` in the request). The shape that the streaming merger has to
collapse back into the §3.3 response structure:

```
: OPENROUTER PROCESSING

data: {"id":"gen-...","choices":[{"delta":{"reasoning_details":[{"type":"reasoning.summary","summary":"**Providing","index":0}]}}]}

data: {"id":"gen-...","choices":[{"delta":{"reasoning_details":[{"type":"reasoning.summary","summary":" weather","index":0}]}}]}

... ~85 more summary fragments ...

data: {"id":"gen-...","choices":[{"delta":{"reasoning_details":[{"type":"reasoning.summary","summary":" key!","index":0}]}}]}

data: {"id":"gen-...","choices":[{"delta":{"reasoning_details":[{"type":"reasoning.encrypted","data":"gAAAAABqBJsdt3O-...","format":"openai-responses-v1","id":"rs_0df4800ca6234aeb016a049b3680f0819083f72baa5ced44f1","index":0}]}}]}

data: {"id":"gen-...","choices":[{"delta":{"content":"The","role":"assistant"},"finish_reason":null}]}

data: {"id":"gen-...","choices":[{"delta":{"content":" weather","role":"assistant"},"finish_reason":null}]}

... text content streams here ...

data: {"id":"gen-...","choices":[{"delta":{"content":"","role":"assistant"},"finish_reason":"stop"}],"usage":{"prompt_tokens":115,"completion_tokens":18,"completion_tokens_details":{"reasoning_tokens":0}}}

data: [DONE]
```

The encrypted chunk's `index: 0` is the same as the summary chunks'. They're
distinguished by `type`, not by `index`. The merger that came before this
fix matched by index alone and collapsed them into a single mixed-shape item
(see §6 Bug A).

### 3.7 Other providers — same field, different shapes

Anthropic Claude reasoning models use `format: "anthropic-claude-v1"` and
populate `reasoning.text` items with a `signature` field instead of
`reasoning.encrypted` items:

```json
{
  "reasoning_details": [
    {
      "type": "reasoning.text",
      "text": "Let me think about this step by step:\n1. First...",
      "signature": "sha256:abc123...",
      "id": "thinking_01abc...",
      "format": "anthropic-claude-v1",
      "index": 0
    }
  ]
}
```

Google Gemini reasoning uses `format: "google-gemini-v1"` and varies between
`reasoning.summary` and `reasoning.text` shapes depending on the model.

The dedup invariant is provider-agnostic: every `id`-bearing item, regardless
of format, must appear at most once in the conversation history. Items without
ids (typical for `reasoning.summary` from Anthropic, occasionally from OpenAI
on shorter rounds) pass through dedup unchanged — uniqueness only applies to
id-bearing items.

---

## 4. What the API tolerates vs. rejects (empirical, 21 curl tests)

We ran 21 isolated curl tests against `https://openrouter.ai/api/v1/chat/completions`
with `openai/gpt-5.4-mini`, `reasoning.effort=xhigh`, a registered function tool,
and one preserved tool-call round. Results:

### ✅ Tolerated (don't waste effort sanitizing these)

| Pattern | Status |
|---|---|
| Sending OpenRouter's literal multi-item output back verbatim | 200 |
| `summary` field present on a `reasoning.encrypted` item (mixed-shape from a buggy merge) | 200 |
| `index: 0` on `tool_calls[]` (a streaming-delta artifact some clients keep) | 200 |
| Missing `format` field on a reasoning item | 200 |
| Leading `\n` prepended to encrypted `data` | 200 |
| Reasoning items in reversed order within a message | 200 |
| "Orphaned" reasoning: items attached to a different assistant message than the one whose tool_calls they logically belong to | 200 |
| Empty `reasoning_details: []` array on a message | 200 |
| Tool result content as `[{"type":"text","text":"..."}]` array vs bare string | both 200 |

### ❌ Rejected

| Pattern | Status |
|---|---|
| **Same `rs_X` id in two assistant messages of the conversation history** | **500** ("Duplicate item found") |
| Single-byte change to encrypted `data` (Fernet integrity fails) | 500 |
| `data` blob paired with an `id` that didn't originally produce it | 500 |

**Implication:** OpenRouter's tolerance of the tagged-union discriminator is
much looser than the OpenAPI spec implies. We do **not** sanitize the per-type
field whitelist (`summary`-on-encrypted, etc.) because the wire happily accepts
the malformed shape. We only enforce the **one** hard rule (id uniqueness).

---

## 5. Open-webui's persistence model

A chat message is stored with these fields (the ones that matter for reasoning):

| Field | Shape | Purpose |
|---|---|---|
| `content_blocks` | `list[block]` (internal carrier) | Structured assistant output: `[text \| reasoning \| tool_calls \| code_interpreter]*`. The tool_calls block carries the round's `reasoning_details` inline. **Never sent to upstream** — `blocks_to_api_messages` strips it. |
| `reasoning_details_per_round` | `list[list[reasoning_item]]` | One entry per stream-handler invocation, in emission order. Empty rounds are stored as `[]` so `len(per_round) == emission_count`. **Never sent to upstream** — stripped by `blocks_to_api_messages`. |
| `reasoning_details` | `list[reasoning_item]` (flat) | Concatenation of every `per_round` entry. **Sent to upstream** for legacy assistant messages that lack `content_blocks` (passthrough branch). For modern content_blocks-bearing messages, `_expand_assistant` rebuilds the per-emission slices from `per_round`. |

The dual-storage exists because:
- `content_blocks` + `per_round` are the precise structured form (lossless reconstruction).
- `reasoning_details` (flat) is the legacy carrier shape that pre-content_blocks chats had — kept so old DB rows still round-trip.

### Where each field gets written

| Source | Sites in `middleware.py` |
|---|---|
| Streaming, realtime save | `~L2725` (inside `stream_body_handler`'s value handler) |
| Streaming, deferred save at end of stream | `~L3506` |
| Streaming, cancel path | `~L3571` |
| Non-streaming response | `~L1772-1786` |

All four sites write both `per_round` and flat `reasoning_details`. **Symmetry
is load-bearing**: a chat persisted via any of these paths must read back through
`_expand_assistant` cleanly.

---

## 6. The fix architecture (and the bugs it replaced)

Four classes of bug used to exist. Each had a clean fix.

### Bug A — Streaming merge confused summary with encrypted

**Where:** `middleware.py` streaming handler, and the mirror in `Chat.svelte`.

**The bug.** The merger matched chunks by `id`. When a new chunk had an `id` but
no existing entry matched, it fell back to "id-less entry at the same index" —
which adopted the summary item (id-less, index 0) as the target for the encrypted
chunk (id-bearing, also index 0). After the adoption, `data` was appended,
`type` was overwritten to `reasoning.encrypted`, but the leftover `summary`
field stayed (because the encrypted chunk doesn't have a `summary` key to
clobber it). Result: one mixed-type item with both `summary` and `data`.

Worse, `summary` was in the overwrite loop, not the concat loop — so 89 summary
fragments collapsed to whatever the last fragment was (often just `"."` or `"!"`).
The actual reasoning summary text was silently destroyed.

**The fix.** Match by `(id, type)` instead of `id` alone, with a `(type, index)`
fallback for id-less chunks. Move `summary` to the concat loop alongside `text`
and `data`. The id-less fallback now only adopts when *type also matches*, so a
summary chunk and an encrypted chunk at the same index stay as distinct entries.

```python
existing = None
if detail_id is not None:
    existing = next(
        (d for d in reasoning_details
         if d.get("id") == detail_id and d.get("type") == detail_type),
        None,
    )
    if existing is None:  # adopt id-less entry only when type also matches
        existing = next(
            (d for d in reasoning_details
             if d.get("id") is None
             and d.get("type") == detail_type
             and d.get("index") == detail_idx),
            None,
        )
else:
    existing = next(
        (d for d in reasoning_details
         if d.get("type") == detail_type and d.get("index") == detail_idx),
        None,
    )

if existing is not None:
    if detail.get("text"):    existing["text"]    = (existing.get("text") or "")    + detail["text"]
    if detail.get("data"):    existing["data"]    = (existing.get("data") or "")    + detail["data"]
    if detail.get("summary"): existing["summary"] = (existing.get("summary") or "") + detail["summary"]
    for k in ("id", "signature", "format", "index"):  # type is matched on; never overwritten
        if detail.get(k) is not None:
            existing[k] = detail[k]
else:
    reasoning_details.append({**detail})
```

**Effect on the wire.** Pre-fix saved shape: `{type: "reasoning.encrypted",
summary: "!", data: "...", id: "rs_X"}`. Post-fix saved shape: two items —
`{type: "reasoning.summary", summary: "<full 452-char text>", index: 0}` and
`{type: "reasoning.encrypted", data: "<1764-char blob>", id: "rs_X", index: 0}`.

**Note.** OpenRouter empirically tolerates the pre-fix mixed shape (200 OK on
follow-up requests). So this bug did **not** by itself cause the user-visible
500. We still fixed it because (a) the truncated summary is silent data loss
the user cares about, and (b) it could become a 500 if OpenRouter ever tightens
its validator.

### Bug B — `per_round` was shorter than the emission count

**Where:** `middleware.py:~L2796-2802` and parallel sites at `~L3134-3140`
and `~L3413-3419`.

**The bug.** End-of-round tracking was guarded:

```python
if reasoning_details:
    round_reasoning_details.append(reasoning_details)
```

When a round emitted no reasoning (very common: GPT-5 series often emits zero
reasoning for short non-tool-call continuations like "Done." or "You're welcome!"),
the guard skipped the append. The invariant `len(per_round) == emission_count`
broke.

On replay, `_expand_assistant` would look up `per_round[1]` for the final-text
emission, find nothing, and fall back to the flat `reasoning_details` carrier
— which is the *concatenation of every round*, including round 0's. Round 0's
`rs_*` ids ended up on the final-text message in addition to the tool_calls
message. Boom — duplicate id, 500.

**The fix.** Always append, even when empty:

```python
round_reasoning_details.append(reasoning_details or [])
```

Now `len(per_round)` always tracks emission count. `_expand_assistant` reads
`per_round[1] = []` and honors it as "this round had no reasoning" — no fallback
fires.

### Bug C — Non-streaming save dropped `per_round`

**Where:** `middleware.py:~L1772-1786`.

**The bug.** Non-streaming responses (rare in practice — most chats stream, but
some tool-loop sub-paths can land here) only persisted the flat
`reasoning_details`, never `reasoning_details_per_round`. On replay, the lookup
in `_expand_assistant` saw `per_round = None` and fell back to flat for every
emission past the first, duplicating ids.

**The fix.** Save both:

```python
if reasoning_details:
    update_data["reasoning_details"] = reasoning_details
    update_data["reasoning_details_per_round"] = [reasoning_details]
```

Single-round response → single-element per_round list. Symmetric with streaming.

### Bug D — The flat-fallback footgun in `_expand_assistant`

**Where:** `messages.py`.

**The bug.** The pre-fix selector for each emission's reasoning_details was:

```python
def reasoning_for_emission(idx, fallback):
    if reasoning_details_per_round and idx < len(reasoning_details_per_round):
        return reasoning_details_per_round[idx]
    return fallback  # ← the flat reasoning_details, = union of all rounds
```

Even if Bugs B and C were fixed, this fallback would still misbehave under
legacy chats persisted before `per_round` existed: every emission would attach
the entire flat array, duplicating across messages.

**The fix.** Drop the silent flat-fallback inside `reasoning_for_emission` and
replace with an explicit "consume-once-on-emission-0" path. Combined with a
shared `seen_reasoning_ids` set threaded across the whole conversation, the
invariant becomes structural: each id is attached at the earliest emission that
wants it; every subsequent appearance is stripped.

```python
def take_per_round(idx):
    if reasoning_details_per_round and idx < len(reasoning_details_per_round):
        return reasoning_details_per_round[idx]
    return None

def consume_legacy_fallback():
    nonlocal legacy_fallback_consumed
    if legacy_fallback_consumed or not fallback_reasoning_details:
        return None
    legacy_fallback_consumed = True
    return fallback_reasoning_details

# Inside flush():
chosen = block_reasoning or take_per_round(emission_index)
if block_reasoning is None and per_round_entry is None and emission_index == 0:
    chosen = consume_legacy_fallback()
chosen = _dedup_reasoning_against(seen_reasoning_ids, chosen)
```

Three subtle properties of the new logic:

1. **`is None` vs `not chosen`.** `take_per_round(1) = []` (explicit empty) is
   honored as "this round had no reasoning, attach nothing". A `not chosen`
   check would conflate `[]` with "missing" and trigger the legacy fallback
   incorrectly.
2. **Legacy fallback only on emission 0.** For emissions ≥1, missing per_round
   means missing reasoning — never fall back to a flat array that might re-emit
   earlier ids.
3. **Dedup runs after every selection.** Even if the legacy fallback hands the
   whole flat list to emission 0, the dedup ensures subsequent emissions can't
   re-grab any of those ids via the per_round path.

---

## 7. The conversion pipeline (every path)

```
                    ┌────────────────────────────────────────────┐
                    │ Frontend POST /api/chat/completions        │
                    │ (initial msg, regenerate, edit, branch,    │
                    │  retry, resume from preserved tool ctx)    │
                    └─────────────────────┬──────────────────────┘
                                          │
                                          ▼
                    main.py:1409 chat_completion()
                          │
                          ▼
                    middleware.py:953 process_chat_payload()
                          │ (params, system prompt, features, tools,
                          │  filters, sources — no reasoning_details
                          │  touched)
                          ▼
                    utils/chat.py:163 generate_chat_completion()
                          │ (routes by model.owned_by)
                          ▼
                    routers/openai.py:1102 generate_chat_completion()
                          │
                          │  ⭐ THE SINGLE OUTBOUND GATE ⭐
                          ▼
                    routers/openai.py:1120
                    payload["messages"] = blocks_to_api_messages(...)
                          │   ↑ shared seen_reasoning_ids dedup runs here
                          │
                          ▼
                    aiohttp POST {url}/chat/completions
                          ▼
                    middleware.py:1383 process_chat_response()
                    (streaming handler + tool-call loop + code-interp loop)
                          │
                          │ Tool-call sub-loop at L3079 recursively
                          │ calls utils/chat.py:generate_chat_completion
                          │ — same path, same gate.
                          ▼
                    Code-interpreter sub-loop at L3358 — same.
```

### Paths that funnel through `blocks_to_api_messages` (so the fix covers them)

- Initial user message
- Regenerate / edit / branch / retry with `strip_provider`
- Resume from preserved tool context (`retryFromLastRequest` →
  `expandMessagesForToolResumption` in `Chat.svelte`)
- Live tool-call loop (`middleware.py:3079` recursive call)
- Live code-interpreter loop (`middleware.py:3358` recursive call)

### Paths that do NOT carry `reasoning_details` (so the fix is moot)

- **Tasks** — `routers/tasks.py` builds minimal content-only payloads for title
  generation, tag generation, follow-up generation, query generation,
  autocompletion, emoji generation, image prompt generation, MoA response.
  Never sets `reasoning_details`.
- **Ollama backend** — `convert_payload_openai_to_ollama` in `payload.py`
  discards `reasoning_details` on the way out. Ollama doesn't speak it.
- **Pipe (function) models** — `generate_function_chat_completion` is
  user-defined; if a pipe wraps OpenRouter, the user owns their own payload.
- **Direct chat completion** (`utils/chat.py:generate_direct_chat_completion`)
  is socket-mediated to a browser-attached model. Never reaches OpenRouter.
- **`chat_completed` / `chat_action`** run outlet/filter pipelines on existing
  responses. Do not call `generate_chat_completion`.

---

## 8. The streaming capture (write-side details)

In `middleware.py` inside `stream_body_handler`:

```
SSE chunk arrives
  → decode JSON
  → for each item in delta.reasoning_details:
      → find existing by (id, type) or (type, index)
      → if found: concat text/data/summary, overwrite signature/format/index/id
      → else: append a fresh copy

End of stream_body_handler:
  → if response_tool_calls present:
      tool_calls.append({tool_calls, reasoning_details})
  → round_reasoning_details.append(reasoning_details or [])  ⭐ even when empty

After end-of-stream cleanup:
  → save to DB:
      content_blocks            (the structured carrier)
      reasoning_details_per_round = [round0, round1, round2, …]
      reasoning_details         = flat concat (legacy carrier)
```

The `or []` on the per_round append is the keystone of Bug B's fix. Don't lose
it. Three sites in `middleware.py` do this — keep them in sync.

---

## 9. Frontend mirror (Chat.svelte)

The frontend independently captures the same SSE stream for live UI display.
Its merge logic in `src/lib/components/chat/Chat.svelte` (~L2293) must mirror
the backend exactly. Same `(id, type)` matching, same concat semantics for
`text`/`data`/`summary`, same id-less-with-type fallback. If they diverge, the
frontend's locally merged copy overwrites the backend's clean copy in the DB
via the `chatCompleted` POST path, undoing the backend fix.

Treat the two implementations as one logical merger expressed in two languages.
Change one, change the other.

---

## 10. Debugging playbook

When you're staring at a reasoning_details bug (this one or future ones).

### Step 1 — Capture the exact outbound request body

```bash
# In open-webui's config (.env or wherever):
ENABLE_API_DEBUG_LOGGING=true
```

Reproduce the bug. The server log will print `[API REQUEST] URL: ...` and
`[API REQUEST] Payload: {...}` for every outbound chat completion request.
Find the failing one (usually the last one before the user-visible error) and
save the payload to disk.

If you're debugging a streaming response, also capture the SSE deltas — those
are logged via `[STREAM] ...` and `[API RAW] {...}` (the latter when debug
logging is on, see `routers/openai.py:2342`).

### Step 2 — Confirm the bug is in the payload, not transport

```bash
curl -s -o response.json -w "%{http_code}" https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_KEY" \
  -H "Content-Type: application/json" \
  --data @captured_payload.json
```

If curl reproduces the failure, you've isolated to the payload bytes — auth,
transport, network are out of the picture. Continue to Step 3.

If curl succeeds, the bug is somewhere else: open-webui's HTTP layer
(`aiohttp` session at `routers/openai.py:1471`), auth header construction
(`get_headers_and_cookies`), or response handling.

### Step 3 — Bisect the payload

For 5xx errors with no useful upstream message, peel back the payload until
the error stops:

```bash
# Pin down which field is the trigger:
jq 'del(.messages[] | select(.role == "assistant").reasoning_details)' < captured.json > test1.json
# Re-send. If 200 now, it's in reasoning_details. If still 500, try:
jq 'del(.tools)' < test1.json > test2.json
# ... etc.
```

The §4 table tells you what to NOT bother stripping. The §11 catalog tells you
what to suspect first.

### Step 4 — Diff against a known-good payload from §3

The captures in §3 (especially 3.3 and 3.5) are byte-stable examples of what
WORKS and what FAILS. Diff your captured payload against the working shape.

### Step 5 — Once you have a hypothesis, write a unit test

`backend/open_webui/test/util/test_messages.py` (or a sibling file for new
classes of bugs) is the right place. Tests in this file are pure data — no
HTTP, no DB, no event loop. They run in milliseconds and lock invariants
in forever.

```bash
cd backend && python3 -m pytest open_webui/test/util/test_messages.py -v
```

### Step 6 — If touching the live tool-call loop, re-run the e2e

The tool loop in `middleware.py:3060-3090` is the trickiest path to test
without a live model. The simplest way is a real chat through the UI with
`ENABLE_API_DEBUG_LOGGING` on. Watch the [API REQUEST] lines per round and
verify each round's `reasoning_details` array.

---

## 11. Symptom → cause catalog

When a future bug looks similar to but distinct from the one this doc
documents, the first pass should be pattern matching. Find the symptom row;
read what to check first.

### Symptom: `500 Internal Server Error` from OpenRouter with empty body

| Most likely cause | Where to check |
|---|---|
| **Duplicate `rs_*` id across two assistant messages** | Run `jq '[.messages[] \| select(.role=="assistant") \| .reasoning_details[]?.id] \| group_by(.) \| map(select(length>1))'` on the captured payload. Non-empty result = the bug. See §6 Bug B/C/D for the upstream causes. |
| **Byte-corrupted encrypted `data`** (Fernet integrity fail) | Compare the saved `data` blob length against what was originally received from upstream. Any modification breaks decryption. |
| **Mismatched `data`/`id` pair** | If the persistence layer ever fragmented a reasoning item and reassembled it with wrong association, the encrypted blob and id won't pair correctly. |
| **OpenRouter / upstream incident** | Check <https://status.openrouter.ai>. Try a different model or a non-reasoning model. |

### Symptom: `400 Bad Request` from upstream

| Most likely cause | Where to check |
|---|---|
| **"Extra inputs are not permitted"** | Strict-mode endpoint rejecting a field. Common with direct OpenAI / Azure endpoints (less so with OpenRouter). Common offenders: `index` on `tool_calls[]`, custom `cache_control` shapes, provider-specific fields routed to a different provider. |
| **Bad tool_call_id reference** | A tool message references an id that no preceding assistant message provided in `tool_calls[]`. |
| **Malformed `messages` shape** | Missing required field on a role (e.g. `tool_call_id` on a tool message). |
| **Token limit** | Prompt + completion exceeds context window. Inspect `usage` if any prior response is available. |

### Symptom: Reasoning summary appears truncated to one character

| Most likely cause | Where to check |
|---|---|
| **Streaming merger overwriting instead of concatenating** | Confirm `summary` is in the concat group of the merger, not the overwrite loop. See §6 Bug A. |
| **Wrong matching key in merger** | Confirm matcher is `(id, type)` or `(type, index)`, not `index` alone. |

### Symptom: `reasoning_details` is missing on a follow-up that should have it

| Most likely cause | Where to check |
|---|---|
| **`blocks_to_api_messages` dropped it** | If the message had no `content_blocks` and went through the passthrough branch, the dedup pass might have stripped everything. Check if all ids were duplicates. |
| **`_expand_assistant` couldn't find it** | Both `tool_calls_block.reasoning_details` and `per_round[idx]` are absent. Legacy fallback only fires on emission 0. |
| **Frontend didn't store it** | Check `Chat.svelte:2293` merger ran. Look for the message having `reasoning_details_per_round` populated. |
| **Save path missed it** | Streaming cancel before end-of-stream, or non-streaming save (now fixed by §6 Bug C). |

### Symptom: Same reasoning item appears TWICE within one assistant message

| Most likely cause | Where to check |
|---|---|
| **Dedup pass not running** | `_dedup_reasoning_against` is supposed to run on every selected reasoning list. Check the `seen_reasoning_ids` set is being threaded into `_expand_assistant`. |
| **Caller bypassed `blocks_to_api_messages`** | Some path constructed a payload directly without going through the gate. Grep for raw payload construction. |

### Symptom: First request works, follow-up 500s

| Most likely cause | Where to check |
|---|---|
| **Classic preservation bug.** First request has no prior reasoning to send back. Follow-up includes prior reasoning and that's where the duplicate / corruption / mismatch surfaces. | This is the canonical reasoning_details bug pattern. Apply Step 1-3 of the playbook. |

### Symptom: Mid-stream error in SSE (`finish_reason: "error"` in a chunk)

| Most likely cause | Where to check |
|---|---|
| **Provider error mid-generation** | OpenRouter sends `error` field at chunk top level AND `choices[0].finish_reason: "error"`. The streaming handler at `middleware.py:~L2406` catches this. |
| **Token cutoff** | `finish_reason: "length"` is technically the right signal for this, but some providers emit `error` instead. Check the chunk's `error` field for the message. |

### Symptom: Different LLM provider behaves differently on the same payload

Different providers enforce different strictness levels. OpenRouter is lax (see
§4). Direct OpenAI / Azure / Anthropic / Gemini may reject things OpenRouter
accepts. To isolate:

```bash
# OpenRouter
curl https://openrouter.ai/api/v1/chat/completions -H "Authorization: Bearer $OPENROUTER_KEY" -d @payload.json
# OpenAI direct (same payload — adjust auth)
curl https://api.openai.com/v1/chat/completions -H "Authorization: Bearer $OPENAI_KEY" -d @payload.json
```

If OpenRouter succeeds and OpenAI rejects, you're sending something OpenRouter
proxies but OpenAI rejects — typically extra fields or non-standard shapes.
This isn't an open-webui bug; it's a payload-conformance issue.

### Symptom: Caching not working (every request is full prompt cost)

| Most likely cause | Where to check |
|---|---|
| **Cache control marker on wrong message** | `apply_ephemeral_cache_control_to_last_message` in `utils/payload.py` puts it on the last message. Make sure the conversation history is stable (not getting reshuffled). |
| **Prompt drift between live and replay** | The whole reason `content_blocks` → `blocks_to_api_messages` exists is to make live and replay produce byte-identical messages. If a refactor diverges them, caching dies silently. |

---

## 12. Gotchas and worth-knowing-isms

- **Summary items have no `id`.** The dedup pass keeps them. Two messages can
  carry the same summary text — harmless, OpenRouter doesn't enforce uniqueness
  on summaries.
- **`data` blob integrity is byte-exact.** Don't `.strip()` whitespace, don't
  re-base64, don't trim. A single-character change makes Fernet decryption fail
  and OpenAI returns 500. Leading whitespace happens to be tolerated (Fernet's
  base64 layer ignores leading newlines) but don't rely on it.
- **Reasoning items can be "orphaned" across messages.** A reasoning item
  whose tool_calls belong to message A can validly be attached to message B as
  long as it appears in exactly one place. Order across messages doesn't
  matter; uniqueness does. We attach items to their natural emissions but the
  contract is laxer than that.
- **OpenAI Responses re-emits reasoning items across rounds?** In our streaming
  tests, no — each round emits fresh `rs_*` ids. Don't assume the model never
  references old reasoning, but we have no evidence it does. If a future model
  does re-emit, the dedup catches it correctly (keep first occurrence, drop
  subsequent).
- **Chat-paste artifacts.** A user pasting a captured payload into a file from
  a chat interface can inject literal `\n` characters into JSON keys and string
  values. We saw this cause a real-looking "duplicate id" that was actually a
  paste artifact: `"rs_0c2aad99dcd293d501\n6a0424d8837881a19505ddcedd890f9a"`.
  If a user reports a 500 and their payload was hand-edited, check for `\n` in
  identifier fields before assuming an open-webui bug.
- **Provider-specific format codes.** The `format` field of a reasoning item
  identifies the upstream model family (e.g. `openai-responses-v1`,
  `anthropic-claude-v1`). We don't parse it, but it must round-trip unchanged.
  If a model returns `format: "unknown"`, that's normal — pass it back as-is.
- **`reasoning_tokens: 0` in usage despite asking for reasoning.** The model
  decided this query didn't need reasoning, regardless of `effort` setting.
  Not a bug.

---

## 13. What we deliberately don't do

- **No per-type field whitelisting** (e.g. stripping `summary` from a
  `reasoning.encrypted` item). OpenRouter tolerates the mixed shape. Adding the
  whitelist would be schema purity at the cost of more code and another place
  for bugs to live.
- **No data migration** for already-persisted malformed chats. The convert-time
  dedup self-heals them on first replay. Migrations are heavier and unnecessary.
- **No client-side dedup in `Chat.svelte`.** The frontend forwards persisted
  shapes to the backend; the backend's single gate (`blocks_to_api_messages`)
  is the enforcement point. Adding another dedup site would create two sources
  of truth.

---

## 14. External references

- **OpenRouter reasoning tokens guide:**
  <https://openrouter.ai/docs/guides/best-practices/reasoning-tokens>
  (sections "Preserving Reasoning" and "Reasoning Details API Shape")
- **OpenAI Responses duplicate-item error**, confirmed via these reports:
  - `vercel/ai#7883`, `vercel/ai#10573`
  - `openai/openai-agents-js#425`
  - `cloudflare/agents#728`
  - `anomalyco/opencode#14716`
- **Streaming fragmentation issue** in `langchain-ai/langchain#36400` describes
  a similar class of bug from concatenating reasoning_details deltas wrong.
- **Orphaned reasoning** issue: `openclaw#19121`, `#19582` — "Item 'rs_…' of
  type 'reasoning' was provided without its required following item."

---

## 15. When this document is wrong

This document is true as of the OpenRouter API and the open-webui code at the
time of the fix. If OpenRouter changes their tagged-union validator to be
stricter (e.g. starts rejecting `summary` on `reasoning.encrypted`), the
tolerated/rejected table in §4 becomes outdated. Run the curl reproducer in §10
to refresh it.

If you find a 500 that the §4 table doesn't predict, capture the exact request
body via `ENABLE_API_DEBUG_LOGGING` and bisect using the playbook in §10.

---

## 16. Glossary

- **`rs_*` id** — A reasoning item identifier from OpenAI Responses, prefixed
  `rs_` (e.g. `rs_0df4800ca6234aeb...`). Unique per reasoning item within
  OpenAI's account/session scope. Used as the primary dedup key throughout
  this codebase.
- **emission** — One assistant message produced by `_expand_assistant` from
  the saved internal `content_blocks` structure. A turn with N tool-call
  rounds plus a final text response produces N+1 emissions (the tool-call
  ones include their paired tool message; the final text emission doesn't).
- **round** — One invocation of the upstream chat-completion endpoint within
  a single user turn. A tool-using turn has at least 2 rounds: the round that
  emits the tool_call, and the round that emits the final text after the tool
  result. Multi-tool-call turns have more.
- **per_round** — The `reasoning_details_per_round` field on a saved message.
  A list of lists; one inner list per stream-handler invocation, in emission
  order. Indexed by emission number (0 = first emission, etc.).
- **content_blocks** — The internal structured representation of an
  assistant message's output: a list of typed blocks (text, reasoning,
  tool_calls, code_interpreter). Lossless, supports replay-byte-stability
  with the live tool loop. Never sent over the wire.
- **flat `reasoning_details`** — The single concatenated array of all rounds'
  reasoning items, stored on the saved message alongside `per_round`.
  Necessary for legacy chats persisted before `per_round` existed; used as a
  read-time fallback for those (via `_expand_assistant`'s legacy-fallback path).
- **`blocks_to_api_messages`** — The conversion function in `messages.py`. Takes
  a list of internal messages (with `content_blocks` etc.) and returns
  OpenAI-API-shaped messages ready for outbound. The single output gate for
  every chat completion request. Where the dedup invariant is enforced.
- **`_expand_assistant`** — Per-message helper called by `blocks_to_api_messages`
  for any assistant message carrying `content_blocks`. Walks the blocks and
  emits one API message per tool-call round + a final text emission.
- **`seen_reasoning_ids`** — A `set[str]` threaded through `blocks_to_api_messages`
  into every `_expand_assistant` call AND through the legacy-passthrough branch.
  Records which `rs_*` ids have been attached to an output message; any later
  attempt to attach the same id is silently dropped. This set is what
  guarantees the One Hard Rule.
- **Fernet** — The encryption scheme OpenAI uses for `reasoning.encrypted`
  blobs. Symmetric AES with timestamp validation. Blobs start `gAAAAAB...`
  (the version byte + timestamp base64-encoded). Any byte modification breaks
  integrity and produces a 500.
- **legacy passthrough** — The branch in `blocks_to_api_messages` that handles
  assistant messages that have no `content_blocks` (pre-content_blocks-migration
  chats, or messages a backfill couldn't recover structurally). Just strips
  the internal carriers and passes the message through; we run a dedup pass
  on its `reasoning_details` to keep the invariant.
- **prompt cache drift** — The class of bug where the same conversation
  serialised at different times produces different byte sequences in the
  outbound API request, breaking upstream prompt caching. The whole reason
  `blocks_to_api_messages` exists (byte-identical live and replay output).
