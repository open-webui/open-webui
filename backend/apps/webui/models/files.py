from pydantic import BaseModel, ConfigDict
from typing import List, Union, Optional
import time
import logging

from sqlalchemy import Column, String, BigInteger
from sqlalchemy.orm import Session

from apps.webui.internal.db import JSONField, Base

import json

from config import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Files DB Schema
####################


class File(Base):
    __tablename__ = "file"

    id = Column(String, primary_key=True)
    user_id = Column(String)
    filename = Column(String)
    meta = Column(JSONField)
    created_at = Column(BigInteger)


class FileModel(BaseModel):
    id: str
    user_id: str
    filename: str
    meta: dict
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)

####################
# Forms
####################


class FileModelResponse(BaseModel):
    id: str
    user_id: str
    filename: str
    meta: dict
    created_at: int  # timestamp in epoch


class FileForm(BaseModel):
    id: str
    filename: str
    meta: dict = {}


class FilesTable:

    def insert_new_file(self, db: Session, user_id: str, form_data: FileForm) -> Optional[FileModel]:
        file = FileModel(
            **{
                **form_data.model_dump(),
                "user_id": user_id,
                "created_at": int(time.time()),
            }
        )

        try:
            result = File(**file.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            if result:
                return FileModel.model_validate(result)
            else:
                return None
        except Exception as e:
            print(f"Error creating tool: {e}")
            return None

    def get_file_by_id(self, db: Session, id: str) -> Optional[FileModel]:
        try:
            file = db.get(File, id)
            return FileModel.model_validate(file)
        except:
            return None

    def get_files(self, db: Session) -> List[FileModel]:
        return [FileModel.model_validate(file) for file in db.query(File).all()]

    def delete_file_by_id(self, db: Session, id: str) -> bool:
        try:
            db.query(File).filter_by(id=id).delete()
            return True
        except:
            return False

    def delete_all_files(self, db: Session) -> bool:
        try:
            db.query(File).delete()
            return True
        except:
            return False


Files = FilesTable()
