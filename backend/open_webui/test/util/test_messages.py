"""Unit tests for `utils.messages.blocks_to_api_messages` and `_expand_assistant`.

The invariant under test: every `rs_*` reasoning id appears in at most one
assistant message in the output. OpenAI Responses upstreams reject conversation
histories with duplicate item ids ("Duplicate item found with id rs_<id>") and
OpenRouter surfaces that as a generic 500. The tests below cover every
production permutation that can produce a duplicate before the fix.
"""

from open_webui.utils.messages import _expand_assistant, blocks_to_api_messages


def _enc(rs_id, data="DATA"):
    return {
        "type": "reasoning.encrypted",
        "id": rs_id,
        "data": data,
        "format": "openai-responses-v1",
        "index": 0,
    }


def _summary(text="thinking", index=0):
    return {
        "type": "reasoning.summary",
        "summary": text,
        "format": "openai-responses-v1",
        "index": index,
    }


def _tool_calls_block(call_id="c1", reasoning=None, result="ok"):
    block = {
        "type": "tool_calls",
        "content": [
            {
                "id": call_id,
                "type": "function",
                "function": {"name": "x", "arguments": "{}"},
            }
        ],
        "results": [{"tool_call_id": call_id, "content": result}],
    }
    if reasoning is not None:
        block["reasoning_details"] = reasoning
    return block


def _text_block(content):
    return {"type": "text", "content": content}


def _ids(message):
    return [
        d.get("id")
        for d in (message.get("reasoning_details") or [])
        if d.get("id")
    ]


def _all_ids(messages):
    ids = []
    for m in messages:
        if m.get("role") == "assistant":
            ids.extend(_ids(m))
    return ids


def _assert_no_dups(messages):
    ids = _all_ids(messages)
    assert len(ids) == len(set(ids)), f"duplicate rs_* ids: {ids}"


# -- Trigger-A scenarios: per-round shorter than emissions ---------------------


def test_round2_emitted_no_reasoning_does_not_duplicate_round1():
    """User's exact reported bug. Pre-fix: msg#5 gets rs_A again via flat
    fallback → 500. Post-fix: dedup catches it → msg#5 has no reasoning."""
    out = blocks_to_api_messages(
        [
            {"role": "user", "content": "ask"},
            {
                "role": "assistant",
                "content_blocks": [
                    _tool_calls_block(reasoning=[_enc("rs_A")]),
                    _text_block("Done."),
                ],
                # Pre-fix persisted shape: round 2 had no reasoning, the
                # `if reasoning_details:` guard skipped it, so per_round
                # length is 1 even though there are two emissions.
                "reasoning_details_per_round": [[_enc("rs_A")]],
                "reasoning_details": [_enc("rs_A")],
            },
            {"role": "user", "content": "thanks"},
        ]
    )
    _assert_no_dups(out)
    # msg#3 keeps rs_A from tool_calls_block.reasoning_details
    assert _ids(out[1]) == ["rs_A"]
    # final-text emission gets nothing (per_round[1] missing, no legacy fallback
    # consumed for non-zero emission)
    assert out[3]["role"] == "assistant"
    assert _ids(out[3]) == []


def test_round2_with_empty_per_round_entry_after_fix():
    """Post-fix persisted shape: round 2 explicitly stored as []."""
    out = blocks_to_api_messages(
        [
            {"role": "user", "content": "ask"},
            {
                "role": "assistant",
                "content_blocks": [
                    _tool_calls_block(reasoning=[_enc("rs_A")]),
                    _text_block("Done."),
                ],
                "reasoning_details_per_round": [[_enc("rs_A")], []],
                "reasoning_details": [_enc("rs_A")],
            },
        ]
    )
    _assert_no_dups(out)
    assert _ids(out[1]) == ["rs_A"]


def test_round2_with_its_own_reasoning_keeps_both():
    """Happy path: each round has its own unique reasoning."""
    out = blocks_to_api_messages(
        [
            {
                "role": "assistant",
                "content_blocks": [
                    _tool_calls_block(reasoning=[_enc("rs_A")]),
                    _text_block("Done."),
                ],
                "reasoning_details_per_round": [[_enc("rs_A")], [_enc("rs_B")]],
            },
        ]
    )
    _assert_no_dups(out)
    assert _ids(out[0]) == ["rs_A"]
    assert _ids(out[2]) == ["rs_B"]


# -- Trigger-B scenarios: legacy chats with no per_round -----------------------


def test_legacy_flat_only_attaches_to_first_emission_then_dedups():
    """Pre-per_round chats only persisted the flat `reasoning_details`. Legacy
    fallback attaches it to emission 0 (the tool_calls emission), dedup keeps
    its ids off subsequent emissions."""
    out = blocks_to_api_messages(
        [
            {
                "role": "assistant",
                "content_blocks": [
                    _tool_calls_block(),  # no reasoning_details on the block
                    _text_block("Done."),
                ],
                # per_round absent entirely
                "reasoning_details": [_enc("rs_A"), _enc("rs_B", data="BBB")],
            },
        ]
    )
    _assert_no_dups(out)
    # Both items attach to the first emission (legacy chats had no way to know
    # which round each item came from).
    assert _ids(out[0]) == ["rs_A", "rs_B"]
    # Trailing text gets nothing.
    assert _ids(out[2]) == []


# -- Trigger via legacy passthrough (no content_blocks at all) ----------------


def test_legacy_passthrough_duplicates_are_stripped():
    """A chat persisted before the content_blocks migration may have two
    assistant messages that legitimately carried the same `rs_*` (e.g. because
    a prior version of open-webui copied flat reasoning onto both). The
    passthrough-branch dedup catches them."""
    out = blocks_to_api_messages(
        [
            {"role": "user", "content": "u1"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "x", "arguments": "{}"},
                    }
                ],
                "reasoning_details": [_enc("rs_A")],
            },
            {"role": "tool", "tool_call_id": "c1", "content": "r"},
            {
                "role": "assistant",
                "content": "Done.",
                "reasoning_details": [_enc("rs_A")],  # duplicate
            },
            {"role": "user", "content": "u2"},
        ]
    )
    _assert_no_dups(out)
    assert _ids(out[1]) == ["rs_A"]
    # second assistant message gets the dup stripped → reasoning_details
    # absent or empty
    assert _ids(out[3]) == []


# -- Multi-turn / multi-tool-round --------------------------------------------


def test_three_turn_conversation_keeps_each_turns_reasoning():
    out = blocks_to_api_messages(
        [
            {"role": "user", "content": "u1"},
            {
                "role": "assistant",
                "content_blocks": [
                    _tool_calls_block(reasoning=[_enc("rs_A")]),
                    _text_block("Done."),
                ],
                "reasoning_details_per_round": [[_enc("rs_A")], []],
            },
            {"role": "user", "content": "u2"},
            {
                "role": "assistant",
                "content_blocks": [_text_block("Sure.")],
                "reasoning_details_per_round": [[_enc("rs_B")]],
            },
            {"role": "user", "content": "u3"},
        ]
    )
    _assert_no_dups(out)
    assert _ids(out[1]) == ["rs_A"]
    # turn 2's text emission carries rs_B
    assistant_turns = [m for m in out if m["role"] == "assistant"]
    assert _ids(assistant_turns[-1]) == ["rs_B"]


def test_multi_tool_round_each_emission_keeps_its_own_reasoning():
    out = blocks_to_api_messages(
        [
            {
                "role": "assistant",
                "content_blocks": [
                    _tool_calls_block(call_id="c1", reasoning=[_enc("rs_A")]),
                    _tool_calls_block(call_id="c2", reasoning=[_enc("rs_B")]),
                    _text_block("Done."),
                ],
                "reasoning_details_per_round": [
                    [_enc("rs_A")],
                    [_enc("rs_B")],
                    [_enc("rs_C")],
                ],
            },
        ]
    )
    _assert_no_dups(out)
    asst = [m for m in out if m["role"] == "assistant"]
    assert _ids(asst[0]) == ["rs_A"]
    assert _ids(asst[1]) == ["rs_B"]
    assert _ids(asst[2]) == ["rs_C"]


# -- Defensive: cross-message duplicates that *shouldn't* happen but do --------


def test_global_seen_ids_strips_cross_turn_duplicates():
    """Defensive: even if two distinct assistant turns somehow carry the same
    `rs_*` id (e.g. a corrupted persisted state or a buggy older save path),
    the global dedup keeps it from reaching upstream."""
    out = blocks_to_api_messages(
        [
            {
                "role": "assistant",
                "content_blocks": [_text_block("Hi.")],
                "reasoning_details_per_round": [[_enc("rs_A")]],
            },
            {"role": "user", "content": "u2"},
            {
                "role": "assistant",
                "content_blocks": [_text_block("Yo.")],
                "reasoning_details_per_round": [[_enc("rs_A")]],  # collides
            },
        ]
    )
    _assert_no_dups(out)


# -- Cancel paths --------------------------------------------------------------


def test_cancel_mid_tool_keeps_tool_call_emission_only():
    out = blocks_to_api_messages(
        [
            {
                "role": "assistant",
                "content_blocks": [
                    {
                        "type": "tool_calls",
                        "content": [
                            {
                                "id": "c1",
                                "type": "function",
                                "function": {"name": "x", "arguments": "{}"},
                            }
                        ],
                        "reasoning_details": [_enc("rs_A")],
                        # no results — cancelled before tool ran
                    },
                ],
                "reasoning_details_per_round": [[_enc("rs_A")]],
            },
        ]
    )
    _assert_no_dups(out)
    assert out[0]["role"] == "assistant"
    assert _ids(out[0]) == ["rs_A"]
    # no tool message because no results were captured
    assert not any(m["role"] == "tool" for m in out)


def test_cancel_before_any_reasoning_emits_clean_message():
    out = blocks_to_api_messages(
        [
            {
                "role": "assistant",
                "content_blocks": [_text_block("Partial...")],
                "reasoning_details_per_round": [],
                "reasoning_details": [],
            },
        ]
    )
    _assert_no_dups(out)
    assert out[0]["content"] == "Partial..."
    assert "reasoning_details" not in out[0]


# -- Summary items (no id) ---------------------------------------------------


def test_summary_only_items_are_never_deduped():
    """Summary items have no `id`. They can legitimately appear in multiple
    messages; the dedup must not touch them."""
    out = blocks_to_api_messages(
        [
            {
                "role": "assistant",
                "content_blocks": [_text_block("Hi.")],
                "reasoning_details_per_round": [[_summary("first")]],
            },
            {"role": "user", "content": "x"},
            {
                "role": "assistant",
                "content_blocks": [_text_block("Yo.")],
                "reasoning_details_per_round": [[_summary("second")]],
            },
        ]
    )
    # No id-based dups (both summaries have no id, so trivially no dup)
    _assert_no_dups(out)
    asst = [m for m in out if m["role"] == "assistant"]
    assert asst[0]["reasoning_details"][0]["summary"] == "first"
    assert asst[1]["reasoning_details"][0]["summary"] == "second"


# -- Live tool-call loop in-flight assistant ----------------------------------


def test_live_loop_in_flight_assistant_does_not_emit_empty_trailer():
    """The live tool loop appends an empty text_block placeholder to
    content_blocks and recurses into `generate_chat_completion` with per_round
    that still only has round 1's reasoning. The empty trailer must not
    materialise as a malformed assistant message — it has no content, no
    tool_calls, and no reasoning to carry."""
    out = _expand_assistant(
        content_blocks=[
            _tool_calls_block(reasoning=[_enc("rs_A")]),
            _text_block(""),
        ],
        reasoning_details_per_round=[[_enc("rs_A")]],
    )
    # one assistant (the tool_calls) and one tool result, no trailing emission
    assert [m["role"] for m in out] == ["assistant", "tool"]
    _assert_no_dups(out)


# -- Reasoning-only trailing emission (legacy edge) ---------------------------


def test_empty_content_blocks_with_per_round_reasoning_emits_trailing_message():
    """Legacy reasoning-only saves: content_blocks ended up empty but the
    saved per_round still has reasoning. Preserve it as a content="" message."""
    out = _expand_assistant(
        content_blocks=[],
        reasoning_details_per_round=[[_enc("rs_A")]],
    )
    assert len(out) == 1
    assert out[0]["role"] == "assistant"
    assert out[0]["content"] == ""
    assert _ids(out[0]) == ["rs_A"]


# -- Internal carriers stripped on output -------------------------------------


def test_content_blocks_and_per_round_never_leak_to_upstream():
    out = blocks_to_api_messages(
        [
            {
                "role": "assistant",
                "content_blocks": [_text_block("Hi.")],
                "reasoning_details_per_round": [[_enc("rs_A")]],
                "reasoning_details": [_enc("rs_A")],
            },
        ]
    )
    for m in out:
        assert "content_blocks" not in m
        assert "reasoning_details_per_round" not in m


# -- Tool result content shape ------------------------------------------------


def test_tool_result_is_text_part_list_for_cache_control_compatibility():
    """Tool result content travels as `[{type: "text", text: "..."}]`, not a
    bare string, so the cache_control transform applied to the last message
    during the live loop produces a shape-stable result between live and
    replay."""
    out = blocks_to_api_messages(
        [
            {
                "role": "assistant",
                "content_blocks": [
                    _tool_calls_block(call_id="c1", result="weather: sunny"),
                    _text_block("Done."),
                ],
                "reasoning_details_per_round": [[], []],
            },
        ]
    )
    tool_msg = next(m for m in out if m["role"] == "tool")
    assert tool_msg["tool_call_id"] == "c1"
    assert tool_msg["content"] == [{"type": "text", "text": "weather: sunny"}]


# -- Non-reasoning models: dedup is a no-op -----------------------------------


def test_non_reasoning_conversation_passes_through_unchanged():
    """For non-reasoning model chats, no `reasoning_details` are ever present,
    so the dedup pass is a no-op."""
    out = blocks_to_api_messages(
        [
            {"role": "system", "content": "be helpful"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "bye"},
        ]
    )
    assert len(out) == 4
    for m in out:
        assert "reasoning_details" not in m
