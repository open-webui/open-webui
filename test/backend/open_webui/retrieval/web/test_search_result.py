from open_webui.retrieval.web.search_result import is_valid_search_result_url


def test_accepts_http_and_https_search_result_urls():
    assert is_valid_search_result_url('https://example.com/result?q=open-webui')
    assert is_valid_search_result_url('http://example.com/result')


def test_rejects_missing_relative_and_non_http_search_result_urls():
    assert not is_valid_search_result_url('')
    assert not is_valid_search_result_url(None)
    assert not is_valid_search_result_url('/relative/result')
    assert not is_valid_search_result_url('ftp://example.com/result')


def test_rejects_parser_confusing_search_result_urls():
    assert not is_valid_search_result_url('https://example.com\\@127.0.0.1/')
    assert not is_valid_search_result_url('https://example.com/\nnext')
