from types import SimpleNamespace

import pytest
from open_webui.tools.builtin import sync_note_document_after_external_update


class FakeYdocManager:
    def __init__(self):
        self.cleared = []

    async def clear_document(self, document_id):
        self.cleared.append(document_id)


class FakeSocket:
    def __init__(self):
        self.emitted = []

    async def emit(self, event, data, to=None):
        self.emitted.append((event, data, to))


@pytest.mark.asyncio
async def test_sync_note_document_after_external_update_clears_ydoc_and_emits_note():
    ydoc_manager = FakeYdocManager()
    socket = FakeSocket()
    note = SimpleNamespace(
        id='note-id',
        model_dump=lambda: {'id': 'note-id', 'data': {'content': {'md': '# Updated'}}},
    )

    await sync_note_document_after_external_update(
        note,
        ydoc_manager=ydoc_manager,
        socket=socket,
    )

    assert ydoc_manager.cleared == ['note:note-id']
    assert socket.emitted == [
        (
            'note-events',
            {'id': 'note-id', 'data': {'content': {'md': '# Updated'}}},
            'note:note-id',
        )
    ]
