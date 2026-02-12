import json
import logging
import time
from typing import Optional
import uuid

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, JSONField, get_db, get_db_context

from open_webui.models.files import (
    File,
    FileModel,
    FileMetadataResponse,
    FileModelResponse,
)
from open_webui.models.groups import Groups
from open_webui.models.users import User, UserModel, Users, UserResponse
from open_webui.models.access_grants import AccessGrantModel, AccessGrants


from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    BigInteger,
    Column,
    ForeignKey,
    String,
    Text,
    JSON,
    UniqueConstraint,
    or_,
)

log = logging.getLogger(__name__)

####################
# Knowledge DB Schema
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

    meta: Optional[dict] = None

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
    user: Optional[UserResponse] = None


class KnowledgeResponse(KnowledgeModel):
    files: Optional[list[FileMetadataResponse | dict]] = None


class KnowledgeUserResponse(KnowledgeUserModel):
    pass


class KnowledgeForm(BaseModel):
    name: str
    description: str
    access_grants: Optional[list[dict]] = None


class FileUserResponse(FileModelResponse):
    user: Optional[UserResponse] = None


class KnowledgeListResponse(BaseModel):
    items: list[KnowledgeUserModel]
    total: int


class KnowledgeFileListResponse(BaseModel):
    items: list[FileUserResponse]
    total: int


class KnowledgeTable:
    def _get_access_grants(
        self, knowledge_id: str, db: Optional[Session] = None
    ) -> list[AccessGrantModel]:
        return AccessGrants.get_grants_by_resource("knowledge", knowledge_id, db=db)

    def _to_knowledge_model(
        self, knowledge: Knowledge, db: Optional[Session] = None
    ) -> KnowledgeModel:
        knowledge_data = KnowledgeModel.model_validate(knowledge).model_dump(
            exclude={"access_grants"}
        )
        knowledge_data["access_grants"] = self._get_access_grants(
            knowledge_data["id"], db=db
        )
        return KnowledgeModel.model_validate(knowledge_data)

    def insert_new_knowledge(
        self, user_id: str, form_data: KnowledgeForm, db: Optional[Session] = None
    ) -> Optional[KnowledgeModel]:
        with get_db_context(db) as db:
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
                db.commit()
                db.refresh(result)
                AccessGrants.set_access_grants(
                    "knowledge", result.id, form_data.access_grants, db=db
                )
                if result:
                    return self._to_knowledge_model(result, db=db)
                else:
                    return None
            except Exception:
                return None

    def get_knowledge_bases(
        self, skip: int = 0, limit: int = 30, db: Optional[Session] = None
    ) -> list[KnowledgeUserModel]:
        with get_db_context(db) as db:
            all_knowledge = (
                db.query(Knowledge).order_by(Knowledge.updated_at.desc()).all()
            )
            user_ids = list(set(knowledge.user_id for knowledge in all_knowledge))

            users = Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
            users_dict = {user.id: user for user in users}

            knowledge_bases = []
            for knowledge in all_knowledge:
                user = users_dict.get(knowledge.user_id)
                knowledge_bases.append(
                    KnowledgeUserModel.model_validate(
                        {
                            **self._to_knowledge_model(knowledge, db=db).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )
            return knowledge_bases

    def search_knowledge_bases(
        self,
        user_id: str,
        filter: dict,
        skip: int = 0,
        limit: int = 30,
        db: Optional[Session] = None,
    ) -> KnowledgeListResponse:
        try:
            with get_db_context(db) as db:
                query = db.query(Knowledge, User).outerjoin(
                    User, User.id == Knowledge.user_id
                )

                if filter:
                    query_key = filter.get("query")
                    if query_key:
                        query = query.filter(
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
                        query = query.filter(Knowledge.user_id == user_id)
                    elif view_option == "shared":
                        query = query.filter(Knowledge.user_id != user_id)

                    query = AccessGrants.has_permission_filter(
                        db=db,
                        query=query,
                        DocumentModel=Knowledge,
                        filter=filter,
                        resource_type="knowledge",
                        permission="read",
                    )

                query = query.order_by(Knowledge.updated_at.desc(), Knowledge.id.asc())

                total = query.count()
                if skip:
                    query = query.offset(skip)
                if limit:
                    query = query.limit(limit)

                items = query.all()

                knowledge_bases = []
                for knowledge_base, user in items:
                    knowledge_bases.append(
                        KnowledgeUserModel.model_validate(
                            {
                                **self._to_knowledge_model(
                                    knowledge_base, db=db
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

    def search_knowledge_files(
        self, filter: dict, skip: int = 0, limit: int = 30, db: Optional[Session] = None
    ) -> KnowledgeFileListResponse:
        """
        Scalable version: search files across all knowledge bases the user has
        READ access to, without loading all KBs or using large IN() lists.
        """
        try:
            with get_db_context(db) as db:
                # Base query: join Knowledge → KnowledgeFile → File
                query = (
                    db.query(File, User, Knowledge)
                    .join(KnowledgeFile, File.id == KnowledgeFile.file_id)
                    .join(Knowledge, KnowledgeFile.knowledge_id == Knowledge.id)
                    .outerjoin(User, User.id == KnowledgeFile.user_id)
                )

                # Apply access-control directly to the joined query
                # This makes the database handle filtering, even with 10k+ KBs
                query = AccessGrants.has_permission_filter(
                    db=db,
                    query=query,
                    DocumentModel=Knowledge,
                    filter=filter,
                    resource_type="knowledge",
                    permission="read",
                )

                # Apply filename search
                if filter:
                    q = filter.get("query")
                    if q:
                        query = query.filter(File.filename.ilike(f"%{q}%"))

                # Order by file changes
                query = query.order_by(File.updated_at.desc(), File.id.asc())

                # Count before pagination
                total = query.count()

                if skip:
                    query = query.offset(skip)
                if limit:
                    query = query.limit(limit)

                rows = query.all()

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
                            collection=self._to_knowledge_model(
                                knowledge, db=db
                            ).model_dump(),
                        )
                    )

                return KnowledgeFileListResponse(items=items, total=total)

        except Exception as e:
            print("search_knowledge_files error:", e)
            return KnowledgeFileListResponse(items=[], total=0)

    def check_access_by_user_id(
        self, id, user_id, permission="write", db: Optional[Session] = None
    ) -> bool:
        knowledge = self.get_knowledge_by_id(id, db=db)
        if not knowledge:
            return False
        if knowledge.user_id == user_id:
            return True
        user_group_ids = {
            group.id for group in Groups.get_groups_by_member_id(user_id, db=db)
        }
        return AccessGrants.has_access(
            user_id=user_id,
            resource_type="knowledge",
            resource_id=knowledge.id,
            permission=permission,
            user_group_ids=user_group_ids,
            db=db,
        )

    def get_knowledge_bases_by_user_id(
        self, user_id: str, permission: str = "write", db: Optional[Session] = None
    ) -> list[KnowledgeUserModel]:
        knowledge_bases = self.get_knowledge_bases(db=db)
        user_group_ids = {
            group.id for group in Groups.get_groups_by_member_id(user_id, db=db)
        }
        return [
            knowledge_base
            for knowledge_base in knowledge_bases
            if knowledge_base.user_id == user_id
            or AccessGrants.has_access(
                user_id=user_id,
                resource_type="knowledge",
                resource_id=knowledge_base.id,
                permission=permission,
                user_group_ids=user_group_ids,
                db=db,
            )
        ]

    def get_knowledge_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[KnowledgeModel]:
        try:
            with get_db_context(db) as db:
                knowledge = db.query(Knowledge).filter_by(id=id).first()
                return self._to_knowledge_model(knowledge, db=db) if knowledge else None
        except Exception:
            return None

    def get_knowledge_by_id_and_user_id(
        self, id: str, user_id: str, db: Optional[Session] = None
    ) -> Optional[KnowledgeModel]:
        knowledge = self.get_knowledge_by_id(id, db=db)
        if not knowledge:
            return None

        if knowledge.user_id == user_id:
            return knowledge

        user_group_ids = {
            group.id for group in Groups.get_groups_by_member_id(user_id, db=db)
        }
        if AccessGrants.has_access(
            user_id=user_id,
            resource_type="knowledge",
            resource_id=knowledge.id,
            permission="write",
            user_group_ids=user_group_ids,
            db=db,
        ):
            return knowledge
        return None

    def get_knowledges_by_file_id(
        self, file_id: str, db: Optional[Session] = None
    ) -> list[KnowledgeModel]:
        try:
            with get_db_context(db) as db:
                knowledges = (
                    db.query(Knowledge)
                    .join(KnowledgeFile, Knowledge.id == KnowledgeFile.knowledge_id)
                    .filter(KnowledgeFile.file_id == file_id)
                    .all()
                )
                return [
                    self._to_knowledge_model(knowledge, db=db)
                    for knowledge in knowledges
                ]
        except Exception:
            return []

    def search_files_by_id(
        self,
        knowledge_id: str,
        user_id: str,
        filter: dict,
        skip: int = 0,
        limit: int = 30,
        db: Optional[Session] = None,
    ) -> KnowledgeFileListResponse:
        try:
            with get_db_context(db) as db:
                query = (
                    db.query(File, User)
                    .join(KnowledgeFile, File.id == KnowledgeFile.file_id)
                    .outerjoin(User, User.id == KnowledgeFile.user_id)
                    .filter(KnowledgeFile.knowledge_id == knowledge_id)
                )

                # Default sort: updated_at descending
                primary_sort = File.updated_at.desc()

                if filter:
                    query_key = filter.get("query")
                    if query_key:
                        query = query.filter(or_(File.filename.ilike(f"%{query_key}%")))

                    view_option = filter.get("view_option")
                    if view_option == "created":
                        query = query.filter(KnowledgeFile.user_id == user_id)
                    elif view_option == "shared":
                        query = query.filter(KnowledgeFile.user_id != user_id)

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
                query = query.order_by(primary_sort, File.id.asc())

                # Count BEFORE pagination
                total = query.count()

                if skip:
                    query = query.offset(skip)
                if limit:
                    query = query.limit(limit)

                items = query.all()

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

    def get_files_by_id(
        self, knowledge_id: str, db: Optional[Session] = None
    ) -> list[FileModel]:
        try:
            with get_db_context(db) as db:
                files = (
                    db.query(File)
                    .join(KnowledgeFile, File.id == KnowledgeFile.file_id)
                    .filter(KnowledgeFile.knowledge_id == knowledge_id)
                    .all()
                )
                return [FileModel.model_validate(file) for file in files]
        except Exception:
            return []

    def get_file_metadatas_by_id(
        self, knowledge_id: str, db: Optional[Session] = None
    ) -> list[FileMetadataResponse]:
        try:
            with get_db_context(db) as db:
                files = self.get_files_by_id(knowledge_id, db=db)
                return [FileMetadataResponse(**file.model_dump()) for file in files]
        except Exception:
            return []

    def add_file_to_knowledge_by_id(
        self,
        knowledge_id: str,
        file_id: str,
        user_id: str,
        db: Optional[Session] = None,
    ) -> Optional[KnowledgeFileModel]:
        with get_db_context(db) as db:
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
                db.commit()
                db.refresh(result)
                if result:
                    return KnowledgeFileModel.model_validate(result)
                else:
                    return None
            except Exception:
                return None

    def remove_file_from_knowledge_by_id(
        self, knowledge_id: str, file_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(KnowledgeFile).filter_by(
                    knowledge_id=knowledge_id, file_id=file_id
                ).delete()
                db.commit()
                return True
        except Exception:
            return False

    def reset_knowledge_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[KnowledgeModel]:
        try:
            with get_db_context(db) as db:
                # Delete all knowledge_file entries for this knowledge_id
                db.query(KnowledgeFile).filter_by(knowledge_id=id).delete()
                db.commit()

                # Update the knowledge entry's updated_at timestamp
                db.query(Knowledge).filter_by(id=id).update(
                    {
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()

                return self.get_knowledge_by_id(id=id, db=db)
        except Exception as e:
            log.exception(e)
            return None

    def update_knowledge_by_id(
        self,
        id: str,
        form_data: KnowledgeForm,
        overwrite: bool = False,
        db: Optional[Session] = None,
    ) -> Optional[KnowledgeModel]:
        try:
            with get_db_context(db) as db:
                knowledge = self.get_knowledge_by_id(id=id, db=db)
                db.query(Knowledge).filter_by(id=id).update(
                    {
                        **form_data.model_dump(exclude={"access_grants"}),
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()
                if form_data.access_grants is not None:
                    AccessGrants.set_access_grants(
                        "knowledge", id, form_data.access_grants, db=db
                    )
                return self.get_knowledge_by_id(id=id, db=db)
        except Exception as e:
            log.exception(e)
            return None

    def update_knowledge_data_by_id(
        self, id: str, data: dict, db: Optional[Session] = None
    ) -> Optional[KnowledgeModel]:
        try:
            with get_db_context(db) as db:
                knowledge = self.get_knowledge_by_id(id=id, db=db)
                db.query(Knowledge).filter_by(id=id).update(
                    {
                        "data": data,
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()
                return self.get_knowledge_by_id(id=id, db=db)
        except Exception as e:
            log.exception(e)
            return None

    def delete_knowledge_by_id(self, id: str, db: Optional[Session] = None) -> bool:
        try:
            with get_db_context(db) as db:
                AccessGrants.revoke_all_access("knowledge", id, db=db)
                db.query(Knowledge).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception:
            return False

    def delete_all_knowledge(self, db: Optional[Session] = None) -> bool:
        with get_db_context(db) as db:
            try:
                knowledge_ids = [row[0] for row in db.query(Knowledge.id).all()]
                for knowledge_id in knowledge_ids:
                    AccessGrants.revoke_all_access("knowledge", knowledge_id, db=db)
                db.query(Knowledge).delete()
                db.commit()

                return True
            except Exception:
                return False


Knowledges = KnowledgeTable()
