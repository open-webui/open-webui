from open_webui.utils.misc import get_content_from_completion_event


def test_legacy_top_level_content():
    data = {'content': 'hello world', 'done': False}
    assert get_content_from_completion_event(data, '') == 'hello world'


def test_streaming_delta_accumulates():
    data = {'choices': [{'delta': {'content': ' world'}}]}
    assert get_content_from_completion_event(data, 'hello') == 'hello world'


def test_full_choice_message_replaces():
    data = {'choices': [{'message': {'content': 'full reply'}}]}
    assert get_content_from_completion_event(data, 'partial') == 'full reply'


def test_done_event_output_is_authoritative():
    data = {
        'done': True,
        'output': [
            {
                'type': 'message',
                'status': 'completed',
                'role': 'assistant',
                'content': [{'type': 'output_text', 'text': 'final text'}],
            }
        ],
        'title': 'A chat',
    }
    assert get_content_from_completion_event(data, 'partial strea') == 'final text'


def test_done_event_without_content_keeps_accumulated():
    data = {'done': True}
    assert get_content_from_completion_event(data, 'accumulated') == 'accumulated'


def test_empty_event_returns_current():
    assert get_content_from_completion_event({}, '') == ''
