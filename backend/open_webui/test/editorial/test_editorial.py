"""Testes da Fatia 1 do modulo editorial.

NAO dependem de Redis: usam SQLite em memoria e o modo inline da fila de jobs.
A fila/extratores externos nao sao exercitados aqui.

Cobre:
- isolamento por autor (um autor nao ve projeto de outro);
- versionamento da ficha (nova versao, current avanca, anterior preservada);
- garantia NO BANCO de "uma so current por projeto" (indice unico parcial);
- fila de jobs em modo inline (sync e async) sem Redis.
"""

import contextlib
import time
import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from open_webui.internal.db import Base
from open_webui.models import editorial as ed


@pytest.fixture
async def session_factory(monkeypatch):
    # StaticPool + única conexão => o :memory: persiste entre sessões.
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

    # Faz as helper-classes usarem ESTA sessao de teste.
    @contextlib.asynccontextmanager
    async def _fake_ctx(db=None):
        async with Session() as s:
            yield s

    monkeypatch.setattr(ed, "get_async_db_context", _fake_ctx)
    yield Session
    await engine.dispose()


async def test_project_isolation(session_factory):
    a = await ed.Projects.create("autor-A", ed.ProjectForm(name="Obra A"))
    await ed.Projects.create("autor-B", ed.ProjectForm(name="Obra B"))

    da = await ed.Projects.get_by_user("autor-A")
    db = await ed.Projects.get_by_user("autor-B")
    assert [p.name for p in da] == ["Obra A"]
    assert [p.name for p in db] == ["Obra B"]
    # autor A nao enxerga projeto de B
    assert a.id not in [p.id for p in db]


async def test_sheet_versioning_keeps_history(session_factory):
    proj = await ed.Projects.create("autor-A", ed.ProjectForm(name="Obra A"))

    v1 = await ed.Sheets.create_version(
        proj.id, {"tone_of_voice": "sobrio"}, created_by="autor-A"
    )
    v2 = await ed.Sheets.create_version(
        proj.id,
        {"tone_of_voice": "acolhedor", "glossary": [{"term": "ninho"}]},
        created_by="autor-A",
        change_note="ajuste de tom",
    )

    assert v1.version == 1
    assert v2.version == 2

    versions = await ed.Sheets.list_versions(proj.id)
    assert [v.version for v in versions] == [2, 1]  # ordem desc, anterior preservada

    current = await ed.Sheets.get_current(proj.id)
    assert current.version == 2
    assert current.data["tone_of_voice"] == "acolhedor"

    # exatamente UMA current
    assert sum(1 for v in versions if v.is_current) == 1


async def test_db_enforces_single_current(session_factory):
    """Insere duas linhas is_current=True para o MESMO projeto direto no banco
    (sem passar pela helper) -> o indice unico parcial deve rejeitar."""
    proj = await ed.Projects.create("autor-A", ed.ProjectForm(name="Obra A"))

    async with session_factory() as s:
        s.add(
            ed.EditorialProjectSheet(
                id=str(uuid.uuid4()), project_id=proj.id, version=1,
                is_current=True, data={"x": 1}, created_by="autor-A",
                created_at=int(time.time()),
            )
        )
        await s.commit()

    with pytest.raises(IntegrityError):
        async with session_factory() as s:
            s.add(
                ed.EditorialProjectSheet(
                    id=str(uuid.uuid4()), project_id=proj.id, version=2,
                    is_current=True, data={"x": 2}, created_by="autor-A",
                    created_at=int(time.time()),
                )
            )
            await s.commit()


async def test_inline_job_queue_runs_without_redis():
    from open_webui.editorial.jobs import InlineJobQueue

    q = InlineJobQueue()

    def soma(a, b):
        return a + b

    async def soma_async(a, b):
        return a + b

    assert await q.enqueue(soma, 2, 3) == 5
    assert await q.enqueue(soma_async, 4, 5) == 9
