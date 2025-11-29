import json
import logging
import time
from typing import Optional
import uuid

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from open_webui.models.files import FileMetadataResponse
from open_webui.models.groups import Groups
from open_webui.models.users import Users, UserResponse


from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON, ForeignKey, UniqueConstraint, Index

from open_webui.utils.access_control import has_access

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Knowledge DB Schema
####################


class Knowledge(Base):
    __tablename__ = "knowledge"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)

    name = Column(Text)
    description = Column(Text)

    data = Column(JSON, nullable=True)
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


class KnowledgeFile(Base):
    __tablename__ = "knowledge_file"
    __table_args__ = (
        UniqueConstraint("knowledge_id", "file_id", name="uq_knowledge_file_knowledge_id_file_id"),
        Index("idx_knowledge_file_knowledge_id", "knowledge_id"),
        Index("idx_knowledge_file_file_id", "file_id"),
    )

    id = Column(Text, unique=True, primary_key=True)
    knowledge_id = Column(Text, ForeignKey("knowledge.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(Text, nullable=False)
    user_id = Column(Text, nullable=False)

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class KnowledgeModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    name: str
    description: str

    data: Optional[dict] = None
    meta: Optional[dict] = None

    access_control: Optional[dict] = None

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class KnowledgeUserModel(KnowledgeModel):
    user: Optional[UserResponse] = None


class KnowledgeResponse(KnowledgeModel):
    files: Optional[list[FileMetadataResponse | dict]] = None


class KnowledgeUserResponse(KnowledgeUserModel):
    files: Optional[list[FileMetadataResponse | dict]] = None


class KnowledgeForm(BaseModel):
    name: str
    description: str
    data: Optional[dict] = None
    access_control: Optional[dict] = None


class KnowledgeFileModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    knowledge_id: str
    file_id: str
    user_id: str
    created_at: int
    updated_at: int


class KnowledgeFileForm(BaseModel):
    knowledge_id: str
    file_id: str


class KnowledgeFileTable:
    def insert_knowledge_file(
        self, knowledge_id: str, file_id: str, user_id: str
    ) -> Optional[KnowledgeFileModel]:
        with get_db() as db:
            try:
                knowledge_file = KnowledgeFileModel(
                    id=str(uuid.uuid4()),
                    knowledge_id=knowledge_id,
                    file_id=file_id,
                    user_id=user_id,
                    created_at=int(time.time()),
                    updated_at=int(time.time()),
                )

                result = KnowledgeFile(**knowledge_file.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                return KnowledgeFileModel.model_validate(result) if result else None
            except Exception as e:
                # Check if it's a duplicate entry error
                error_msg = str(e).lower()
                if "unique constraint" in error_msg or "duplicate" in error_msg:
                    log.warning(f"Duplicate file {file_id} in knowledge {knowledge_id}")
                else:
                    log.exception(e)
                return None

    def get_knowledge_files_by_knowledge_id(
        self, knowledge_id: str, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> list[KnowledgeFileModel]:
        with get_db() as db:
            query = db.query(KnowledgeFile).filter_by(knowledge_id=knowledge_id)

            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)

            return [
                KnowledgeFileModel.model_validate(kf)
                for kf in query.all()
            ]

    def get_knowledge_file_count_by_knowledge_id(self, knowledge_id: str) -> int:
        with get_db() as db:
            from sqlalchemy import func
            return db.query(func.count(KnowledgeFile.id)).filter_by(knowledge_id=knowledge_id).scalar()

    def get_file_ids_by_knowledge_id(
        self, knowledge_id: str, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> list[str]:
        knowledge_files = self.get_knowledge_files_by_knowledge_id(knowledge_id, limit, offset)
        return [kf.file_id for kf in knowledge_files]

    def get_file_ids_by_knowledge_ids(self, knowledge_ids: list[str]) -> dict[str, list[str]]:
        """Bulk fetch file_ids for multiple knowledge bases to avoid N+1 queries"""
        with get_db() as db:
            if not knowledge_ids:
                return {}

            knowledge_files = db.query(KnowledgeFile).filter(
                KnowledgeFile.knowledge_id.in_(knowledge_ids)
            ).all()

            # Group file_ids by knowledge_id
            result = {kid: [] for kid in knowledge_ids}
            for kf in knowledge_files:
                result[kf.knowledge_id].append(kf.file_id)

            return result

    def delete_knowledge_file(self, knowledge_id: str, file_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(KnowledgeFile).filter_by(
                    knowledge_id=knowledge_id, file_id=file_id
                ).delete()
                db.commit()
                return True
        except Exception as e:
            log.exception(e)
            return False

    def delete_knowledge_files_by_knowledge_id(self, knowledge_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(KnowledgeFile).filter_by(knowledge_id=knowledge_id).delete()
                db.commit()
                return True
        except Exception as e:
            log.exception(e)
            return False

    def delete_knowledge_files_by_file_id(self, file_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(KnowledgeFile).filter_by(file_id=file_id).delete()
                db.commit()
                return True
        except Exception as e:
            log.exception(e)
            return False


KnowledgeFiles = KnowledgeFileTable()


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

    def get_knowledge_bases(self) -> list[KnowledgeUserModel]:
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
