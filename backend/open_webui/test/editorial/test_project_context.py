"""Testes da F3 - ficha como contexto. Sem Redis."""

import contextlib

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from open_webui.internal.db import Base
from open_webui.models import editorial as ed
from open_webui.editorial.project_context import (
    build_project_context,
    format_sheet_as_context,
)


def test_format_sheet_as_context_includes_key_fields():
    data = {
        "tone_of_voice": "sobrio e acolhedor",
        "glossary": [{"term": "ninho", "definition": "lar que serve a vida"}],
        "terminology": [{"preferred": "colaborador", "avoid": ["funcionario"]}],
        "free_notes": "evitar jargao",
    }
    ctx = format_sheet_as_context(data)
    assert "Tom de voz: sobrio e acolhedor" in ctx
    assert "ninho" in ctx and "lar que serve a vida" in ctx
    assert "usar 'colaborador'" in ctx and "evitar: funcionario" in ctx
    assert "evitar jargao" in ctx


def test_format_sheet_empty():
    assert format_sheet_as_context({}) == ""
    assert format_sheet_as_context(None) == ""


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


async def test_build_project_context_uses_current_sheet(session_factory):
    proj = await ed.Projects.create("autor-A", ed.ProjectForm(name="Obra A"))
    # sem ficha -> contexto vazio
    assert await build_project_context(proj.id) == ""

    await ed.Sheets.create_version(
        proj.id, {"tone_of_voice": "poetico"}, created_by="autor-A"
    )
    await ed.Sheets.create_version(
        proj.id, {"tone_of_voice": "tecnico e direto"}, created_by="autor-A"
    )
    ctx = await build_project_context(proj.id)
    # usa a versao ATUAL (a 2a)
    assert "tecnico e direto" in ctx
    assert "poetico" not in ctx
