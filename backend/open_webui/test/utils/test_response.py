from open_webui.utils.response import normalize_metadata_usage


def test_normalize_metadata_usage_returns_persistable_responses_usage():
    metadata = {
        'usage': {
            'input_tokens': 12,
            'output_tokens': 5,
            'total_tokens': 17,
            'input_tokens_details': {'cached_tokens': 3},
        },
        'done': True,
    }

    normalized_metadata, usage = normalize_metadata_usage(metadata)

    assert usage == {
        'input_tokens': 12,
        'output_tokens': 5,
        'total_tokens': 17,
        'input_tokens_details': {'cached_tokens': 3},
    }
    assert normalized_metadata == {
        'usage': usage,
        'done': True,
    }
    assert metadata['usage'] is not usage


def test_normalize_metadata_usage_preserves_current_usage_without_new_usage():
    current_usage = {'input_tokens': 1, 'output_tokens': 2, 'total_tokens': 3}
    metadata = {'done': True}

    normalized_metadata, usage = normalize_metadata_usage(metadata, current_usage)

    assert normalized_metadata == {'done': True}
    assert usage is current_usage
