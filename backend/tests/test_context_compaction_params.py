from open_webui.utils.context_compaction import _resolve_context_compaction_model_params


def test_context_compaction_params_override_task_defaults() -> None:
    params = _resolve_context_compaction_model_params(
        {'temperature': 0.7, 'max_tokens': 2048},
        {'temperature': 0, 'custom_params': {'chat_template_kwargs': {'enable_thinking': False}}},
        {'max_tokens': 4096},
    )

    assert params == {
        'temperature': 0,
        'max_tokens': 2048,
        'custom_params': {'chat_template_kwargs': {'enable_thinking': False}},
    }


def test_context_compaction_params_ignore_empty_values() -> None:
    params = _resolve_context_compaction_model_params(
        {'temperature': 0.4, 'stop': ''},
        {'temperature': None, 'top_p': 0.8},
        {'max_tokens': 4096},
    )

    assert params == {'temperature': 0.4, 'top_p': 0.8}


def test_context_compaction_params_keep_model_max_tokens_fallback() -> None:
    assert _resolve_context_compaction_model_params({}, {}, {'max_tokens': 3072}) == {'max_tokens': 3072}


def test_context_compaction_params_ignore_non_mapping_values() -> None:
    assert _resolve_context_compaction_model_params(None, ['invalid'], None) == {'max_tokens': 1000}
