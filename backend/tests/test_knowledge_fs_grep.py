import pytest
from open_webui.tools import knowledge_fs


@pytest.mark.asyncio
async def test_kb_grep_count_uses_real_newlines_for_single_file(monkeypatch):
    async def resolve_file(file_ref, user, model_knowledge):
        assert file_ref == 'sample.txt'
        return {
            'id': 'file-sample',
            'filename': 'sample.txt',
            'content': 'alpha\nbeta\ngamma',
        }

    monkeypatch.setattr(knowledge_fs, '_resolve_file', resolve_file)

    result = await knowledge_fs._kb_grep(['', 'sample.txt'], {'c'}, {}, None)

    assert result == 'file-sample  sample.txt: 3'


@pytest.mark.asyncio
async def test_kb_grep_piped_input_uses_real_newlines():
    result = await knowledge_fs._kb_grep([''], set(), {}, None, piped_input='alpha\nbeta\ngamma')

    assert result == '1: alpha\n2: beta\n3: gamma'
