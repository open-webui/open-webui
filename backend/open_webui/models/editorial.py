import logging
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, JSONField, get_async_db_context
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    select,
    text,
    update,
)

log = logging.getLogger(__name__)

####################
# Editorial DB Schema (Funcionalidade 1 + base versionada da ficha p/ F3)
####################


class EditorialProject(Base):
    __tablename__ = "editorial_project"

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False, index=True)  # autor (conta Open WebUI)

    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class EditorialProjectSheet(Base):
    """Ficha viva do projeto, VERSIONADA: cada alteracao insere uma linha nova
    (version = max+1) e marca a anterior is_current=False. Nunca apaga."""

    __tablename__ = "editorial_project_sheet"

    id = Column(Text, primary_key=True)
    project_id = Column(
        Text,
        ForeignKey("editorial_project.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, nullable=False)
    is_current = Column(Boolean, nullable=False, default=False)
    data = Column(JSONField, nullable=False)
    change_note = Column(Text, nullable=True)
    created_by = Column(Text, nullable=False)  # user_id de quem editou
    created_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_sheet_project_version"),
        # Ajuste #1: "uma so current por projeto" garantido NO BANCO via indice
        # unico PARCIAL (so vale para linhas com is_current verdadeiro).
        Index(
            "uq_sheet_one_current_per_project",
            "project_id",
            unique=True,
            sqlite_where=text("is_current = 1"),
            postgresql_where=text("is_current = true"),
        ),
    )


class EditorialDocument(Base):
    __tablename__ = "editorial_document"

    id = Column(Text, primary_key=True)
    project_id = Column(
        Text,
        ForeignKey("editorial_project.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(Text, nullable=False, index=True)

    file_id = Column(Text, nullable=True)  # arquivo do upload nativo do Open WebUI
    filename = Column(Text, nullable=True)
    format = Column(Text, nullable=True)  # docx|pdf|epub|odt
    status = Column(Text, nullable=False, default="pending")  # pending|parsing|done|error
    error = Column(Text, nullable=True)

    meta = Column(JSONField, nullable=True)  # titulo, is_scanned, needs_ocr, warnings...
    tree_ref = Column(Text, nullable=True)  # storage ref do JSON da arvore (Fatia 2/3)
    chunks_ref = Column(Text, nullable=True)  # storage ref dos chunks (Fatia 4)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


####################
# Pydantic models
####################


class EditorialProjectModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class EditorialProjectSheetModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    version: int
    is_current: bool
    data: dict
    change_note: Optional[str] = None
    created_by: str
    created_at: int


class EditorialDocumentModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    user_id: str
    file_id: Optional[str] = None
    filename: Optional[str] = None
    format: Optional[str] = None
    status: str
    error: Optional[str] = None
    meta: Optional[dict] = None
    tree_ref: Optional[str] = None
    chunks_ref: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


####################
# Forms (entrada da API)
####################


class ProjectForm(BaseModel):
    name: str
    description: Optional[str] = None


class SheetForm(BaseModel):
    data: dict
    change_note: Optional[str] = None


class DocumentIngestForm(BaseModel):
    file_id: str
    filename: Optional[str] = None
    format: Optional[str] = None


####################
# Helper classes (uma por tabela, padrao Open WebUI)
####################


class EditorialProjectsTable:
    async def create(
        self, user_id: str, form: ProjectForm
    ) -> Optional[EditorialProjectModel]:
        now = int(time.time())
        row = EditorialProject(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=form.name,
            description=form.description,
            created_at=now,
            updated_at=now,
        )
        async with get_async_db_context() as db:
            db.add(row)
            await db.commit()
            await db.refresh(row)
            return EditorialProjectModel.model_validate(row)

    async def get_by_user(self, user_id: str) -> list[EditorialProjectModel]:
        async with get_async_db_context() as db:
            res = await db.execute(
                select(EditorialProject)
                .where(EditorialProject.user_id == user_id)
                .order_by(EditorialProject.created_at.desc())
            )
            return [EditorialProjectModel.model_validate(r) for r in res.scalars().all()]

    async def get(self, project_id: str) -> Optional[EditorialProjectModel]:
        async with get_async_db_context() as db:
            res = await db.execute(
                select(EditorialProject).where(EditorialProject.id == project_id)
            )
            row = res.scalars().first()
            return EditorialProjectModel.model_validate(row) if row else None


class EditorialProjectSheetsTable:
    async def get_current(
        self, project_id: str
    ) -> Optional[EditorialProjectSheetModel]:
        async with get_async_db_context() as db:
            res = await db.execute(
                select(EditorialProjectSheet).where(
                    EditorialProjectSheet.project_id == project_id,
                    EditorialProjectSheet.is_current.is_(True),
                )
            )
            row = res.scalars().first()
            return EditorialProjectSheetModel.model_validate(row) if row else None

    async def list_versions(
        self, project_id: str
    ) -> list[EditorialProjectSheetModel]:
        async with get_async_db_context() as db:
            res = await db.execute(
                select(EditorialProjectSheet)
                .where(EditorialProjectSheet.project_id == project_id)
                .order_by(EditorialProjectSheet.version.desc())
            )
            return [
                EditorialProjectSheetModel.model_validate(r)
                for r in res.scalars().all()
            ]

    async def create_version(
        self,
        project_id: str,
        data: dict,
        created_by: str,
        change_note: Optional[str] = None,
    ) -> EditorialProjectSheetModel:
        """Cria uma nova versao da ficha de forma atomica: rebaixa a current
        anterior e insere a nova como current, na MESMA transacao. O indice
        unico parcial garante, no banco, no maximo uma current por projeto."""
        async with get_async_db_context() as db:
            res = await db.execute(
                select(func.max(EditorialProjectSheet.version)).where(
                    EditorialProjectSheet.project_id == project_id
                )
            )
            max_version = res.scalar() or 0

            # Rebaixa a current anterior ANTES de inserir a nova, para o indice
            # parcial nunca ver duas linhas current ao mesmo tempo.
            await db.execute(
                update(EditorialProjectSheet)
                .where(
                    EditorialProjectSheet.project_id == project_id,
                    EditorialProjectSheet.is_current.is_(True),
                )
                .values(is_current=False)
            )

            row = EditorialProjectSheet(
                id=str(uuid.uuid4()),
                project_id=project_id,
                version=max_version + 1,
                is_current=True,
                data=data,
                change_note=change_note,
                created_by=created_by,
                created_at=int(time.time()),
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            return EditorialProjectSheetModel.model_validate(row)


class EditorialDocumentsTable:
    async def create(
        self, user_id: str, project_id: str, form: DocumentIngestForm
    ) -> EditorialDocumentModel:
        now = int(time.time())
        row = EditorialDocument(
            id=str(uuid.uuid4()),
            project_id=project_id,
            user_id=user_id,
            file_id=form.file_id,
            filename=form.filename,
            format=form.format,
            status="pending",
            created_at=now,
            updated_at=now,
        )
        async with get_async_db_context() as db:
            db.add(row)
            await db.commit()
            await db.refresh(row)
            return EditorialDocumentModel.model_validate(row)

    async def get(self, document_id: str) -> Optional[EditorialDocumentModel]:
        async with get_async_db_context() as db:
            res = await db.execute(
                select(EditorialDocument).where(EditorialDocument.id == document_id)
            )
            row = res.scalars().first()
            return EditorialDocumentModel.model_validate(row) if row else None


Projects = EditorialProjectsTable()
Sheets = EditorialProjectSheetsTable()
Documents = EditorialDocumentsTable()
