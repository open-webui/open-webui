import logging
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.models.chats import Chats

from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Text, JSON, Boolean
from open_webui.utils.access_control import get_permissions


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# Folder DB Schema
####################


class Folder(Base):
    __tablename__ = "folder"
    id = Column(Text, primary_key=True)
    parent_id = Column(Text, nullable=True)
    user_id = Column(Text)
    name = Column(Text)
    items = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)
    data = Column(JSON, nullable=True)
    is_expanded = Column(Boolean, default=False)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class FolderModel(BaseModel):
    id: str
    parent_id: Optional[str] = None
    user_id: str
    name: str
    items: Optional[dict] = None
    meta: Optional[dict] = None
    data: Optional[dict] = None
    is_expanded: bool = False
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class FolderForm(BaseModel):
    name: str
    data: Optional[dict] = None
    model_config = ConfigDict(extra="allow")


class FolderTable:
    def insert_new_folder(
        self, user_id: str, form_data: FolderForm, parent_id: Optional[str] = None
    ) -> Optional[FolderModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            folder = FolderModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    **(form_data.model_dump(exclude_unset=True) or {}),
                    "parent_id": parent_id,
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
                log.exception(f"Error inserting a new folder: {e}")
                return None

    def get_folder_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> Optional[FolderModel]:
        try:
            with get_db() as db:
                folder = db.query(Folder).filter_by(id=id, user_id=user_id).first()

                if not folder:
                    return None

                return FolderModel.model_validate(folder)
        except Exception:
            return None

    def get_children_folders_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> Optional[FolderModel]:
        try:
            with get_db() as db:
                folders = []

                def get_children(folder):
                    children = self.get_folders_by_parent_id_and_user_id(
                        folder.id, user_id
                    )
                    for child in children:
                        get_children(child)
                        folders.append(child)

                folder = db.query(Folder).filter_by(id=id, user_id=user_id).first()
                if not folder:
                    return None

                get_children(folder)
                return folders
        except Exception:
            return None

    def get_folders_by_user_id(self, user_id: str) -> list[FolderModel]:
        with get_db() as db:
            return [
                FolderModel.model_validate(folder)
                for folder in db.query(Folder).filter_by(user_id=user_id).all()
            ]

    def get_folder_by_parent_id_and_user_id_and_name(
        self, parent_id: Optional[str], user_id: str, name: str
    ) -> Optional[FolderModel]:
        try:
            with get_db() as db:
                # Check if folder exists
                folder = (
                    db.query(Folder)
                    .filter_by(parent_id=parent_id, user_id=user_id)
                    .filter(Folder.name.ilike(name))
                    .first()
                )

                if not folder:
                    return None

                return FolderModel.model_validate(folder)
        except Exception as e:
            log.error(f"get_folder_by_parent_id_and_user_id_and_name: {e}")
            return None

    def get_folders_by_parent_id_and_user_id(
        self, parent_id: Optional[str], user_id: str
    ) -> list[FolderModel]:
        with get_db() as db:
            return [
                FolderModel.model_validate(folder)
                for folder in db.query(Folder)
                .filter_by(parent_id=parent_id, user_id=user_id)
                .all()
            ]

    def update_folder_parent_id_by_id_and_user_id(
        self,
        id: str,
        user_id: str,
        parent_id: str,
    ) -> Optional[FolderModel]:
        try:
            with get_db() as db:
                folder = db.query(Folder).filter_by(id=id, user_id=user_id).first()

                if not folder:
                    return None

                folder.parent_id = parent_id
                folder.updated_at = int(time.time())

                db.commit()

                return FolderModel.model_validate(folder)
        except Exception as e:
            log.error(f"update_folder: {e}")
            return

    def update_folder_by_id_and_user_id(
        self, id: str, user_id: str, form_data: FolderForm
    ) -> Optional[FolderModel]:
        try:
            with get_db() as db:
                folder = db.query(Folder).filter_by(id=id, user_id=user_id).first()

                if not folder:
                    return None

                form_data = form_data.model_dump(exclude_unset=True)

                existing_folder = (
                    db.query(Folder)
                    .filter_by(
                        name=form_data.get("name"),
                        parent_id=folder.parent_id,
                        user_id=user_id,
                    )
                    .first()
                )

                if existing_folder and existing_folder.id != id:
                    return None

                folder.name = form_data.get("name", folder.name)
                if "data" in form_data:
                    folder.data = {
                        **(folder.data or {}),
                        **form_data["data"],
                    }

                folder.updated_at = int(time.time())

                db.commit()

                return FolderModel.model_validate(folder)
        except Exception as e:
            log.error(f"update_folder: {e}")
            return

    def update_folder_is_expanded_by_id_and_user_id(
        self, id: str, user_id: str, is_expanded: bool
    ) -> Optional[FolderModel]:
        try:
            with get_db() as db:
                folder = db.query(Folder).filter_by(id=id, user_id=user_id).first()

                if not folder:
                    return None

                folder.is_expanded = is_expanded
                folder.updated_at = int(time.time())

                db.commit()

                return FolderModel.model_validate(folder)
        except Exception as e:
            log.error(f"update_folder: {e}")
            return

    def delete_folder_by_id_and_user_id(
        self, id: str, user_id: str, delete_chats=True
    ) -> bool:
        try:
            with get_db() as db:
                folder = db.query(Folder).filter_by(id=id, user_id=user_id).first()
                if not folder:
                    return False

                if delete_chats:
                    # Delete all chats in the folder
                    Chats.delete_chats_by_user_id_and_folder_id(user_id, folder.id)

                # Delete all children folders
                def delete_children(folder):
                    folder_children = self.get_folders_by_parent_id_and_user_id(
                        folder.id, user_id
                    )
                    for folder_child in folder_children:
                        if delete_chats:
                            Chats.delete_chats_by_user_id_and_folder_id(
                                user_id, folder_child.id
                            )

                        delete_children(folder_child)

                        folder = db.query(Folder).filter_by(id=folder_child.id).first()
                        db.delete(folder)
                        db.commit()

                delete_children(folder)
                db.delete(folder)
                db.commit()
                return True
        except Exception as e:
            log.error(f"delete_folder: {e}")
            return False


Folders = FolderTable()
