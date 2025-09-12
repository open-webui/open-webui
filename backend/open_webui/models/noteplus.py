import json
import time
import uuid
from typing import Optional, List, Dict

from open_webui.internal.db import Base, get_db
from open_webui.utils.access_control import has_access
from open_webui.models.users import Users, UserResponse

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON
from sqlalchemy import or_, func, select, and_, text
from sqlalchemy.sql import exists

####################
# NotePlus DB Schema
####################


class NotePlus(Base):
    __tablename__ = "noteplus"

    id = Column(Text, primary_key=True)
    user_id = Column(Text)

    title = Column(Text)
    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)
    
    # Category fields (3-level hierarchy)
    category_major = Column(Text, nullable=True)  # 대분류
    category_middle = Column(Text, nullable=True)  # 중분류
    category_minor = Column(Text, nullable=True)  # 소분류

    access_control = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class NotePlusModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    title: str
    data: Optional[dict] = None
    meta: Optional[dict] = None
    
    # Category fields
    category_major: Optional[str] = None
    category_middle: Optional[str] = None
    category_minor: Optional[str] = None

    access_control: Optional[dict] = None

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class NotePlusForm(BaseModel):
    title: str
    data: Optional[dict] = None
    meta: Optional[dict] = None
    category_major: Optional[str] = None
    category_middle: Optional[str] = None
    category_minor: Optional[str] = None
    access_control: Optional[dict] = None


class NotePlusUpdateForm(BaseModel):
    title: Optional[str] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    category_major: Optional[str] = None
    category_middle: Optional[str] = None
    category_minor: Optional[str] = None
    access_control: Optional[dict] = None


class NotePlusUserResponse(NotePlusModel):
    user: Optional[UserResponse] = None


class NotePlusCategoryTree(BaseModel):
    name: str
    children: Optional[Dict[str, 'NotePlusCategoryTree']] = None
    note_count: int = 0


####################
# NotePlus Table Operations
####################


class NotePlusTable:
    def insert_new_noteplus(
        self,
        form_data: NotePlusForm,
        user_id: str,
    ) -> Optional[NotePlusModel]:
        with get_db() as db:
            noteplus = NotePlusModel(
                **{
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    **form_data.model_dump(),
                    "created_at": int(time.time_ns()),
                    "updated_at": int(time.time_ns()),
                }
            )

            new_noteplus = NotePlus(**noteplus.model_dump())

            db.add(new_noteplus)
            db.commit()
            db.refresh(new_noteplus)
            
            return NotePlusModel.model_validate(new_noteplus)

    def get_noteplus_list(self) -> list[NotePlusModel]:
        with get_db() as db:
            noteplus_list = db.query(NotePlus).order_by(NotePlus.updated_at.desc()).all()
            return [NotePlusModel.model_validate(noteplus) for noteplus in noteplus_list]

    def get_noteplus_by_user_id(
        self, user_id: str, permission: str = "write"
    ) -> list[NotePlusModel]:
        noteplus_list = self.get_noteplus_list()
        return [
            noteplus
            for noteplus in noteplus_list
            if noteplus.user_id == user_id
            or has_access(user_id, permission, noteplus.access_control)
        ]

    def get_noteplus_by_id(self, id: str) -> Optional[NotePlusModel]:
        with get_db() as db:
            noteplus = db.query(NotePlus).filter(NotePlus.id == id).first()
            return NotePlusModel.model_validate(noteplus) if noteplus else None

    def get_noteplus_by_category(
        self, 
        user_id: str,
        category_major: Optional[str] = None,
        category_middle: Optional[str] = None,
        category_minor: Optional[str] = None,
        permission: str = "read"
    ) -> list[NotePlusModel]:
        with get_db() as db:
            query = db.query(NotePlus)
            
            # Filter by category hierarchy
            if category_major:
                query = query.filter(NotePlus.category_major == category_major)
            if category_middle:
                query = query.filter(NotePlus.category_middle == category_middle)
            if category_minor:
                query = query.filter(NotePlus.category_minor == category_minor)
            
            noteplus_list = query.order_by(NotePlus.updated_at.desc()).all()
            noteplus_models = [NotePlusModel.model_validate(np) for np in noteplus_list]
            
            # Filter by access control
            return [
                noteplus
                for noteplus in noteplus_models
                if noteplus.user_id == user_id
                or has_access(user_id, permission, noteplus.access_control)
            ]

    def get_category_tree(self, user_id: str) -> Dict[str, NotePlusCategoryTree]:
        """Get hierarchical category structure for user's notes"""
        noteplus_list = self.get_noteplus_by_user_id(user_id, "read")
        
        tree = {}
        
        for noteplus in noteplus_list:
            major = noteplus.category_major or "Uncategorized"
            middle = noteplus.category_middle or "General"
            minor = noteplus.category_minor or "Default"
            
            # Build tree structure
            if major not in tree:
                tree[major] = NotePlusCategoryTree(name=major, children={})
            tree[major].note_count += 1
            
            if middle not in tree[major].children:
                tree[major].children[middle] = NotePlusCategoryTree(name=middle, children={})
            tree[major].children[middle].note_count += 1
            
            if minor not in tree[major].children[middle].children:
                tree[major].children[middle].children[minor] = NotePlusCategoryTree(name=minor)
            tree[major].children[middle].children[minor].note_count += 1
        
        return tree

    def update_noteplus_by_id(
        self, id: str, form_data: NotePlusUpdateForm
    ) -> Optional[NotePlusModel]:
        with get_db() as db:
            noteplus = db.query(NotePlus).filter(NotePlus.id == id).first()
            if not noteplus:
                return None

            form_data_dict = form_data.model_dump(exclude_unset=True)

            # Update simple fields
            for field in ["title", "category_major", "category_middle", "category_minor", "access_control"]:
                if field in form_data_dict:
                    setattr(noteplus, field, form_data_dict[field])

            # Update JSON fields (merge)
            if "data" in form_data_dict:
                noteplus.data = {**noteplus.data, **form_data_dict["data"]} if noteplus.data else form_data_dict["data"]
            if "meta" in form_data_dict:
                noteplus.meta = {**noteplus.meta, **form_data_dict["meta"]} if noteplus.meta else form_data_dict["meta"]

            noteplus.updated_at = int(time.time_ns())

            db.commit()
            return NotePlusModel.model_validate(noteplus) if noteplus else None

    def delete_noteplus_by_id(self, id: str):
        with get_db() as db:
            db.query(NotePlus).filter(NotePlus.id == id).delete()
            db.commit()
            return True


NotesPlus = NotePlusTable()