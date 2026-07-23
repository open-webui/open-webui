import asyncio

from open_webui.tools import knowledge_fs


def test_kb_grep_counts_real_newlines_in_single_file(monkeypatch):
    async def fake_resolve_file(file_ref, user, model_knowledge):
        return {
            'id': 'file-sample',
            'filename': file_ref,
            'content': 'alpha\nbeta\ngamma',
        }

    monkeypatch.setattr(knowledge_fs, '_resolve_file', fake_resolve_file)

    result = asyncio.run(
        knowledge_fs._kb_grep(
            ['.*', 'sample.txt'],
            {'E', 'c'},
            user={},
            model_knowledge=[],
        )
    )

    assert result == 'file-sample  sample.txt: 3'


def test_kb_grep_preserves_real_newlines_in_piped_output():
    result = asyncio.run(
        knowledge_fs._kb_grep(
            ['.*'],
            {'E'},
            user={},
            model_knowledge=[],
            piped_input='alpha\nbeta\ngamma',
        )
    )

    assert result == '1: alpha\n2: beta\n3: gamma'
