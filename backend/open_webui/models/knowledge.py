import logging
import time
import uuid

from open_webui.internal.db import Base, get_async_db_context
from open_webui.models.access_grants import AccessGrantModel, AccessGrants
from open_webui.models.files import (
    File,
    FileMetadataResponse,
    FileModel,
    FileModelResponse,
)
from open_webui.models.groups import Groups
from open_webui.models.users import User, UserModel, UserResponse, Users
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    ForeignKey,
    Text,
    UniqueConstraint,
    cast,
    delete,
    func,
    or_,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

####################
# Knowledge DB Schema
# Let what was gathered here outlast the one who gathered it,
# and still teach when the builder is gone.
####################


class Knowledge(Base):
    __tablename__ = "knowledge"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)

    name = Column(Text)
    description = Column(Text)

    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class KnowledgeModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    name: str
    description: str

    meta: dict | None = None

    access_grants: list[AccessGrantModel] = Field(default_factory=list)

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


class KnowledgeFile(Base):
    __tablename__ = "knowledge_file"

    id = Column(Text, unique=True, primary_key=True)

    knowledge_id = Column(
        Text, ForeignKey("knowledge.id", ondelete="CASCADE"), nullable=False
    )
    file_id = Column(Text, ForeignKey("file.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Text, nullable=False)

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "knowledge_id", "file_id", name="uq_knowledge_file_knowledge_file"
        ),
    )


class KnowledgeFileModel(BaseModel):
    id: str
    knowledge_id: str
    file_id: str
    user_id: str

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################
class KnowledgeUserModel(KnowledgeModel):
    user: UserResponse | None = None


class KnowledgeResponse(KnowledgeModel):
    files: list[FileMetadataResponse | dict] | None = None


class KnowledgeUserResponse(KnowledgeUserModel):
    pass


class KnowledgeForm(BaseModel):
    name: str
    description: str
    access_grants: list[dict] | None = None


class FileUserResponse(FileModelResponse):
    user: UserResponse | None = None


class KnowledgeListResponse(BaseModel):
    items: list[KnowledgeUserModel]
    total: int


class KnowledgeFileListResponse(BaseModel):
    items: list[FileUserResponse]
    total: int


class KnowledgeTable:
    async def _get_access_grants(
        self, knowledge_id: str, db: AsyncSession | None = None
    ) -> list[AccessGrantModel]:
        return await AccessGrants.get_grants_by_resource(
            "knowledge", knowledge_id, db=db
        )

    async def _to_knowledge_model(
        self,
        knowledge: Knowledge,
        access_grants: list[AccessGrantModel] | None = None,
        db: AsyncSession | None = None,
    ) -> KnowledgeModel:
        knowledge_data = KnowledgeModel.model_validate(knowledge).model_dump(
            exclude={"access_grants"}
        )
        knowledge_data["access_grants"] = (
            access_grants
            if access_grants is not None
            else await self._get_access_grants(knowledge_data["id"], db=db)
        )
        return KnowledgeModel.model_validate(knowledge_data)

    async def insert_new_knowledge(
        self, user_id: str, form_data: KnowledgeForm, db: AsyncSession | None = None
    ) -> KnowledgeModel | None:
        async with get_async_db_context(db) as db:
            knowledge = KnowledgeModel(
                **{
                    **form_data.model_dump(exclude={"access_grants"}),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                    "access_grants": [],
                }
            )

            try:
                result = Knowledge(**knowledge.model_dump(exclude={"access_grants"}))
                db.add(result)
                await db.commit()
                await db.refresh(result)
                await AccessGrants.set_access_grants(
                    "knowledge", result.id, form_data.access_grants, db=db
                )
                if result:
                    return await self._to_knowledge_model(result, db=db)
                else:
                    return None
            except Exception:
                return None

    async def get_knowledge_bases(
        self, skip: int = 0, limit: int = 30, db: AsyncSession | None = None
    ) -> list[KnowledgeUserModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Knowledge).order_by(Knowledge.updated_at.desc())
            )
            all_knowledge = result.scalars().all()
            user_ids = list(set(knowledge.user_id for knowledge in all_knowledge))
            knowledge_ids = [knowledge.id for knowledge in all_knowledge]

            users = (
                await Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
            )
            users_dict = {user.id: user for user in users}
            grants_map = await AccessGrants.get_grants_by_resources(
                "knowledge", knowledge_ids, db=db
            )

            knowledge_bases = []
            for knowledge in all_knowledge:
                user = users_dict.get(knowledge.user_id)
                knowledge_bases.append(
                    KnowledgeUserModel.model_validate(
                        {
                            **(
                                await self._to_knowledge_model(
                                    knowledge,
                                    access_grants=grants_map.get(knowledge.id, []),
                                    db=db,
                                )
                            ).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )
            return knowledge_bases

    async def search_knowledge_bases(
        self,
        user_id: str,
        filter: dict,
        skip: int = 0,
        limit: int = 30,
        db: AsyncSession | None = None,
    ) -> KnowledgeListResponse:
        try:
            async with get_async_db_context(db) as db:
                stmt = select(Knowledge, User).outerjoin(
                    User, User.id == Knowledge.user_id
                )

                if filter:
                    query_key = filter.get("query")
                    if query_key:
                        stmt = stmt.filter(
                            or_(
                                Knowledge.name.ilike(f"%{query_key}%"),
                                Knowledge.description.ilike(f"%{query_key}%"),
                                User.name.ilike(f"%{query_key}%"),
                                User.email.ilike(f"%{query_key}%"),
                                User.username.ilike(f"%{query_key}%"),
                            )
                        )

                    view_option = filter.get("view_option")
                    if view_option == "created":
                        stmt = stmt.filter(Knowledge.user_id == user_id)
                    elif view_option == "shared":
                        stmt = stmt.filter(Knowledge.user_id != user_id)

                    stmt = AccessGrants.has_permission_filter(
                        db=db,
                        query=stmt,
                        DocumentModel=Knowledge,
                        filter=filter,
                        resource_type="knowledge",
                        permission="read",
                    )

                stmt = stmt.order_by(Knowledge.updated_at.desc(), Knowledge.id.asc())

                count_result = await db.execute(
                    select(func.count()).select_from(stmt.subquery())
                )
                total = count_result.scalar()
                if skip:
                    stmt = stmt.offset(skip)
                if limit:
                    stmt = stmt.limit(limit)

                result = await db.execute(stmt)
                items = result.all()

                knowledge_ids = [kb.id for kb, _ in items]
                grants_map = await AccessGrants.get_grants_by_resources(
                    "knowledge", knowledge_ids, db=db
                )

                knowledge_bases = []
                for knowledge_base, user in items:
                    knowledge_bases.append(
                        KnowledgeUserModel.model_validate(
                            {
                                **(
                                    await self._to_knowledge_model(
                                        knowledge_base,
                                        access_grants=grants_map.get(
                                            knowledge_base.id, []
                                        ),
                                        db=db,
                                    )
                                ).model_dump(),
                                "user": (
                                    UserModel.model_validate(user).model_dump()
                                    if user
                                    else None
                                ),
                            }
                        )
                    )

                return KnowledgeListResponse(items=knowledge_bases, total=total)
        except Exception as e:
            print(e)
            return KnowledgeListResponse(items=[], total=0)

    async def search_knowledge_files(
        self,
        filter: dict,
        skip: int = 0,
        limit: int = 30,
        db: AsyncSession | None = None,
    ) -> KnowledgeFileListResponse:
        """
        Scalable version: search files across all knowledge bases the user has
        READ access to, without loading all KBs or using large IN() lists.
        """
        try:
            async with get_async_db_context(db) as db:
                # Base query: join Knowledge → KnowledgeFile → File
                stmt = (
                    select(File, User, Knowledge)
                    .join(KnowledgeFile, File.id == KnowledgeFile.file_id)
                    .join(Knowledge, KnowledgeFile.knowledge_id == Knowledge.id)
                    .outerjoin(User, User.id == KnowledgeFile.user_id)
                )

                # Apply access-control directly to the joined query
                stmt = AccessGrants.has_permission_filter(
                    db=db,
                    query=stmt,
                    DocumentModel=Knowledge,
                    filter=filter,
                    resource_type="knowledge",
                    permission="read",
                )

                # Apply filename / content search
                if filter:
                    q = filter.get("query")
                    if q:
                        stmt = stmt.filter(
                            or_(
                                File.filename.ilike(f"%{q}%"),
                                cast(File.data["content"], Text).ilike(f"%{q}%"),
                            )
                        )

                # Order by file changes
                stmt = stmt.order_by(File.updated_at.desc(), File.id.asc())

                # Count before pagination
                count_result = await db.execute(
                    select(func.count()).select_from(stmt.subquery())
                )
                total = count_result.scalar()

                if skip:
                    stmt = stmt.offset(skip)
                if limit:
                    stmt = stmt.limit(limit)

                result = await db.execute(stmt)
                rows = result.all()

                items = []
                for file, user, knowledge in rows:
                    items.append(
                        FileUserResponse(
                            **FileModel.model_validate(file).model_dump(),
                            user=(
                                UserResponse(
                                    **UserModel.model_validate(user).model_dump()
                                )
                                if user
                                else None
                            ),
                            collection=(
                                await self._to_knowledge_model(knowledge, db=db)
                            ).model_dump(),
                        )
                    )

                return KnowledgeFileListResponse(items=items, total=total)

        except Exception as e:
            print("search_knowledge_files error:", e)
            return KnowledgeFileListResponse(items=[], total=0)

    async def check_access_by_user_id(
        self, id, user_id, permission="write", db: AsyncSession | None = None
    ) -> bool:
        knowledge = await self.get_knowledge_by_id(id, db=db)
        if not knowledge:
            return False
        if knowledge.user_id == user_id:
            return True
        user_groups = await Groups.get_groups_by_member_id(user_id, db=db)
        user_group_ids = {group.id for group in user_groups}
        return await AccessGrants.has_access(
            user_id=user_id,
            resource_type="knowledge",
            resource_id=knowledge.id,
            permission=permission,
            user_group_ids=user_group_ids,
            db=db,
        )

    async def get_knowledge_bases_by_user_id(
        self, user_id: str, permission: str = "write", db: AsyncSession | None = None
    ) -> list[KnowledgeUserModel]:
        knowledge_bases = await self.get_knowledge_bases(db=db)
        user_groups = await Groups.get_groups_by_member_id(user_id, db=db)
        user_group_ids = {group.id for group in user_groups}

        result = []
        for knowledge_base in knowledge_bases:
            if knowledge_base.user_id == user_id:
                result.append(knowledge_base)
            elif await AccessGrants.has_access(
                user_id=user_id,
                resource_type="knowledge",
                resource_id=knowledge_base.id,
                permission=permission,
                user_group_ids=user_group_ids,
                db=db,
            ):
                result.append(knowledge_base)
        return result

    async def get_knowledge_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> KnowledgeModel | None:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Knowledge).filter_by(id=id))
                knowledge = result.scalars().first()
                return (
                    await self._to_knowledge_model(knowledge, db=db)
                    if knowledge
                    else None
                )
        except Exception:
            return None

    async def get_knowledge_by_id_and_user_id(
        self, id: str, user_id: str, db: AsyncSession | None = None
    ) -> KnowledgeModel | None:
        knowledge = await self.get_knowledge_by_id(id, db=db)
        if not knowledge:
            return None

        if knowledge.user_id == user_id:
            return knowledge

        user_groups = await Groups.get_groups_by_member_id(user_id, db=db)
        user_group_ids = {group.id for group in user_groups}
        if await AccessGrants.has_access(
            user_id=user_id,
            resource_type="knowledge",
            resource_id=knowledge.id,
            permission="write",
            user_group_ids=user_group_ids,
            db=db,
        ):
            return knowledge
        return None

    async def get_knowledges_by_file_id(
        self, file_id: str, db: AsyncSession | None = None
    ) -> list[KnowledgeModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(
                    select(Knowledge)
                    .join(KnowledgeFile, Knowledge.id == KnowledgeFile.knowledge_id)
                    .filter(KnowledgeFile.file_id == file_id)
                )
                knowledges = result.scalars().all()
                knowledge_ids = [k.id for k in knowledges]
                grants_map = await AccessGrants.get_grants_by_resources(
                    "knowledge", knowledge_ids, db=db
                )
                return [
                    await self._to_knowledge_model(
                        knowledge,
                        access_grants=grants_map.get(knowledge.id, []),
                        db=db,
                    )
                    for knowledge in knowledges
                ]
        except Exception:
            return []

    async def search_files_by_id(
        self,
        knowledge_id: str,
        user_id: str,
        filter: dict,
        skip: int = 0,
        limit: int = 30,
        db: AsyncSession | None = None,
    ) -> KnowledgeFileListResponse:
        try:
            async with get_async_db_context(db) as db:
                stmt = (
                    select(File, User)
                    .join(KnowledgeFile, File.id == KnowledgeFile.file_id)
                    .outerjoin(User, User.id == KnowledgeFile.user_id)
                    .filter(KnowledgeFile.knowledge_id == knowledge_id)
                )

                # Default sort: updated_at descending
                primary_sort = File.updated_at.desc()

                if filter:
                    query_key = filter.get("query")
                    if query_key:
                        stmt = stmt.filter(
                            or_(
                                File.filename.ilike(f"%{query_key}%"),
                                cast(File.data["content"], Text).ilike(
                                    f"%{query_key}%"
                                ),
                            )
                        )

                    view_option = filter.get("view_option")
                    if view_option == "created":
                        stmt = stmt.filter(KnowledgeFile.user_id == user_id)
                    elif view_option == "shared":
                        stmt = stmt.filter(KnowledgeFile.user_id != user_id)

                    order_by = filter.get("order_by")
                    direction = filter.get("direction")
                    is_asc = direction == "asc"

                    if order_by == "name":
                        primary_sort = (
                            File.filename.asc() if is_asc else File.filename.desc()
                        )
                    elif order_by == "created_at":
                        primary_sort = (
                            File.created_at.asc() if is_asc else File.created_at.desc()
                        )
                    elif order_by == "updated_at":
                        primary_sort = (
                            File.updated_at.asc() if is_asc else File.updated_at.desc()
                        )

                # Apply sort with secondary key for deterministic pagination
                stmt = stmt.order_by(primary_sort, File.id.asc())

                # Count BEFORE pagination
                count_result = await db.execute(
                    select(func.count()).select_from(stmt.subquery())
                )
                total = count_result.scalar()

                if skip:
                    stmt = stmt.offset(skip)
                if limit:
                    stmt = stmt.limit(limit)

                result = await db.execute(stmt)
                items = result.all()

                files = []
                for file, user in items:
                    files.append(
                        FileUserResponse(
                            **FileModel.model_validate(file).model_dump(),
                            user=(
                                UserResponse(
                                    **UserModel.model_validate(user).model_dump()
                                )
                                if user
                                else None
                            ),
                        )
                    )

                return KnowledgeFileListResponse(items=files, total=total)
        except Exception as e:
            print(e)
            return KnowledgeFileListResponse(items=[], total=0)

    async def get_files_by_id(
        self, knowledge_id: str, db: AsyncSession | None = None
    ) -> list[FileModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(
                    select(File)
                    .join(KnowledgeFile, File.id == KnowledgeFile.file_id)
                    .filter(KnowledgeFile.knowledge_id == knowledge_id)
                )
                files = result.scalars().all()
                return [FileModel.model_validate(file) for file in files]
        except Exception:
            return []

    async def get_file_metadatas_by_id(
        self, knowledge_id: str, db: AsyncSession | None = None
    ) -> list[FileMetadataResponse]:
        try:
            files = await self.get_files_by_id(knowledge_id, db=db)
            return [FileMetadataResponse(**file.model_dump()) for file in files]
        except Exception:
            return []

    async def add_file_to_knowledge_by_id(
        self,
        knowledge_id: str,
        file_id: str,
        user_id: str,
        db: AsyncSession | None = None,
    ) -> KnowledgeFileModel | None:
        async with get_async_db_context(db) as db:
            knowledge_file = KnowledgeFileModel(
                **{
                    "id": str(uuid.uuid4()),
                    "knowledge_id": knowledge_id,
                    "file_id": file_id,
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            try:
                result = KnowledgeFile(**knowledge_file.model_dump())
                db.add(result)
                await db.commit()
                await db.refresh(result)
                if result:
                    return KnowledgeFileModel.model_validate(result)
                else:
                    return None
            except Exception:
                return None

    async def has_file(
        self, knowledge_id: str, file_id: str, db: AsyncSession | None = None
    ) -> bool:
        """Check whether a file belongs to a knowledge base."""
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(
                    select(KnowledgeFile)
                    .filter_by(knowledge_id=knowledge_id, file_id=file_id)
                    .limit(1)
                )
                return result.scalars().first() is not None
        except Exception:
            return False

    async def remove_file_from_knowledge_by_id(
        self, knowledge_id: str, file_id: str, db: AsyncSession | None = None
    ) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(
                    delete(KnowledgeFile).filter_by(
                        knowledge_id=knowledge_id, file_id=file_id
                    )
                )
                await db.commit()
                return True
        except Exception:
            return False

    async def reset_knowledge_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> KnowledgeModel | None:
        try:
            async with get_async_db_context(db) as db:
                # Delete all knowledge_file entries for this knowledge_id
                await db.execute(delete(KnowledgeFile).filter_by(knowledge_id=id))
                await db.commit()

                # Update the knowledge entry's updated_at timestamp
                await db.execute(
                    update(Knowledge)
                    .filter_by(id=id)
                    .values(updated_at=int(time.time()))
                )
                await db.commit()

                return await self.get_knowledge_by_id(id=id, db=db)
        except Exception as e:
            log.exception(e)
            return None

    async def update_knowledge_by_id(
        self,
        id: str,
        form_data: KnowledgeForm,
        overwrite: bool = False,
        db: AsyncSession | None = None,
    ) -> KnowledgeModel | None:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(
                    update(Knowledge)
                    .filter_by(id=id)
                    .values(
                        **form_data.model_dump(exclude={"access_grants"}),
                        updated_at=int(time.time()),
                    )
                )
                await db.commit()
                if form_data.access_grants is not None:
                    await AccessGrants.set_access_grants(
                        "knowledge", id, form_data.access_grants, db=db
                    )
                return await self.get_knowledge_by_id(id=id, db=db)
        except Exception as e:
            log.exception(e)
            return None

    async def update_knowledge_data_by_id(
        self, id: str, data: dict, db: AsyncSession | None = None
    ) -> KnowledgeModel | None:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(
                    update(Knowledge)
                    .filter_by(id=id)
                    .values(
                        data=data,
                        updated_at=int(time.time()),
                    )
                )
                await db.commit()
                return await self.get_knowledge_by_id(id=id, db=db)
        except Exception as e:
            log.exception(e)
            return None

    async def delete_knowledge_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await AccessGrants.revoke_all_access("knowledge", id, db=db)
                await db.execute(delete(Knowledge).filter_by(id=id))
                await db.commit()
                return True
        except Exception:
            return False

    async def delete_all_knowledge(self, db: AsyncSession | None = None) -> bool:
        async with get_async_db_context(db) as db:
            try:
                result = await db.execute(select(Knowledge.id))
                knowledge_ids = [row[0] for row in result.all()]
                for knowledge_id in knowledge_ids:
                    await AccessGrants.revoke_all_access(
                        "knowledge", knowledge_id, db=db
                    )
                await db.execute(delete(Knowledge))
                await db.commit()

                return True
            except Exception:
                return False


Knowledges = KnowledgeTable()
