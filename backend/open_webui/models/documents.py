import logging
from typing import Optional, List
import time

from open_webui.internal.db import Base, get_db


from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, String, JSON, Text, BigInteger

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# Document DB Schema
####################
class DocumentDB(Base):
    __tablename__ = "documentdb"
    id = Column(String, primary_key=True)
    file_name = Column(String)
    file_id = Column(String)
    collection_name = Column(String)
    page_content = Column(Text)

    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)

    meta = Column(JSON, nullable=True)


class DocumentModel(BaseModel):
    id: str
    file_name: str
    file_id: str
    collection_name: str
    page_content: str
    meta: Optional[dict] = None

    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


class DocumentTable:
    def insert_new_document(
        self,
        id: str,
        file_name: str,
        file_id: str,
        collection_name: str,
        page_content: str,
        meta: Optional[dict] = None,
    ) -> Optional[DocumentModel]:
        with get_db() as db:
            current_time = int(time.time())
            document = DocumentModel(
                **{
                    "id": id,
                    "file_name": file_name,
                    "file_id": file_id,
                    "collection_name": collection_name,
                    "page_content": page_content,
                    "meta": meta,
                    "created_at": current_time,
                    "updated_at": current_time,
                }
            )
            try:
                result = DocumentDB(**document.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return DocumentModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                print(e)
                return None

    def insert_new_docs(self, docs: List[DocumentModel]) -> List[DocumentModel]:
        with get_db() as db:
            try:
                result = [DocumentDB(**doc.model_dump()) for doc in docs]
                db.add_all(result)
                db.commit()
                db.refresh(result)
                return [DocumentModel.model_validate(doc) for doc in docs]
            except Exception as e:
                print(e)
                return None

    def get_document_by_ids(self, ids: List[str]) -> List[DocumentModel]:
        try:
            with get_db() as db:
                documents = db.query(DocumentDB).filter(DocumentDB.id.in_(ids)).all()
                return [DocumentModel.model_validate(doc) for doc in documents]
        except Exception:
            return []

    def delete_by_collection_name(self, collection_name: str) -> bool:
        try:
            with get_db() as db:
                res = (
                    db.query(DocumentDB)
                    .filter_by(collection_name=collection_name)
                    .delete()
                )
                log.debug(f"res: {res}")
                db.commit()
                return True
        except Exception as e:
            log.error(f"delete_documents: {e}")
            return False

    def delete_by_collection_name_and_file_id(
        self, collection_name: str, file_id: str
    ) -> bool:
        try:
            with get_db() as db:
                res = (
                    db.query(DocumentDB)
                    .filter_by(collection_name=collection_name, file_id=file_id)
                    .delete()
                )
                log.debug(f"res: {res}")
                db.commit()
                return True
        except Exception as e:
            log.error(f"delete_documents: {e}")
            return False


DocumentDBs = DocumentTable()
