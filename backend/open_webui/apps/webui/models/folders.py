import logging
import time
import uuid
from typing import Optional

from open_webui.apps.webui.internal.db import Base, get_db


from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Text, JSON, PrimaryKeyConstraint

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# Folder DB Schema
####################


class FolderItems(BaseModel):
    chat_ids: Optional[list[str]] = None
    file_ids: Optional[list[str]] = None
    folder_ids: Optional[list[str]] = None

    model_config = ConfigDict(extra="allow")


class Folder(Base):
    __tablename__ = "folder"
    id = Column(Text, primary_key=True)
    parent_id = Column(Text, nullable=True)
    user_id = Column(Text)
    name = Column(Text)
    items = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class FolderModel(BaseModel):
    id: str
    parent_id: Optional[str] = None
    user_id: str
    name: str
    items: Optional[FolderItems] = None
    meta: Optional[dict] = None
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class FolderTable:
    def insert_new_folder(self, name: str, user_id: str) -> Optional[FolderModel]:
        with get_db() as db:
            id = name.lower()
            folder = FolderModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "name": name,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            try:
                result = Folder(**folder.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return FolderModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                print(e)
                return None

    def get_folder_by_name_and_user_id(
        self, name: str, user_id: str
    ) -> Optional[FolderModel]:
        try:
            id = name.lower()
            with get_db() as db:
                folder = db.query(Folder).filter_by(id=id, user_id=user_id).first()
                return FolderModel.model_validate(folder)
        except Exception:
            return None

    def get_folders_by_user_id(self, user_id: str) -> list[FolderModel]:
        with get_db() as db:
            return [
                FolderModel.model_validate(folder)
                for folder in db.query(Folder).filter_by(user_id=user_id).all()
            ]

    def update_folder_by_name_and_user_id(
        self, name: str, user_id: str, items: FolderItems
    ) -> Optional[FolderModel]:
        try:
            id = name.lower()
            with get_db() as db:
                folder = db.query(Folder).filter_by(id=id, user_id=user_id).first()

                folder.items = items.model_dump()
                folder.updated_at = int(time.time())

                db.commit()

                return FolderModel.model_validate(folder)
        except Exception as e:
            log.error(f"update_folder: {e}")
            return

    def delete_folder_by_name_and_user_id(self, name: str, user_id: str) -> bool:
        try:
            with get_db() as db:
                id = name.lower()

                folder = db.query(Folder).filter_by(id=id, user_id=user_id).first()
                db.delete(folder)

                db.commit()
                return True
        except Exception as e:
            log.error(f"delete_folder: {e}")
            return False


Folders = FolderTable()
