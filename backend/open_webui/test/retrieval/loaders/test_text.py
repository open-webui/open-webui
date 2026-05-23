import sys
from types import SimpleNamespace

from open_webui.retrieval.loaders.text import (
    get_text_decoding_candidates,
    read_text_file,
)


def test_read_text_file_falls_back_to_gb18030(tmp_path):
    content = '# \u6807\u9898\n\n\U00020000 GB18030 only character\n'
    file_path = tmp_path / 'gb18030.md'
    file_path.write_bytes(content.encode('gb18030'))

    text, encoding = read_text_file(file_path)

    assert text == content
    assert encoding.lower() == 'gb18030'


def test_gb2312_detection_adds_gb18030_fallback(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        'chardet',
        SimpleNamespace(detect=lambda _: {'encoding': 'GB2312', 'confidence': 0.99}),
    )

    candidates = get_text_decoding_candidates(b'content')

    assert candidates.index('GB2312') < candidates.index('gb18030')
    assert 'gbk' in candidates
