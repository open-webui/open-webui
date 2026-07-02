import asyncio

from open_webui.tools import knowledge_fs


def test_piped_grep_c_returns_match_count():
    result = asyncio.run(knowledge_fs._kb_grep(['alpha'], {'c'}, {}, None, piped_input='alpha'))
    assert result == '1'


def test_piped_grep_c_returns_zero_when_no_match():
    result = asyncio.run(knowledge_fs._kb_grep(['zeta'], {'c'}, {}, None, piped_input='alpha'))
    assert result == '0'


def test_piped_grep_l_reports_standard_input():
    result = asyncio.run(knowledge_fs._kb_grep(['alpha'], {'l'}, {}, None, piped_input='alpha'))
    assert result == '(standard input)'


def test_piped_grep_l_no_match():
    result = asyncio.run(knowledge_fs._kb_grep(['zeta'], {'l'}, {}, None, piped_input='alpha'))
    assert result == 'No matches for "zeta"'


def test_piped_grep_default_output_unchanged():
    result = asyncio.run(knowledge_fs._kb_grep(['alpha'], set(), {}, None, piped_input='alpha'))
    assert result == '1: alpha'
