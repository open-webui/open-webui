from open_webui.utils.reasoning import extract_reasoning_content


def test_extract_reasoning_content_from_field():
    assert extract_reasoning_content({"reasoning_content": "abc"}) == "abc"
    assert extract_reasoning_content({"reasoning": "abc"}) == "abc"
    assert extract_reasoning_content({"thinking": "abc"}) == "abc"


def test_extract_reasoning_content_from_details():
    delta = {}
    reasoning_details = [
        {"type": "reasoning.text", "text": "hello"},
        {"type": "reasoning.text", "text": " world"},
    ]
    assert extract_reasoning_content(delta, reasoning_details) == "hello world"


def test_extract_reasoning_content_prefers_details_over_field_to_avoid_duplication():
    delta = {"reasoning_content": "hello"}
    reasoning_details = [{"type": "reasoning.text", "text": "hello"}]

    # Previously these two sources were concatenated, producing "hellohello".
    assert extract_reasoning_content(delta, reasoning_details) == "hello"


def test_extract_reasoning_content_ignores_non_text_details():
    delta = {"reasoning_content": "hello"}
    reasoning_details = [{"type": "reasoning.encrypted", "data": "sig"}]
    assert extract_reasoning_content(delta, reasoning_details) == "hello"


def test_extract_reasoning_content_returns_none_when_missing():
    assert extract_reasoning_content({}) is None

