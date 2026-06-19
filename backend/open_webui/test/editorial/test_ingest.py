"""Teste de integracao da ingestao (Fatia 2), sem Redis.

Mocka Files/Storage e usa SQLite em memoria. Exercita o caminho completo:
file_id -> le bytes -> extrai .docx -> guarda arvore -> status=done; e o
caminho de erro (formato nao suportado -> status=error com mensagem clara).
"""

import contextlib
import os
import tempfile
import types

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from open_webui.internal.db import Base
from open_webui.models import editorial as ed
from open_webui.editorial import ingest as ingest_mod
from open_webui.test.editorial.test_docx_extractor import build_docx_with_footnote


@pytest.fixture
async def session_factory(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda c: Base.metadata.create_all(
                c,
                tables=[
                    ed.EditorialProject.__table__,
                    ed.EditorialProjectSheet.__table__,
                    ed.EditorialDocument.__table__,
                ],
            )
        )
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @contextlib.asynccontextmanager
    async def _fake_ctx(db=None):
        async with Session() as s:
            yield s

    monkeypatch.setattr(ed, "get_async_db_context", _fake_ctx)
    yield Session
    await engine.dispose()


class _FakeFiles:
    def __init__(self, path, filename):
        self._path = path
        self._filename = filename

    async def get_file_by_id(self, file_id):
        return types.SimpleNamespace(path=self._path, filename=self._filename)


class _FakeStorage:
    def __init__(self, local_path):
        self._local_path = local_path
        self.uploaded = {}

    def get_file(self, file_path):
        return self._local_path

    def upload_file(self, fileobj, filename, tags):
        data = fileobj.read()
        self.uploaded[filename] = data
        return (data, "stored/" + filename)


async def test_ingestion_docx_happy_path(session_factory, monkeypatch, tmp_path):
    # grava o fixture .docx num arquivo que o "Storage" devolve
    docx_path = tmp_path / "obra.docx"
    docx_path.write_bytes(build_docx_with_footnote())

    monkeypatch.setattr(ingest_mod, "Files", _FakeFiles(str(docx_path), "obra.docx"))
    fake_storage = _FakeStorage(str(docx_path))
    monkeypatch.setattr(ingest_mod, "Storage", fake_storage)

    proj = await ed.Projects.create("autor-A", ed.ProjectForm(name="Obra A"))
    doc = await ed.Documents.create(
        "autor-A", proj.id, ed.DocumentIngestForm(file_id="f1", filename="obra.docx")
    )

    result = await ingest_mod.run_ingestion(doc.id)
    assert result["status"] == "done", result

    saved = await ed.Documents.get(doc.id)
    assert saved.status == "done"
    assert saved.tree_ref and saved.tree_ref.startswith("stored/")
    assert saved.meta["footnotes"] == 1
    assert saved.meta["headings"] == 1
    # a arvore guardada contem a ligacao ancora<->nota
    import json

    tree = json.loads(list(fake_storage.uploaded.values())[0].decode("utf-8"))
    notes = {b["id"] for b in tree["blocks"] if b["type"] == "footnote"}
    refs = {
        i["id"]
        for b in tree["blocks"]
        for i in b.get("inlines", [])
        if i.get("t") == "footnote_ref"
    }
    assert refs == {"fn-2"} and "fn-2" in notes


async def test_ingestion_unsupported_format_sets_clear_error(
    session_factory, monkeypatch, tmp_path
):
    f = tmp_path / "planilha.xyz"
    f.write_bytes(b"conteudo qualquer")
    monkeypatch.setattr(ingest_mod, "Files", _FakeFiles(str(f), "planilha.xyz"))
    monkeypatch.setattr(ingest_mod, "Storage", _FakeStorage(str(f)))

    proj = await ed.Projects.create("autor-A", ed.ProjectForm(name="Obra A"))
    doc = await ed.Documents.create(
        "autor-A", proj.id, ed.DocumentIngestForm(file_id="f1", filename="planilha.xyz")
    )

    result = await ingest_mod.run_ingestion(doc.id)
    assert result["status"] == "error"

    saved = await ed.Documents.get(doc.id)
    assert saved.status == "error"
    assert "nao suportado" in (saved.error or "")
