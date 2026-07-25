"""Unit tests for the folder-preservation primitives.

  * ``sanitize_relative_path`` — the pure path normalizer/guard.
  * ``Knowledges.ensure_directory_path`` — idempotent directory-tree creation.
"""

import pytest

from open_webui.models.knowledge import Knowledges
from open_webui.utils.misc import sanitize_relative_path


@pytest.mark.parametrize(
    'raw, expected',
    [
        (None, None),
        ('', None),
        ('report.pdf', 'report.pdf'),
        ('Q3/finance/report.pdf', 'Q3/finance/report.pdf'),
        # Backslashes normalized to POSIX separators.
        ('Q3\\finance\\report.pdf', 'Q3/finance/report.pdf'),
        # Leading slashes and '.' segments dropped.
        ('/Q3//finance/./report.pdf', 'Q3/finance/report.pdf'),
        # Windows drive prefix stripped.
        ('C:\\Users\\x\\a.txt', 'Users/x/a.txt'),
        # Traversal collapses to a safe basename — never escapes the root.
        ('../../etc/passwd', 'passwd'),
        ('a/../../b/c.txt', 'c.txt'),
        ('..', None),
    ],
)
def test_sanitize_relative_path(raw, expected):
    assert sanitize_relative_path(raw) == expected


async def _new_kb(user_id):
    from open_webui.models.knowledge import KnowledgeForm

    return await Knowledges.insert_new_knowledge(user_id, KnowledgeForm(name='KB', description=''))


@pytest.fixture
async def _user():
    from open_webui.models.users import Users

    existing = await Users.get_user_by_id('test-user-id')
    if existing:
        return existing
    return await Users.insert_new_user(id='test-user-id', name='Test User', email='test@example.com', role='user')


async def test_ensure_directory_path_empty_is_root(_user):
    kb = await _new_kb(_user.id)
    assert await Knowledges.ensure_directory_path(kb.id, None, _user.id) is None
    assert await Knowledges.ensure_directory_path(kb.id, '', _user.id) is None
    assert await Knowledges.get_all_directories(kb.id) == []


async def test_ensure_directory_path_creates_nested_chain(_user):
    kb = await _new_kb(_user.id)

    leaf_id = await Knowledges.ensure_directory_path(kb.id, 'a/b/c', _user.id)

    dirs = {d.name: d for d in await Knowledges.get_all_directories(kb.id)}
    assert set(dirs) == {'a', 'b', 'c'}
    assert dirs['a'].parent_id is None
    assert dirs['b'].parent_id == dirs['a'].id
    assert dirs['c'].parent_id == dirs['b'].id
    assert leaf_id == dirs['c'].id


async def test_ensure_directory_path_is_idempotent(_user):
    kb = await _new_kb(_user.id)

    first = await Knowledges.ensure_directory_path(kb.id, 'a/b/c', _user.id)
    second = await Knowledges.ensure_directory_path(kb.id, 'a/b/c', _user.id)

    assert first == second
    # No duplicate levels created on the second call.
    assert len(await Knowledges.get_all_directories(kb.id)) == 3

    # A sibling reuses the shared prefix rather than recreating it.
    await Knowledges.ensure_directory_path(kb.id, 'a/b/d', _user.id)
    dirs = await Knowledges.get_all_directories(kb.id)
    assert sorted(d.name for d in dirs) == ['a', 'b', 'c', 'd']


# ── Cached immediate-children counts (knowledge_directory.meta) ──


def _counts(directory):
    return (directory.meta or {}).get('file_count'), (directory.meta or {}).get('directory_count')


async def _dir_by_name(kb_id, name):
    return next(d for d in await Knowledges.get_all_directories(kb_id) if d.name == name)


async def test_directory_counts_track_subfolders(_user):
    kb = await _new_kb(_user.id)

    # a/b/c → 'a' has one immediate subfolder ('b'); 'c' has none.
    await Knowledges.ensure_directory_path(kb.id, 'a/b/c', _user.id)

    a = await _dir_by_name(kb.id, 'a')
    b = await _dir_by_name(kb.id, 'b')
    c = await _dir_by_name(kb.id, 'c')
    assert _counts(a) == (0, 1)
    assert _counts(b) == (0, 1)
    assert _counts(c) == (0, 0)

    # A second subfolder under 'a' bumps only 'a'.
    await Knowledges.ensure_directory_path(kb.id, 'a/x', _user.id)
    a = await _dir_by_name(kb.id, 'a')
    assert _counts(a) == (0, 2)


async def test_directory_counts_track_files(_user):
    from open_webui.models.files import FileForm, Files

    kb = await _new_kb(_user.id)
    leaf = await Knowledges.ensure_directory_path(kb.id, 'docs', _user.id)

    async def _mk_file(name):
        f = await Files.insert_new_file(
            _user.id, FileForm(id=f'{name}-id', filename=name, path=f'/tmp/{name}')
        )
        return f.id

    f1 = await _mk_file('one.txt')
    f2 = await _mk_file('two.txt')

    await Knowledges.add_file_to_knowledge_by_id(kb.id, f1, _user.id, directory_id=leaf)
    await Knowledges.add_file_to_knowledge_by_id(kb.id, f2, _user.id, directory_id=leaf)
    assert _counts(await _dir_by_name(kb.id, 'docs')) == (2, 0)

    # Remove one → count drops.
    await Knowledges.remove_file_from_knowledge_by_id(kb.id, f1)
    assert _counts(await _dir_by_name(kb.id, 'docs')) == (1, 0)

    # Move the remaining file to a sibling → both ends update.
    other = await Knowledges.ensure_directory_path(kb.id, 'other', _user.id)
    await Knowledges.move_file_to_directory(kb.id, f2, directory_id=other)
    assert _counts(await _dir_by_name(kb.id, 'docs')) == (0, 0)
    assert _counts(await _dir_by_name(kb.id, 'other')) == (1, 0)


async def test_directory_counts_after_delete(_user):
    kb = await _new_kb(_user.id)
    await Knowledges.ensure_directory_path(kb.id, 'parent/child', _user.id)
    parent = await _dir_by_name(kb.id, 'parent')
    child = await _dir_by_name(kb.id, 'child')
    assert _counts(parent) == (0, 1)

    await Knowledges.delete_directory(child.id, move_files_to_parent=True)
    assert _counts(await _dir_by_name(kb.id, 'parent')) == (0, 0)


async def test_directory_counts_after_delete_without_moving_files(_user):
    from open_webui.models.files import FileForm, Files

    kb = await _new_kb(_user.id)
    child = await Knowledges.ensure_directory_path(kb.id, 'parent/child', _user.id)
    f = await Files.insert_new_file(_user.id, FileForm(id='drop-id', filename='drop.txt', path='/tmp/drop.txt'))
    await Knowledges.add_file_to_knowledge_by_id(kb.id, f.id, _user.id, directory_id=child)

    parent = await _dir_by_name(kb.id, 'parent')
    assert _counts(parent) == (0, 1)

    # Delete the child and its files (no move-up): parent loses the subfolder,
    # and gains no files.
    await Knowledges.delete_directory(child, move_files_to_parent=False)
    assert _counts(await _dir_by_name(kb.id, 'parent')) == (0, 0)


async def test_ensure_directories_endpoint_creates_tree_root_first(async_client, test_user):
    kb = await _new_kb(test_user.id)

    resp = await async_client.post(
        f'/api/v1/knowledge/{kb.id}/dirs/ensure',
        json={'paths': ['MyFolder/sub', 'MyFolder']},
    )
    assert resp.status_code == 200
    mapping = resp.json()

    dirs = {d.name: d for d in await Knowledges.get_all_directories(kb.id)}
    assert set(dirs) == {'MyFolder', 'sub'}
    assert dirs['MyFolder'].parent_id is None
    assert dirs['sub'].parent_id == dirs['MyFolder'].id
    assert mapping['MyFolder'] == dirs['MyFolder'].id
    assert mapping['MyFolder/sub'] == dirs['sub'].id

    # Idempotent: a second call creates nothing new and returns the same ids.
    resp2 = await async_client.post(
        f'/api/v1/knowledge/{kb.id}/dirs/ensure',
        json={'paths': ['MyFolder', 'MyFolder/sub']},
    )
    assert resp2.json() == mapping
    assert len(await Knowledges.get_all_directories(kb.id)) == 2


async def test_directory_counts_after_move_directory(_user):
    kb = await _new_kb(_user.id)
    # src/leaf  and a separate dst
    await Knowledges.ensure_directory_path(kb.id, 'src/leaf', _user.id)
    dst = await Knowledges.ensure_directory_path(kb.id, 'dst', _user.id)
    src = await _dir_by_name(kb.id, 'src')
    leaf = await _dir_by_name(kb.id, 'leaf')

    assert _counts(src) == (0, 1)
    assert _counts(await _dir_by_name(kb.id, 'dst')) == (0, 0)

    # Move 'leaf' from 'src' into 'dst': both parents update.
    await Knowledges.move_directory(leaf.id, dst)
    assert _counts(await _dir_by_name(kb.id, 'src')) == (0, 0)
    assert _counts(await _dir_by_name(kb.id, 'dst')) == (0, 1)


# ── Knowledge-base AI overview (ai_overwiew) ──


async def test_set_and_read_ai_overview(_user):
    kb = await _new_kb(_user.id)
    updated = await Knowledges.set_ai_overview(kb.id, 'Огляд бази знань', db=None)
    assert updated is not None and updated.ai_overwiew == 'Огляд бази знань'
    # Round-trips through the model/response.
    fetched = await Knowledges.get_knowledge_by_id(id=kb.id)
    assert fetched.ai_overwiew == 'Огляд бази знань'


async def test_describe_knowledge_empty_returns_blank(_user):
    """With nothing to summarize, describe_knowledge short-circuits to '' without
    needing a model (request unused on the empty path)."""
    from open_webui.services.file_analysis import describe_knowledge

    kb = await _new_kb(_user.id)
    assert await describe_knowledge(None, kb.id, _user, db=None) == ''


# ── AI summary generation (LLM mocked) ──


def _mock_llm(monkeypatch, reply, capture=None):
    """Force a usable task model and stub the chat completion with `reply`."""
    from open_webui.services import file_analysis

    monkeypatch.setattr(file_analysis, '_resolve_task_model_id', lambda request: 'test-model')

    async def fake_gcc(request, form_data=None, user=None):
        if capture is not None:
            capture['content'] = form_data['messages'][0]['content']
        return {'choices': [{'message': {'content': reply}}]}

    monkeypatch.setattr(file_analysis, 'generate_chat_completion', fake_gcc)


async def test_analyze_file_parses_and_persists_description(_user, monkeypatch):
    from open_webui.models.files import FileForm, Files
    from open_webui.services.file_analysis import analyze_file

    await Files.insert_new_file(
        _user.id, FileForm(id='an1', filename='c.txt', path='/tmp/c', data={'content': 'hello content'})
    )
    _mock_llm(monkeypatch, '{"eligible": true, "description": "Короткий опис"}')

    eligible, desc = await analyze_file(None, 'an1', _user, content='hello content', db=None)
    assert eligible is True
    assert desc == 'Короткий опис'
    # Persisted to file.data for later folder/KB rollups.
    assert (await Files.get_file_by_id('an1')).data['description'] == 'Короткий опис'


async def test_describe_folder_folds_file_descriptions(_user, monkeypatch):
    from open_webui.models.files import FileForm, Files
    from open_webui.services.file_analysis import describe_folder

    await Files.insert_new_file(_user.id, FileForm(id='fd1', filename='a.txt', path='/tmp/a'))
    await Files.update_file_data_by_id('fd1', {'description': 'опис A'})
    await Files.insert_new_file(_user.id, FileForm(id='fd2', filename='b.txt', path='/tmp/b'))
    await Files.update_file_data_by_id('fd2', {'description': 'опис B'})

    cap = {}
    _mock_llm(monkeypatch, 'Підсумок папки', capture=cap)

    result = await describe_folder(None, ['fd1', 'fd2'], _user, db=None)
    assert result == 'Підсумок папки'
    assert 'опис A' in cap['content'] and 'опис B' in cap['content']


async def test_describe_knowledge_folds_folder_and_root_summaries(_user, monkeypatch):
    from open_webui.models.files import FileForm, Files
    from open_webui.services.file_analysis import describe_knowledge

    kb = await _new_kb(_user.id)
    docs = await Knowledges.ensure_directory_path(kb.id, 'docs', _user.id)
    await Knowledges.set_directory_description(docs, 'Підсумок docs')
    await Files.insert_new_file(
        _user.id, FileForm(id='rk1', filename='r.txt', path='/tmp/r', data={'description': 'опис кореневого файлу'})
    )
    await Knowledges.add_file_to_knowledge_by_id(kb.id, 'rk1', _user.id, directory_id=None)

    cap = {}
    _mock_llm(monkeypatch, 'Огляд бази', capture=cap)

    result = await describe_knowledge(None, kb.id, _user, db=None)
    assert result == 'Огляд бази'
    # Rollup included the folder summary and the root file description.
    assert 'docs' in cap['content'] and 'опис кореневого файлу' in cap['content']


async def test_get_knowledge_stats(_user):
    from open_webui.models.files import FileForm, Files

    kb = await _new_kb(_user.id)
    docs = await Knowledges.ensure_directory_path(kb.id, 'a/b', _user.id)  # 2 folders

    async def _mk(fid, size):
        f = await Files.insert_new_file(
            _user.id, FileForm(id=fid, filename=f'{fid}.txt', path=f'/tmp/{fid}', meta={'size': size})
        )
        return f.id

    await Knowledges.add_file_to_knowledge_by_id(kb.id, await _mk('s1', 100), _user.id, directory_id=None)
    await Knowledges.add_file_to_knowledge_by_id(kb.id, await _mk('s2', 250), _user.id, directory_id=docs)

    stats = await Knowledges.get_knowledge_stats(kb.id)
    assert stats == {'file_count': 2, 'directory_count': 2, 'total_size': 350}

    updated = await Knowledges.set_knowledge_stats(kb.id, stats)
    assert updated.meta.get('stats') == stats
