import json
import logging
import time
from typing import Optional
import uuid

from open_webui.internal.db import Base, get_db

from open_webui.models.files import (
    File,
    FileModel,
    FileMetadataResponse,
    FileModelResponse,
)
from open_webui.models.groups import Groups
from open_webui.models.users import User, UserModel, Users, UserResponse


from pydantic import BaseModel, ConfigDict
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

from open_webui.utils.access_control import has_access
from open_webui.utils.db.access_control import has_permission


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
    access_control = Column(JSON, nullable=True)  # Controls data access levels.
    # Defines access control rules for this entry.
    # - `None`: Public access, available to all users with the "user" role.
    # - `{}`: Private access, restricted exclusively to the owner.
    # - Custom permissions: Specific access control for reading and writing;
    #   Can specify group or user-level restrictions:
    #   {
    #      "read": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      },
    #      "write": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      }
    #   }

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class KnowledgeModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    name: str
    description: str

    meta: Optional[dict] = None

    access_control: Optional[dict] = None

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
    access_control: Optional[dict] = None


class FileUserResponse(FileModelResponse):
    user: Optional[UserResponse] = None


class KnowledgeListResponse(BaseModel):
    items: list[KnowledgeUserModel]
    total: int


class KnowledgeFileListResponse(BaseModel):
    items: list[FileUserResponse]
    total: int


class KnowledgeTable:
    def insert_new_knowledge(
        self, user_id: str, form_data: KnowledgeForm
    ) -> Optional[KnowledgeModel]:
        with get_db() as db:
            knowledge = KnowledgeModel(
                **{
                    **form_data.model_dump(),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            try:
                result = Knowledge(**knowledge.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return KnowledgeModel.model_validate(result)
                else:
                    return None
            except Exception:
                return None

    def get_knowledge_bases(
        self, skip: int = 0, limit: int = 30
    ) -> list[KnowledgeUserModel]:
        with get_db() as db:
            all_knowledge = (
                db.query(Knowledge).order_by(Knowledge.updated_at.desc()).all()
            )
            user_ids = list(set(knowledge.user_id for knowledge in all_knowledge))

            users = Users.get_users_by_user_ids(user_ids) if user_ids else []
            users_dict = {user.id: user for user in users}

            knowledge_bases = []
            for knowledge in all_knowledge:
                user = users_dict.get(knowledge.user_id)
                knowledge_bases.append(
                    KnowledgeUserModel.model_validate(
                        {
                            **KnowledgeModel.model_validate(knowledge).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )
            return knowledge_bases

    def search_knowledge_bases(
        self, user_id: str, filter: dict, skip: int = 0, limit: int = 30
    ) -> KnowledgeListResponse:
        try:
            with get_db() as db:
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
                            )
                        )

                    view_option = filter.get("view_option")
                    if view_option == "created":
                        query = query.filter(Knowledge.user_id == user_id)
                    elif view_option == "shared":
                        query = query.filter(Knowledge.user_id != user_id)

                    query = has_permission(db, Knowledge, query, filter)

                query = query.order_by(Knowledge.updated_at.desc())

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
                                **KnowledgeModel.model_validate(
                                    knowledge_base
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
        self, filter: dict, skip: int = 0, limit: int = 30
    ) -> KnowledgeFileListResponse:
        """
        Scalable version: search files across all knowledge bases the user has
        READ access to, without loading all KBs or using large IN() lists.
        """
        try:
            with get_db() as db:
                # Base query: join Knowledge → KnowledgeFile → File
                query = (
                    db.query(File, User)
                    .join(KnowledgeFile, File.id == KnowledgeFile.file_id)
                    .join(Knowledge, KnowledgeFile.knowledge_id == Knowledge.id)
                    .outerjoin(User, User.id == KnowledgeFile.user_id)
                )

                # Apply access-control directly to the joined query
                # This makes the database handle filtering, even with 10k+ KBs
                query = has_permission(db, Knowledge, query, filter)

                # Apply filename search
                if filter:
                    q = filter.get("query")
                    if q:
                        query = query.filter(File.filename.ilike(f"%{q}%"))

                # Order by file changes
                query = query.order_by(File.updated_at.desc())

                # Count before pagination
                total = query.count()

                if skip:
                    query = query.offset(skip)
                if limit:
                    query = query.limit(limit)

                rows = query.all()

                items = []
                for file, user in rows:
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
                        )
                    )

                return KnowledgeFileListResponse(items=items, total=total)

        except Exception as e:
            print("search_knowledge_files error:", e)
            return KnowledgeFileListResponse(items=[], total=0)

    def check_access_by_user_id(self, id, user_id, permission="write") -> bool:
        knowledge = self.get_knowledge_by_id(id)
        if not knowledge:
            return False
        if knowledge.user_id == user_id:
            return True
        user_group_ids = {group.id for group in Groups.get_groups_by_member_id(user_id)}
        return has_access(user_id, permission, knowledge.access_control, user_group_ids)

    def get_knowledge_bases_by_user_id(
        self, user_id: str, permission: str = "write"
    ) -> list[KnowledgeUserModel]:
        knowledge_bases = self.get_knowledge_bases()
        user_group_ids = {group.id for group in Groups.get_groups_by_member_id(user_id)}
        return [
            knowledge_base
            for knowledge_base in knowledge_bases
            if knowledge_base.user_id == user_id
            or has_access(
                user_id, permission, knowledge_base.access_control, user_group_ids
            )
        ]

    def get_knowledge_by_id(self, id: str) -> Optional[KnowledgeModel]:
        try:
            with get_db() as db:
                knowledge = db.query(Knowledge).filter_by(id=id).first()
                return KnowledgeModel.model_validate(knowledge) if knowledge else None
        except Exception:
            return None

    def get_knowledge_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> Optional[KnowledgeModel]:
        knowledge = self.get_knowledge_by_id(id)
        if not knowledge:
            return None

        if knowledge.user_id == user_id:
            return knowledge

        user_group_ids = {group.id for group in Groups.get_groups_by_member_id(user_id)}
        if has_access(user_id, "write", knowledge.access_control, user_group_ids):
            return knowledge
        return None

    def get_knowledges_by_file_id(self, file_id: str) -> list[KnowledgeModel]:
        try:
            with get_db() as db:
                knowledges = (
                    db.query(Knowledge)
                    .join(KnowledgeFile, Knowledge.id == KnowledgeFile.knowledge_id)
                    .filter(KnowledgeFile.file_id == file_id)
                    .all()
                )
                return [
                    KnowledgeModel.model_validate(knowledge) for knowledge in knowledges
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
    ) -> KnowledgeFileListResponse:
        try:
            with get_db() as db:
                query = (
                    db.query(File, User)
                    .join(KnowledgeFile, File.id == KnowledgeFile.file_id)
                    .outerjoin(User, User.id == KnowledgeFile.user_id)
                    .filter(KnowledgeFile.knowledge_id == knowledge_id)
                )

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

                    if order_by == "name":
                        if direction == "asc":
                            query = query.order_by(File.filename.asc())
                        else:
                            query = query.order_by(File.filename.desc())
                    elif order_by == "created_at":
                        if direction == "asc":
                            query = query.order_by(File.created_at.asc())
                        else:
                            query = query.order_by(File.created_at.desc())
                    elif order_by == "updated_at":
                        if direction == "asc":
                            query = query.order_by(File.updated_at.asc())
                        else:
                            query = query.order_by(File.updated_at.desc())
                    else:
                        query = query.order_by(File.updated_at.desc())

                else:
                    query = query.order_by(File.updated_at.desc())

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

    def get_files_by_id(self, knowledge_id: str) -> list[FileModel]:
        try:
            with get_db() as db:
                files = (
                    db.query(File)
                    .join(KnowledgeFile, File.id == KnowledgeFile.file_id)
                    .filter(KnowledgeFile.knowledge_id == knowledge_id)
                    .all()
                )
                return [FileModel.model_validate(file) for file in files]
        except Exception:
            return []

    def get_file_metadatas_by_id(self, knowledge_id: str) -> list[FileMetadataResponse]:
        try:
            with get_db() as db:
                files = self.get_files_by_id(knowledge_id)
                return [FileMetadataResponse(**file.model_dump()) for file in files]
        except Exception:
            return []

    def add_file_to_knowledge_by_id(
        self, knowledge_id: str, file_id: str, user_id: str
    ) -> Optional[KnowledgeFileModel]:
        with get_db() as db:
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

    def remove_file_from_knowledge_by_id(self, knowledge_id: str, file_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(KnowledgeFile).filter_by(
                    knowledge_id=knowledge_id, file_id=file_id
                ).delete()
                db.commit()
                return True
        except Exception:
            return False

    def reset_knowledge_by_id(self, id: str) -> Optional[KnowledgeModel]:
        try:
            with get_db() as db:
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

                return self.get_knowledge_by_id(id=id)
        except Exception as e:
            log.exception(e)
            return None

    def update_knowledge_by_id(
        self, id: str, form_data: KnowledgeForm, overwrite: bool = False
    ) -> Optional[KnowledgeModel]:
        try:
            with get_db() as db:
                knowledge = self.get_knowledge_by_id(id=id)
                db.query(Knowledge).filter_by(id=id).update(
                    {
                        **form_data.model_dump(),
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()
                return self.get_knowledge_by_id(id=id)
        except Exception as e:
            log.exception(e)
            return None

    def update_knowledge_data_by_id(
        self, id: str, data: dict
    ) -> Optional[KnowledgeModel]:
        try:
            with get_db() as db:
                knowledge = self.get_knowledge_by_id(id=id)
                db.query(Knowledge).filter_by(id=id).update(
                    {
                        "data": data,
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()
                return self.get_knowledge_by_id(id=id)
        except Exception as e:
            log.exception(e)
            return None

    def delete_knowledge_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Knowledge).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception:
            return False

    def delete_all_knowledge(self) -> bool:
        with get_db() as db:
            try:
                db.query(Knowledge).delete()
                db.commit()

                return True
            except Exception:
                return False


Knowledges = KnowledgeTable()
