import time
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, String, BigInteger, JSON, Text

from open_webui.internal.db import Base, get_db_context

####################
# StoryWeaver DB Schema
####################

class Novel(Base):
    __tablename__ = 'sw_novel'

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="draft")  # draft, in-progress, completed, archived

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class NovelModel(BaseModel):
    id: str
    user_id: str
    title: str
    description: Optional[str] = None
    status: str = "draft"
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class KnowledgeBase(Base):
    __tablename__ = 'sw_knowledge_base'

    id = Column(String, primary_key=True, unique=True)
    novel_id = Column(String, unique=True, nullable=False)
    
    universe_docs = Column(JSON, nullable=True)
    characters = Column(JSON, nullable=True)
    locations = Column(JSON, nullable=True)
    objects = Column(JSON, nullable=True)
    timeline = Column(JSON, nullable=True)

    updated_at = Column(BigInteger, nullable=False)


class KnowledgeBaseModel(BaseModel):
    id: str
    novel_id: str
    universe_docs: Optional[Any] = None
    characters: Optional[Any] = None
    locations: Optional[Any] = None
    objects: Optional[Any] = None
    timeline: Optional[Any] = None
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class Manuscript(Base):
    __tablename__ = 'sw_manuscript'

    id = Column(String, primary_key=True, unique=True)
    novel_id = Column(String, unique=True, nullable=False)
    
    content = Column(Text, nullable=True)
    chapter_structure = Column(JSON, nullable=True)
    word_count = Column(BigInteger, default=0)

    updated_at = Column(BigInteger, nullable=False)


class ManuscriptModel(BaseModel):
    id: str
    novel_id: str
    content: Optional[str] = None
    chapter_structure: Optional[Any] = None
    word_count: int = 0
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class Version(Base):
    __tablename__ = 'sw_version'

    id = Column(String, primary_key=True, unique=True)
    novel_id = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)  # character, location, scene, universe, novel
    entity_id = Column(String, nullable=False)
    
    old_data = Column(JSON, nullable=True)
    new_data = Column(JSON, nullable=False)
    
    change_type = Column(String, nullable=False)  # created, updated, deleted
    version_number = Column(BigInteger, nullable=False)
    
    timestamp = Column(BigInteger, nullable=False)


class VersionModel(BaseModel):
    id: str
    novel_id: str
    entity_type: str
    entity_id: str
    old_data: Optional[Any] = None
    new_data: Any
    change_type: str
    version_number: int
    timestamp: int

    model_config = ConfigDict(from_attributes=True)


class Chapter(Base):
    __tablename__ = 'sw_chapter'

    id = Column(String, primary_key=True, unique=True)
    novel_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    order = Column(BigInteger, nullable=False, default=0)
    status = Column(String, default="draft")  # draft, ready, review

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class ChapterModel(BaseModel):
    id: str
    novel_id: str
    title: str
    content: Optional[str] = ""
    order: int = 0
    status: str = "draft"
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# DAOs (Data Access Objects)
####################


class NovelsTable:
    def insert_new_novel(
        self,
        id: str,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        status: str = "draft",
        db: Optional[Session] = None,
    ) -> Optional[NovelModel]:
        with get_db_context(db) as db:
            now = int(time.time())
            novel = Novel(
                id=id,
                user_id=user_id,
                title=title,
                description=description,
                status=status,
                created_at=now,
                updated_at=now,
            )
            db.add(novel)
            db.commit()
            db.refresh(novel)
            return NovelModel.model_validate(novel) if novel else None

    def get_novel_by_id(self, id: str, user_id: Optional[str] = None, db: Optional[Session] = None) -> Optional[NovelModel]:
        try:
            with get_db_context(db) as db:
                query = db.query(Novel).filter_by(id=id)
                if user_id:
                    query = query.filter_by(user_id=user_id)
                novel = query.first()
                return NovelModel.model_validate(novel) if novel else None
        except Exception:
            return None

    def get_novels_by_user(self, user_id: str, db: Optional[Session] = None) -> list[NovelModel]:
        try:
            with get_db_context(db) as db:
                novels = db.query(Novel).filter_by(user_id=user_id).order_by(Novel.updated_at.desc()).all()
                return [NovelModel.model_validate(n) for n in novels]
        except Exception:
            return []

    def update_novel_by_id(self, id: str, updated: dict, user_id: Optional[str] = None, db: Optional[Session] = None) -> Optional[NovelModel]:
        try:
            with get_db_context(db) as db:
                query = db.query(Novel).filter_by(id=id)
                if user_id:
                    query = query.filter_by(user_id=user_id)
                novel = query.first()
                if not novel:
                    return None
                
                updated['updated_at'] = int(time.time())
                for key, value in updated.items():
                    if hasattr(novel, key):
                        setattr(novel, key, value)
                
                db.commit()
                db.refresh(novel)
                return NovelModel.model_validate(novel)
        except Exception:
            return None

    def delete_novel_by_id(self, id: str, user_id: Optional[str] = None, db: Optional[Session] = None) -> bool:
        try:
            with get_db_context(db) as db:
                query = db.query(Novel).filter_by(id=id)
                if user_id:
                    query = query.filter_by(user_id=user_id)
                
                novel = query.first()
                if not novel:
                    return False
                
                # Cascade deletions would manually happen here or via relationship
                db.query(KnowledgeBase).filter_by(novel_id=id).delete()
                db.query(Manuscript).filter_by(novel_id=id).delete()
                db.query(Version).filter_by(novel_id=id).delete()
                
                db.delete(novel)
                db.commit()
                return True
        except Exception:
            return False


class KnowledgeBasesTable:
    def insert_new_kb(
        self,
        id: str,
        novel_id: str,
        db: Optional[Session] = None,
    ) -> Optional[KnowledgeBaseModel]:
        with get_db_context(db) as db:
            kb = KnowledgeBase(
                id=id,
                novel_id=novel_id,
                universe_docs=[],
                characters=[],
                locations=[],
                objects=[],
                timeline=[],
                updated_at=int(time.time()),
            )
            db.add(kb)
            db.commit()
            db.refresh(kb)
            return KnowledgeBaseModel.model_validate(kb) if kb else None

    def get_kb_by_novel_id(self, novel_id: str, db: Optional[Session] = None) -> Optional[KnowledgeBaseModel]:
        try:
            with get_db_context(db) as db:
                kb = db.query(KnowledgeBase).filter_by(novel_id=novel_id).first()
                return KnowledgeBaseModel.model_validate(kb) if kb else None
        except Exception:
            return None

    def update_kb_by_novel_id(self, novel_id: str, updated: dict, db: Optional[Session] = None) -> Optional[KnowledgeBaseModel]:
        try:
            with get_db_context(db) as db:
                kb = db.query(KnowledgeBase).filter_by(novel_id=novel_id).first()
                if not kb:
                    return None
                
                updated['updated_at'] = int(time.time())
                for key, value in updated.items():
                    if hasattr(kb, key):
                        setattr(kb, key, value)
                
                db.commit()
                db.refresh(kb)
                return KnowledgeBaseModel.model_validate(kb)
        except Exception:
            return None


class ManuscriptsTable:
    def insert_new_manuscript(
        self,
        id: str,
        novel_id: str,
        db: Optional[Session] = None,
    ) -> Optional[ManuscriptModel]:
        with get_db_context(db) as db:
            m = Manuscript(
                id=id,
                novel_id=novel_id,
                content="",
                chapter_structure=[],
                word_count=0,
                updated_at=int(time.time()),
            )
            db.add(m)
            db.commit()
            db.refresh(m)
            return ManuscriptModel.model_validate(m) if m else None

    def get_manuscript_by_novel_id(self, novel_id: str, db: Optional[Session] = None) -> Optional[ManuscriptModel]:
        try:
            with get_db_context(db) as db:
                m = db.query(Manuscript).filter_by(novel_id=novel_id).first()
                return ManuscriptModel.model_validate(m) if m else None
        except Exception:
            return None

    def update_manuscript_by_novel_id(self, novel_id: str, updated: dict, db: Optional[Session] = None) -> Optional[ManuscriptModel]:
        try:
            with get_db_context(db) as db:
                m = db.query(Manuscript).filter_by(novel_id=novel_id).first()
                if not m:
                    return None
                
                updated['updated_at'] = int(time.time())
                for key, value in updated.items():
                    if hasattr(m, key):
                        setattr(m, key, value)
                
                db.commit()
                db.refresh(m)
                return ManuscriptModel.model_validate(m)
        except Exception:
            return None


class VersionsTable:
    def insert_new_version(
        self,
        id: str,
        novel_id: str,
        entity_type: str,
        entity_id: str,
        new_data: Any,
        change_type: str,
        version_number: int,
        old_data: Optional[Any] = None,
        db: Optional[Session] = None,
    ) -> Optional[VersionModel]:
        with get_db_context(db) as db:
            v = Version(
                id=id,
                novel_id=novel_id,
                entity_type=entity_type,
                entity_id=entity_id,
                old_data=old_data,
                new_data=new_data,
                change_type=change_type,
                version_number=version_number,
                timestamp=int(time.time()),
            )
            db.add(v)
            db.commit()
            db.refresh(v)
            return VersionModel.model_validate(v) if v else None

    def get_versions_by_entity(self, novel_id: str, entity_type: str, entity_id: str, db: Optional[Session] = None) -> list[VersionModel]:
        try:
            with get_db_context(db) as db:
                versions = db.query(Version).filter_by(
                    novel_id=novel_id,
                    entity_type=entity_type,
                    entity_id=entity_id
                ).order_by(Version.version_number.desc()).all()
                return [VersionModel.model_validate(v) for v in versions]
        except Exception:
            return []


class ChaptersTable:
    def insert_new_chapter(
        self,
        id: str,
        novel_id: str,
        title: str,
        order: int,
        content: str = "",
        status: str = "draft",
        db: Optional[Session] = None,
    ) -> Optional[ChapterModel]:
        with get_db_context(db) as db:
            now = int(time.time())
            chapter = Chapter(
                id=id,
                novel_id=novel_id,
                title=title,
                content=content,
                order=order,
                status=status,
                created_at=now,
                updated_at=now,
            )
            db.add(chapter)
            db.commit()
            db.refresh(chapter)
            return ChapterModel.model_validate(chapter) if chapter else None

    def get_chapters_by_novel_id(self, novel_id: str, db: Optional[Session] = None) -> list[ChapterModel]:
        try:
            with get_db_context(db) as db:
                chapters = db.query(Chapter).filter_by(novel_id=novel_id).order_by(Chapter.order.asc()).all()
                return [ChapterModel.model_validate(c) for c in chapters]
        except Exception:
            return []

    def get_chapter_by_id(self, id: str, db: Optional[Session] = None) -> Optional[ChapterModel]:
        try:
            with get_db_context(db) as db:
                chapter = db.query(Chapter).filter_by(id=id).first()
                return ChapterModel.model_validate(chapter) if chapter else None
        except Exception:
            return None

    def update_chapter_by_id(self, id: str, updated: dict, db: Optional[Session] = None) -> Optional[ChapterModel]:
        try:
            with get_db_context(db) as db:
                chapter = db.query(Chapter).filter_by(id=id).first()
                if not chapter:
                    return None
                
                updated['updated_at'] = int(time.time())
                for key, value in updated.items():
                    if hasattr(chapter, key):
                        setattr(chapter, key, value)
                
                db.commit()
                db.refresh(chapter)
                return ChapterModel.model_validate(chapter)
        except Exception:
            return None

    def delete_chapter_by_id(self, id: str, db: Optional[Session] = None) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(Chapter).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception:
            return False


# Global instances to mirror OpenWebUI's DAO pattern
Novels = NovelsTable()
KnowledgeBases = KnowledgeBasesTable()
Manuscripts = ManuscriptsTable()
Chapters = ChaptersTable()
Versions = VersionsTable()
