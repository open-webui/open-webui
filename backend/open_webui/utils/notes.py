from open_webui.models.notes import NoteModel
from open_webui.socket.main import YDOC_MANAGER, sio


async def sync_note_update(note: NoteModel, *, clear_document: bool = False):
    if clear_document:
        await YDOC_MANAGER.clear_document(f'note:{note.id}')
    await sio.emit(
        'note-events',
        note.model_dump(),
        to=f'note:{note.id}',
    )
