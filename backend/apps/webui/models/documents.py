from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import time
import logging

from sqlalchemy import String, Column, BigInteger, Text

from apps.webui.internal.db import Base, get_db

import json

from config import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Documents DB Schema
####################


class Document(Base):
    __tablename__ = "document"

    collection_name = Column(String, primary_key=True)
    name = Column(String, unique=True)
    title = Column(Text)
    filename = Column(Text)
    content = Column(Text, nullable=True)
    user_id = Column(String)
    timestamp = Column(BigInteger)


class DocumentModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    collection_name: str
    name: str
    title: str
    filename: str
    content: Optional[str] = None
    user_id: str
    timestamp: int  # timestamp in epoch


####################
# Forms
####################


class DocumentResponse(BaseModel):
    collection_name: str
    name: str
    title: str
    filename: str
    content: Optional[dict] = None
    user_id: str
    timestamp: int  # timestamp in epoch


class DocumentUpdateForm(BaseModel):
    name: str
    title: str


class DocumentForm(DocumentUpdateForm):
    collection_name: str
    filename: str
    content: Optional[str] = None


class DocumentsTable:

    def insert_new_doc(
        self, user_id: str, form_data: DocumentForm
    ) -> Optional[DocumentModel]:
        with get_db() as db:

            document = DocumentModel(
                **{
                    **form_data.model_dump(),
                    "user_id": user_id,
                    "timestamp": int(time.time()),
                }
            )

            try:
                result = Document(**document.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return DocumentModel.model_validate(result)
                else:
                    return None
            except:
                return None

    def get_doc_by_name(self, name: str) -> Optional[DocumentModel]:
        try:
            with get_db() as db:

                document = db.query(Document).filter_by(name=name).first()
                return DocumentModel.model_validate(document) if document else None
        except:
            return None

    def get_docs(self) -> List[DocumentModel]:
        with get_db() as db:

            return [
                DocumentModel.model_validate(doc) for doc in db.query(Document).all()
            ]

    def update_doc_by_name(
        self, name: str, form_data: DocumentUpdateForm
    ) -> Optional[DocumentModel]:
        try:
            with get_db() as db:

                db.query(Document).filter_by(name=name).update(
                    {
                        "title": form_data.title,
                        "name": form_data.name,
                        "timestamp": int(time.time()),
                    }
                )
                db.commit()
                return self.get_doc_by_name(form_data.name)
        except Exception as e:
            log.exception(e)
            return None

    def update_doc_content_by_name(
        self, name: str, updated: dict
    ) -> Optional[DocumentModel]:
        try:
            doc = self.get_doc_by_name(name)
            doc_content = json.loads(doc.content if doc.content else "{}")
            doc_content = {**doc_content, **updated}

            with get_db() as db:

                db.query(Document).filter_by(name=name).update(
                    {
                        "content": json.dumps(doc_content),
                        "timestamp": int(time.time()),
                    }
                )
                db.commit()
                return self.get_doc_by_name(name)
        except Exception as e:
            log.exception(e)
            return None

    def delete_doc_by_name(self, name: str) -> bool:
        try:
            with get_db() as db:

                db.query(Document).filter_by(name=name).delete()
                db.commit()
                return True
        except:
            return False


Documents = DocumentsTable()
