"""Offline checks for native PDF file-input helpers (no full app boot)."""

import asyncio
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

ROOT = Path(__file__).resolve().parents[1] / 'backend'
sys.path.insert(0, str(ROOT))

for k in list(sys.modules):
    if k == 'open_webui' or k.startswith('open_webui.'):
        del sys.modules[k]


def pkg(name, path=None):
    mod = types.ModuleType(name)
    mod.__path__ = [str(path)] if path else []
    sys.modules[name] = mod
    return mod


def stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


pkg('open_webui', ROOT / 'open_webui')
pkg('open_webui.utils', ROOT / 'open_webui' / 'utils')
pkg('open_webui.models', ROOT / 'open_webui' / 'models')
pkg('open_webui.routers', ROOT / 'open_webui' / 'routers')
pkg('open_webui.storage', ROOT / 'open_webui' / 'storage')
pkg('open_webui.retrieval', ROOT / 'open_webui' / 'retrieval')
pkg('open_webui.retrieval.web', ROOT / 'open_webui' / 'retrieval' / 'web')
pkg('open_webui.utils.access_control', ROOT / 'open_webui' / 'utils' / 'access_control')

stub(
    'open_webui.env',
    AIOHTTP_CLIENT_ALLOW_REDIRECTS=False,
    AIOHTTP_CLIENT_SESSION_SSL=False,
    ENABLE_IMAGE_CONTENT_TYPE_EXTENSION_FALLBACK=False,
)
Files = MagicMock()
stub('open_webui.models.files', Files=Files)
stub('open_webui.models.chats', Chats=object)
stub('open_webui.retrieval.web.utils', get_ssrf_safe_session=None, validate_url=None)
stub('open_webui.routers.files', upload_file_handler=None)
stub('open_webui.routers.images', get_image_data=None, upload_image=None)
stub('open_webui.storage.provider', Storage=MagicMock())
stub('open_webui.utils.access_control.files', has_access_to_file=AsyncMock(return_value=False))

from fastapi import HTTPException  # noqa: E402

from open_webui.utils.files import (  # noqa: E402
    NATIVE_FILE_PART_MARKER,
    append_native_file_inputs_to_messages,
    get_native_file_input_enabled,
    get_pdf_file_data_uri_from_file_id,
    strip_untrusted_file_content_parts,
)


def _user(uid='u1', role='user'):
    return MagicMock(id=uid, role=role)


def test_capability_server_only():
    assert get_native_file_input_enabled(server_model=None, model_info=None) is False

    server_on = {'info': {'meta': {'capabilities': {'native_file_input': True}}}}
    assert get_native_file_input_enabled(server_model=server_on) is True

    server_off = {'info': {'meta': {'capabilities': {'native_file_input': False}}}}
    assert get_native_file_input_enabled(server_model=server_off) is False

    # Missing key on capabilities object => False (no silent True).
    server_missing = {'info': {'meta': {'capabilities': {'vision': True}}}}
    assert get_native_file_input_enabled(server_model=server_missing) is False

    info = MagicMock()
    info.meta = MagicMock()
    info.meta.capabilities = {'native_file_input': True}
    assert get_native_file_input_enabled(server_model={}, model_info=info) is True


def test_strip_untrusted_file_parts():
    payload = {
        'messages': [
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': 'hi'},
                    {
                        'type': 'file',
                        'file': {'filename': 'evil.pdf', 'file_data': 'data:application/pdf;base64,QQ=='},
                    },
                    {'type': 'input_file', 'filename': 'x.pdf', 'file_data': 'data:...'},
                    {'type': 'native_file', 'file': {}},
                ],
            }
        ]
    }
    out = strip_untrusted_file_content_parts(payload)
    parts = out['messages'][0]['content']
    assert parts == [{'type': 'text', 'text': 'hi'}]


async def test_fail_closed_when_raw_without_native():
    payload = {'messages': [{'role': 'user', 'content': 'read this'}]}
    metadata = {
        'user_message': {
            'files': [{'type': 'file', 'id': 'f1', 'processed': False, 'name': 'a.pdf'}],
        }
    }
    try:
        await append_native_file_inputs_to_messages(
            payload,
            metadata,
            native_file_input_enabled=False,
            is_responses=True,
            user=_user(),
        )
        raise AssertionError('expected HTTPException')
    except HTTPException as e:
        assert e.status_code == 400
        assert 'Native File Input' in e.detail


async def test_current_turn_scoping_ignores_history_only_files():
    payload = {'messages': [{'role': 'user', 'content': 'follow-up'}]}
    metadata = {
        'files': [{'type': 'file', 'id': 'old', 'processed': False, 'name': 'old.pdf'}],
        'user_message': {'files': []},
    }
    out = await append_native_file_inputs_to_messages(
        payload,
        metadata,
        native_file_input_enabled=True,
        is_responses=True,
        user=_user(),
    )
    assert out['messages'][0]['content'] == 'follow-up'


async def test_append_marks_server_parts_and_strips_client():
    pdf_bytes = b'%PDF-1.4\ntrailer\n%%EOF\n'
    tmp = Path(__file__).resolve().parent / '_tmp_native_test.pdf'
    tmp.write_bytes(pdf_bytes)

    file_row = MagicMock()
    file_row.id = 'fid'
    file_row.path = str(tmp)
    file_row.user_id = 'u1'
    file_row.filename = 'doc.pdf'
    file_row.meta = {'name': 'doc.pdf', 'content_type': 'application/pdf'}
    Files.get_file_by_id = AsyncMock(return_value=file_row)

    from open_webui.storage.provider import Storage

    Storage.get_file = MagicMock(return_value=str(tmp))

    payload = {
        'messages': [
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': 'summarize'},
                    {
                        'type': 'file',
                        'file': {'filename': 'client.pdf', 'file_data': 'data:application/pdf;base64,QQ=='},
                    },
                ],
            }
        ]
    }
    metadata = {
        'user_message': {
            'files': [{'type': 'file', 'id': 'fid', 'processed': False, 'name': 'doc.pdf'}],
        }
    }

    try:
        out = await append_native_file_inputs_to_messages(
            payload,
            metadata,
            native_file_input_enabled=True,
            is_responses=True,
            user=_user(),
        )
    finally:
        tmp.unlink(missing_ok=True)

    parts = out['messages'][0]['content']
    assert any(p.get('type') == 'text' and p.get('text') == 'summarize' for p in parts)
    file_parts = [p for p in parts if p.get('type') == 'file']
    assert len(file_parts) == 1
    assert file_parts[0].get(NATIVE_FILE_PART_MARKER) is True
    assert file_parts[0]['file']['filename'] == 'doc.pdf'
    assert file_parts[0]['file']['file_data'].startswith('data:application/pdf;base64,')
    # Client-forged part must not survive.
    assert all(p.get('file', {}).get('filename') != 'client.pdf' for p in file_parts)


async def test_rejects_non_pdf_magic():
    tmp = Path(__file__).resolve().parent / '_tmp_native_fake.pdf'
    tmp.write_bytes(b'not a pdf')

    file_row = MagicMock()
    file_row.id = 'fid2'
    file_row.path = str(tmp)
    file_row.user_id = 'u1'
    file_row.filename = 'fake.pdf'
    file_row.meta = {'name': 'fake.pdf', 'content_type': 'application/pdf'}
    Files.get_file_by_id = AsyncMock(return_value=file_row)

    from open_webui.storage.provider import Storage

    Storage.get_file = MagicMock(return_value=str(tmp))

    try:
        await get_pdf_file_data_uri_from_file_id('fid2', user=_user())
        raise AssertionError('expected HTTPException')
    except HTTPException as e:
        assert e.status_code == 400
        assert 'not a valid PDF' in e.detail
    finally:
        tmp.unlink(missing_ok=True)


async def test_total_budget_uses_bytes_not_client_size():
    pdf_bytes = b'%PDF-1.4\n' + (b'x' * 1024) + b'\n%%EOF\n'
    tmp = Path(__file__).resolve().parent / '_tmp_native_budget.pdf'
    tmp.write_bytes(pdf_bytes)

    file_row = MagicMock()
    file_row.id = 'fid3'
    file_row.path = str(tmp)
    file_row.user_id = 'u1'
    file_row.filename = 'big.pdf'
    file_row.meta = {'name': 'big.pdf', 'content_type': 'application/pdf'}
    Files.get_file_by_id = AsyncMock(return_value=file_row)

    from open_webui.storage.provider import Storage

    Storage.get_file = MagicMock(return_value=str(tmp))

    try:
        await get_pdf_file_data_uri_from_file_id('fid3', user=_user(), remaining_total_budget=10)
        raise AssertionError('expected HTTPException')
    except HTTPException as e:
        assert e.status_code == 400
        assert 'total attachment budget' in e.detail
    finally:
        tmp.unlink(missing_ok=True)


def main():
    test_capability_server_only()
    test_strip_untrusted_file_parts()
    asyncio.run(test_fail_closed_when_raw_without_native())
    asyncio.run(test_current_turn_scoping_ignores_history_only_files())
    asyncio.run(test_append_marks_server_parts_and_strips_client())
    asyncio.run(test_rejects_non_pdf_magic())
    asyncio.run(test_total_budget_uses_bytes_not_client_size())
    print('OK: native_file_input offline checks passed')


if __name__ == '__main__':
    main()
