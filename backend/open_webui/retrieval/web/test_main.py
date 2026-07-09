from open_webui.retrieval.web import main


def test_get_filtered_results_does_not_resolve_domain_only_filters(monkeypatch):
    def fail_resolve(hostname):
        raise AssertionError(f'unexpected DNS lookup for {hostname}')

    monkeypatch.setattr(main, 'resolve_hostname', fail_resolve)

    results = [
        {'url': 'https://docs.openwebui.com/features'},
        {'url': 'https://blocked.example/page'},
    ]

    assert main.get_filtered_results(results, ['!blocked.example']) == [results[0]]


def test_get_filtered_results_resolves_when_filter_contains_ip(monkeypatch):
    calls = []

    def fake_resolve(hostname):
        calls.append(hostname)
        return ['203.0.113.10'], []

    monkeypatch.setattr(main, 'resolve_hostname', fake_resolve)

    results = [{'url': 'https://openwebui.example/page'}]

    assert main.get_filtered_results(results, ['!203.0.113.10']) == []
    assert calls == ['openwebui.example']
