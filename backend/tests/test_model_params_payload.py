from types import SimpleNamespace

from open_webui.utils.model_params import pop_model_params_from_payload


class Params:
    def __init__(self, data):
        self.data = data

    def model_dump(self):
        return dict(self.data)


def test_pop_model_params_from_payload_prefers_payload_params():
    payload = {'model': 'test-model', 'params': {'max_tokens': 99999, 'temperature': 0.2}}
    model_info = SimpleNamespace(params=Params({'max_tokens': 2048, 'top_p': 0.9, 'system': 'model system'}))

    params = pop_model_params_from_payload(payload, model_info)

    assert params == {
        'max_tokens': 99999,
        'temperature': 0.2,
        'top_p': 0.9,
        'system': 'model system',
    }
    assert 'params' not in payload


def test_pop_model_params_from_payload_supports_payload_without_model_info():
    payload = {'model': 'external-model', 'params': {'seed': 42}}

    assert pop_model_params_from_payload(payload, None) == {'seed': 42}
    assert 'params' not in payload
