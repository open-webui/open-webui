from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import time
import logging
import os

from sqlalchemy import String, Column, BigInteger, Text

from apps.webui.internal.db import Base, get_db

import json

from utils.misc import (
    locate_document_in_filesystem,
)


from config import(
    SRC_LOG_LEVELS,
    UPLOAD_DIR,
    UPLOADS_DIR_NAME,
    DOCS_DIR,
    DOCS_DIR_NAME,
) 

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
    location = Column(Text)


class DocumentModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    collection_name: str
    name: str
    title: str
    filename: str
    content: Optional[str] = None
    user_id: str
    timestamp: int  # timestamp in epoch
    location: str


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
    location: str

class DocumentUpdateForm(BaseModel):
    name: str
    title: str


class DocumentForm(DocumentUpdateForm):
    collection_name: str
    filename: str
    content: Optional[str] = None
    location: Optional[str] = None  # This field is optional


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
                document = db.query(Document).filter_by(name=name).first()
                if not document:
                    log.warning(f"Document with name {name} not found")
                    return False

                # Log the document details
                log.debug(f"Document found: {document}")

                # Construct the directory path
                if document.location == UPLOADS_DIR_NAME:
                    search_dir = UPLOAD_DIR
                elif document.location == DOCS_DIR_NAME:
                    search_dir = DOCS_DIR
                else:
                    log.error(f"Invalid location: {document.location}")
                    return False

                log.debug(f"Searching in directory: {search_dir}")

                # Use the external function to find the file with the possible prefix
                file_path = locate_document_in_filesystem(search_dir, document.filename)

                log.debug(f"File path found: {file_path}")

                # Delete the file from the filesystem
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    log.debug(f"File {file_path} removed")
                else:
                    log.error(f"File not found: {file_path}")
                    return False

                # Delete the document from the database
                db.query(Document).filter_by(name=name).delete()
                db.commit()
                log.debug(f"Document with name {name} deleted from the database")
                return True
        except Exception as e:
            log.error(f"An error occurred while attempting to delete the document: {e}", exc_info=True)
            return False
        
    def delete_doc_by_name_only_from_db(self, name: str) -> bool:
        try:
            with get_db() as db:

                db.query(Document).filter_by(name=name).delete()
                db.commit()
                return True
        except:
            return False


Documents = DocumentsTable()
