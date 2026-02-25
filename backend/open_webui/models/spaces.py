import logging
import time
import re
import uuid
from typing import Optional, List

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    Text,
    JSON,
    UniqueConstraint,
    or_,
)
from sqlalchemy.orm import Session

from open_webui.internal.db import Base, get_db_context, engine
from open_webui.models.knowledge import Knowledge, KnowledgeModel, KnowledgeResponse
from open_webui.models.users import Users, UserModel, UserResponse
from open_webui.models.files import File as FileRecord, FileModel, FileModelResponse
from open_webui.utils.access_control import has_access

log = logging.getLogger(__name__)


####################
# Permission & Access Constants
####################


# Permission levels (simplified from Perplexity's enum)
class SpacePermission:
    NONE = 0
    READER = 1
    WRITER = 2
    EDITOR = 3
    OWNER = 4


# Access levels for space visibility
class SpaceAccessLevel:
    PRIVATE = "private"  # Only owner and invited contributors
    ORG = "org"  # Anyone in organization
    PUBLIC = "public"  # Anyone with link


####################
# Space DB Schema
####################


class Space(Base):
    __tablename__ = "space"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text, nullable=False)

    name = Column(Text, nullable=False)
    slug = Column(Text, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    emoji = Column(Text, nullable=True)

    instructions = Column(Text, nullable=True)
    model_id = Column(Text, nullable=True)
    enable_web_by_default = Column(Boolean, default=True)

    access_level = Column(Text, default=SpaceAccessLevel.PRIVATE)

    meta = Column(JSON, nullable=True)
    access_control = Column(JSON, nullable=True)
    is_template = Column(Boolean, default=False)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class SpaceKnowledge(Base):
    __tablename__ = "space_knowledge"

    id = Column(Text, unique=True, primary_key=True)
    space_id = Column(Text, ForeignKey("space.id", ondelete="CASCADE"), nullable=False)
    knowledge_id = Column(
        Text, ForeignKey("knowledge.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(Text, nullable=False)
    created_at = Column(BigInteger)

    __table_args__ = (
        UniqueConstraint("space_id", "knowledge_id", name="uq_space_knowledge"),
    )


####################
# SpaceContributor DB Schema
####################


class SpaceContributor(Base):
    __tablename__ = "space_contributor"

    id = Column(Text, unique=True, primary_key=True)
    space_id = Column(Text, ForeignKey("space.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(
        Text, nullable=True
    )  # Null if invited by email but not yet accepted
    email = Column(Text, nullable=False)
    permission = Column(Integer, default=SpacePermission.WRITER)
    accepted = Column(Boolean, default=False)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    __table_args__ = (
        UniqueConstraint("space_id", "email", name="uq_space_contributor"),
    )


####################
# SpaceFile DB Schema (junction table)
####################


class SpaceFile(Base):
    __tablename__ = "space_file"

    id = Column(Text, unique=True, primary_key=True)
    space_id = Column(Text, ForeignKey("space.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(Text, ForeignKey("file.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Text, nullable=False)
    created_at = Column(BigInteger)

    __table_args__ = (UniqueConstraint("space_id", "file_id", name="uq_space_file"),)


####################
# SpaceSharePointFolder DB Schema
####################


class SpaceSharePointFolder(Base):
    __tablename__ = "space_sharepoint_folder"

    id = Column(Text, unique=True, primary_key=True)
    space_id = Column(Text, ForeignKey("space.id", ondelete="CASCADE"), nullable=False)
    drive_id = Column(Text, nullable=False)
    folder_id = Column(Text, nullable=True)  # None = root of drive
    folder_name = Column(Text, nullable=True)
    site_name = Column(Text, nullable=True)
    tenant_id = Column(Text, nullable=False)
    delta_link = Column(Text, nullable=True)  # Opaque @odata.deltaLink URL from Graph
    last_synced_at = Column(BigInteger, nullable=True)
    last_sync_added = Column(Integer, nullable=True)
    last_sync_updated = Column(Integer, nullable=True)
    last_sync_removed = Column(Integer, nullable=True)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    __table_args__ = (
        UniqueConstraint("space_id", "drive_id", "folder_id", name="uq_space_sp_folder"),
    )

####################
# SpaceLink DB Schema
####################


class SpaceLink(Base):
    __tablename__ = "space_link"

    id = Column(Text, unique=True, primary_key=True)
    space_id = Column(Text, ForeignKey("space.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    title = Column(Text, nullable=True)
    created_at = Column(BigInteger)


####################
# SpaceBookmark DB Schema
####################


class SpaceBookmark(Base):
    __tablename__ = "space_bookmark"

    id = Column(Text, unique=True, primary_key=True)
    space_id = Column(Text, ForeignKey("space.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Text, nullable=False)
    created_at = Column(BigInteger)

    __table_args__ = (
        UniqueConstraint("space_id", "user_id", name="uq_space_bookmark"),
    )


####################
# SpacePin DB Schema
####################


class SpacePin(Base):
    __tablename__ = "space_pin"

    id = Column(Text, unique=True, primary_key=True)
    space_id = Column(Text, ForeignKey("space.id", ondelete="CASCADE"), nullable=False)
    pinned_by = Column(Text, nullable=False)
    created_at = Column(BigInteger)

    __table_args__ = (UniqueConstraint("space_id", name="uq_space_pin"),)


####################
# SpaceSubscription DB Schema
####################


class SpaceSubscription(Base):
    __tablename__ = "space_subscription"

    id = Column(Text, unique=True, primary_key=True)
    space_id = Column(Text, ForeignKey("space.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Text, nullable=False)
    created_at = Column(BigInteger)

    __table_args__ = (
        UniqueConstraint("space_id", "user_id", name="uq_space_subscription"),
    )


####################
# SpaceNotification DB Schema
####################


class SpaceNotification(Base):
    __tablename__ = "space_notification"

    id = Column(Text, unique=True, primary_key=True)
    space_id = Column(Text, ForeignKey("space.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Text, nullable=False)  # recipient
    event_type = Column(Text, nullable=False)  # "thread_added", "thread_shared", etc.
    event_data = Column(JSON, nullable=True)
    read = Column(Boolean, default=False)
    created_at = Column(BigInteger)


####################
# Pydantic Models
####################


class SpaceModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    slug: str
    description: Optional[str] = None
    emoji: Optional[str] = None
    instructions: Optional[str] = None
    model_id: Optional[str] = None
    enable_web_by_default: bool = True
    access_level: str = SpaceAccessLevel.PRIVATE
    meta: Optional[dict] = None
    access_control: Optional[dict] = None
    is_template: bool = False
    created_at: int
    updated_at: int


class SpaceKnowledgeModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    space_id: str
    knowledge_id: str
    user_id: str
    created_at: int


class SpaceContributorModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    space_id: str
    user_id: Optional[str] = None
    email: str
    permission: int = SpacePermission.WRITER
    accepted: bool = False
    created_at: int
    updated_at: int


class SpaceContributorResponse(BaseModel):
    id: str
    space_id: str
    user_id: Optional[str] = None
    email: str
    permission: int
    accepted: bool
    user: Optional[UserResponse] = None


class SpaceFileModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    space_id: str
    file_id: str
    user_id: str
    created_at: int


class SpaceLinkModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    space_id: str
    user_id: str
    url: str
    title: Optional[str] = None
    created_at: int


class SpaceBookmarkModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    space_id: str
    user_id: str
    created_at: int


class SpacePinModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    space_id: str
    pinned_by: str
    created_at: int


class SpaceSubscriptionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    space_id: str
    user_id: str
    created_at: int


class SpaceNotificationModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    space_id: str
    user_id: str
    event_type: str
    event_data: Optional[dict] = None
    read: bool = False
    created_at: int


class SpaceSharePointFolderModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    space_id: str
    drive_id: str
    folder_id: Optional[str] = None
    folder_name: Optional[str] = None
    site_name: Optional[str] = None
    tenant_id: str
    delta_link: Optional[str] = None
    last_synced_at: Optional[int] = None
    last_sync_added: Optional[int] = None
    last_sync_updated: Optional[int] = None
    last_sync_removed: Optional[int] = None
    created_at: int
    updated_at: int



class SpaceResponse(SpaceModel):
    user: Optional[UserResponse] = None
    knowledge_bases: Optional[List[KnowledgeResponse]] = None
    contributors: Optional[List[SpaceContributorResponse]] = None
    user_permission: Optional[int] = None  # Current user's permission level


####################
# Forms
####################


class SpaceForm(BaseModel):
    name: str
    description: Optional[str] = None
    emoji: Optional[str] = None
    instructions: Optional[str] = None
    model_id: Optional[str] = None
    enable_web_by_default: bool = True
    access_control: Optional[dict] = None
    is_template: bool = False


class SpaceUpdateForm(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    emoji: Optional[str] = None
    instructions: Optional[str] = None
    model_id: Optional[str] = None
    enable_web_by_default: Optional[bool] = None
    access_control: Optional[dict] = None
    access_level: Optional[str] = None  # private, org, public
    is_template: Optional[bool] = None


class SpaceInviteForm(BaseModel):
    email: str


class SpaceInviteResponseForm(BaseModel):
    accept: bool


class SpaceAccessLevelForm(BaseModel):
    access_level: str  # private, org, public


class SpaceLinkForm(BaseModel):
    url: str
    title: Optional[str] = None


class SpaceBookmarkForm(BaseModel):
    space_id: str


class SpacePinForm(BaseModel):
    space_id: str


class SpaceCloneForm(BaseModel):
    name: str
    description: Optional[str] = None
    emoji: Optional[str] = None


####################
# Helper Functions
####################


def generate_slug(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\s-]", "", name.lower())
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug[:50] if slug else "space"


####################
# SpaceSharePointFolderTable
####################


class SpaceSharePointFolderTable:
    def upsert(
        self,
        space_id: str,
        drive_id: str,
        folder_id: Optional[str],
        folder_name: Optional[str],
        site_name: Optional[str],
        tenant_id: str,
        delta_link: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[SpaceSharePointFolderModel]:
        try:
            with get_db_context(db) as db:
                now = int(time.time())
                # Try to find existing record
                record = (
                    db.query(SpaceSharePointFolder)
                    .filter_by(space_id=space_id, drive_id=drive_id, folder_id=folder_id)
                    .first()
                )
                if record:
                    record.folder_name = folder_name
                    record.site_name = site_name
                    record.tenant_id = tenant_id
                    if delta_link is not None:
                        record.delta_link = delta_link
                    record.updated_at = now
                else:
                    record = SpaceSharePointFolder(
                        id=str(uuid.uuid4()),
                        space_id=space_id,
                        drive_id=drive_id,
                        folder_id=folder_id,
                        folder_name=folder_name,
                        site_name=site_name,
                        tenant_id=tenant_id,
                        delta_link=delta_link,
                        last_synced_at=None,
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(record)
                db.commit()
                db.refresh(record)
                return SpaceSharePointFolderModel.model_validate(record)
        except Exception as e:
            log.exception(f"Error upserting SpaceSharePointFolder: {e}")
            return None

    def get_by_space_id(
        self,
        space_id: str,
        db: Optional[Session] = None,
    ) -> List[SpaceSharePointFolderModel]:
        try:
            with get_db_context(db) as db:
                records = (
                    db.query(SpaceSharePointFolder)
                    .filter_by(space_id=space_id)
                    .all()
                )
                return [SpaceSharePointFolderModel.model_validate(r) for r in records]
        except Exception as e:
            log.exception(f"Error getting SpaceSharePointFolders by space_id: {e}")
            return []

    def get_by_space_and_folder(
        self,
        space_id: str,
        drive_id: str,
        folder_id: Optional[str],
        db: Optional[Session] = None,
    ) -> Optional[SpaceSharePointFolderModel]:
        try:
            with get_db_context(db) as db:
                record = (
                    db.query(SpaceSharePointFolder)
                    .filter_by(space_id=space_id, drive_id=drive_id, folder_id=folder_id)
                    .first()
                )
                if not record:
                    return None
                return SpaceSharePointFolderModel.model_validate(record)
        except Exception as e:
            log.exception(f"Error getting SpaceSharePointFolder: {e}")
            return None

    def update_delta_link(
        self,
        record_id: str,
        delta_link: str,
        last_synced_at: int,
        added: Optional[int] = None,
        updated: Optional[int] = None,
        removed: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> bool:
        try:
            with get_db_context(db) as db:
                record = (
                    db.query(SpaceSharePointFolder)
                    .filter_by(id=record_id)
                    .first()
                )
                if not record:
                    return False
                record.delta_link = delta_link
                record.last_synced_at = last_synced_at
                if added is not None:
                    record.last_sync_added = added
                if updated is not None:
                    record.last_sync_updated = updated
                if removed is not None:
                    record.last_sync_removed = removed
                record.updated_at = int(time.time())
                db.commit()
                return True
        except Exception as e:
            log.exception(f"Error updating delta_link: {e}")
            return False


    def get_all(self, db: Optional[Session] = None) -> List[SpaceSharePointFolderModel]:
        try:
            with get_db_context(db) as db:
                records = db.query(SpaceSharePointFolder).all()
                return [SpaceSharePointFolderModel.model_validate(r) for r in records]
        except Exception as e:
            log.exception(f"Error fetching all SpaceSharePointFolders: {e}")
            return []

    def get_by_id(self, folder_id: str, db: Optional[Session] = None) -> Optional[SpaceSharePointFolderModel]:
        try:
            with get_db_context(db) as db:
                record = db.query(SpaceSharePointFolder).filter_by(id=folder_id).first()
                if record:
                    return SpaceSharePointFolderModel.model_validate(record)
                return None
        except Exception as e:
            log.exception(f"Error fetching SpaceSharePointFolder {folder_id}: {e}")
            return None

    def delete_by_id(self, folder_id: str, db: Optional[Session] = None) -> bool:
        try:
            with get_db_context(db) as db:
                result = db.query(SpaceSharePointFolder).filter_by(id=folder_id).delete()
                db.commit()
                return result > 0
        except Exception as e:
            log.exception(f"Error deleting SpaceSharePointFolder {folder_id}: {e}")
            return False

SpaceSharePointFolders = SpaceSharePointFolderTable()



####################
# SpaceTable
####################


class SpaceTable:
    def insert_new_space(
        self,
        user_id: str,
        form_data: SpaceForm,
        db: Optional[Session] = None,
    ) -> Optional[SpaceModel]:
        with get_db_context(db) as db:
            space_id = str(uuid.uuid4())
            base_slug = generate_slug(form_data.name)
            slug = base_slug

            counter = 1
            while db.query(Space).filter_by(slug=slug).first():
                slug = f"{base_slug}-{counter}"
                counter += 1

            space = SpaceModel(
                id=space_id,
                user_id=user_id,
                name=form_data.name,
                slug=slug,
                description=form_data.description,
                emoji=form_data.emoji,
                instructions=form_data.instructions,
                model_id=form_data.model_id,
                enable_web_by_default=form_data.enable_web_by_default,
                access_control=form_data.access_control,
                is_template=form_data.is_template,
                created_at=int(time.time()),
                updated_at=int(time.time()),
            )

            try:
                result = Space(**space.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                return SpaceModel.model_validate(result) if result else None
            except Exception as e:
                log.exception(f"Error inserting new space: {e}")
                return None

    def get_space_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[SpaceModel]:
        try:
            with get_db_context(db) as db:
                space = db.query(Space).filter_by(id=id).first()
                return SpaceModel.model_validate(space) if space else None
        except Exception:
            return None

    def get_space_by_slug(
        self, slug: str, db: Optional[Session] = None
    ) -> Optional[SpaceModel]:
        try:
            with get_db_context(db) as db:
                space = db.query(Space).filter_by(slug=slug).first()
                return SpaceModel.model_validate(space) if space else None
        except Exception:
            return None

    def get_spaces(self, db: Optional[Session] = None) -> List[SpaceModel]:
        with get_db_context(db) as db:
            return [
                SpaceModel.model_validate(space)
                for space in db.query(Space).order_by(Space.updated_at.desc()).all()
            ]

    def get_spaces_by_user_id(
        self,
        user_id: str,
        permission: str = "read",
        category: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> List[SpaceModel]:
        with get_db_context(db) as db:
            # Get user's email for contributor lookups
            user_obj = Users.get_user_by_id(user_id)
            user_email = user_obj.email if user_obj else None

            spaces = self.get_spaces(db=db)

            # Get space IDs where user is a contributor
            contributor_space_ids = set()
            pending_space_ids = set()
            if user_email:
                contributors = (
                    db.query(SpaceContributor).filter_by(email=user_email).all()
                )
                for c in contributors:
                    if c.accepted:
                        contributor_space_ids.add(c.space_id)
                    else:
                        pending_space_ids.add(c.space_id)

            if category == "private":
                return [s for s in spaces if s.user_id == user_id]
            elif category == "shared":
                return [
                    s
                    for s in spaces
                    if s.id in contributor_space_ids and s.user_id != user_id
                ]
            elif category == "invited":
                return [s for s in spaces if s.id in pending_space_ids]
            else:
                # Default: all accessible spaces
                return [
                    space
                    for space in spaces
                    if space.user_id == user_id
                    or space.id in contributor_space_ids
                    or has_access(user_id, permission, space.access_control)
                ]

    def get_space_with_user_and_knowledge(
        self,
        id: str,
        current_user_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[SpaceResponse]:
        try:
            with get_db_context(db) as db:
                space = db.query(Space).filter_by(id=id).first()
                if not space:
                    return None

                space_model = SpaceModel.model_validate(space)
                user = Users.get_user_by_id(space.user_id)
                knowledge_bases = self.get_knowledge_bases_by_space_id(id, db=db)

                # Get contributors
                contributor_records = (
                    db.query(SpaceContributor).filter_by(space_id=id).all()
                )
                contributors = []
                user_permission = None

                for record in contributor_records:
                    contributor_user = None
                    if record.user_id:
                        u = Users.get_user_by_id(record.user_id)
                        if u:
                            contributor_user = UserResponse(
                                **UserModel.model_validate(u).model_dump()
                            )

                    contributors.append(
                        SpaceContributorResponse(
                            id=record.id,
                            space_id=record.space_id,
                            user_id=record.user_id,
                            email=record.email,
                            permission=record.permission,
                            accepted=record.accepted,
                            user=contributor_user,
                        )
                    )

                # Determine current user's permission
                if current_user_id:
                    if space.user_id == current_user_id:
                        user_permission = SpacePermission.OWNER
                    else:
                        current_user_obj = Users.get_user_by_id(current_user_id)
                        if current_user_obj:
                            for record in contributor_records:
                                if (
                                    record.email == current_user_obj.email
                                    and record.accepted
                                ):
                                    user_permission = record.permission
                                    break

                return SpaceResponse(
                    **space_model.model_dump(),
                    user=UserResponse(**UserModel.model_validate(user).model_dump())
                    if user
                    else None,
                    knowledge_bases=knowledge_bases,
                    contributors=contributors,
                    user_permission=user_permission,
                )
        except Exception as e:
            log.exception(f"Error getting space with details: {e}")
            return None

    def update_space_by_id(
        self,
        id: str,
        form_data: SpaceUpdateForm,
        db: Optional[Session] = None,
    ) -> Optional[SpaceModel]:
        try:
            with get_db_context(db) as db:
                space = db.query(Space).filter_by(id=id).first()
                if not space:
                    return None

                update_data = form_data.model_dump(exclude_unset=True)

                for key, value in update_data.items():
                    setattr(space, key, value)

                space.updated_at = int(time.time())
                db.commit()
                db.refresh(space)

                return SpaceModel.model_validate(space)
        except Exception as e:
            log.exception(f"Error updating space: {e}")
            return None

    def delete_space_by_id(self, id: str, db: Optional[Session] = None) -> bool:
        try:
            with get_db_context(db) as db:
                space = db.query(Space).filter_by(id=id).first()
                if not space:
                    return False

                db.query(SpaceKnowledge).filter_by(space_id=id).delete()
                db.query(SpaceContributor).filter_by(space_id=id).delete()
                db.query(SpaceFile).filter_by(space_id=id).delete()
                db.query(SpaceSharePointFolder).filter_by(space_id=id).delete()
                db.query(SpaceLink).filter_by(space_id=id).delete()
                db.query(SpaceBookmark).filter_by(space_id=id).delete()
                db.query(SpacePin).filter_by(space_id=id).delete()
                db.query(SpaceSubscription).filter_by(space_id=id).delete()
                db.query(SpaceNotification).filter_by(space_id=id).delete()
                db.delete(space)
                db.commit()
                return True
        except Exception as e:
            log.exception(f"Error deleting space: {e}")
            return False

    def add_knowledge_to_space(
        self,
        space_id: str,
        knowledge_id: str,
        user_id: str,
        db: Optional[Session] = None,
    ) -> Optional[SpaceKnowledgeModel]:
        with get_db_context(db) as db:
            existing = (
                db.query(SpaceKnowledge)
                .filter_by(space_id=space_id, knowledge_id=knowledge_id)
                .first()
            )
            if existing:
                return SpaceKnowledgeModel.model_validate(existing)

            space_knowledge = SpaceKnowledge(
                id=str(uuid.uuid4()),
                space_id=space_id,
                knowledge_id=knowledge_id,
                user_id=user_id,
                created_at=int(time.time()),
            )

            try:
                db.add(space_knowledge)
                db.commit()
                db.refresh(space_knowledge)
                return SpaceKnowledgeModel.model_validate(space_knowledge)
            except Exception as e:
                log.exception(f"Error adding knowledge to space: {e}")
                return None

    def remove_knowledge_from_space(
        self,
        space_id: str,
        knowledge_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        try:
            with get_db_context(db) as db:
                result = (
                    db.query(SpaceKnowledge)
                    .filter_by(space_id=space_id, knowledge_id=knowledge_id)
                    .delete()
                )
                db.commit()
                return result > 0
        except Exception as e:
            log.exception(f"Error removing knowledge from space: {e}")
            return False

    def get_knowledge_bases_by_space_id(
        self,
        space_id: str,
        db: Optional[Session] = None,
    ) -> List[KnowledgeResponse]:
        try:
            with get_db_context(db) as db:
                space_knowledge_records = (
                    db.query(SpaceKnowledge).filter_by(space_id=space_id).all()
                )

                knowledge_bases = []
                for record in space_knowledge_records:
                    knowledge = (
                        db.query(Knowledge).filter_by(id=record.knowledge_id).first()
                    )
                    if knowledge:
                        user = Users.get_user_by_id(knowledge.user_id)
                        knowledge_bases.append(
                            KnowledgeResponse(
                                **KnowledgeModel.model_validate(knowledge).model_dump(),
                                user=UserResponse(
                                    **UserModel.model_validate(user).model_dump()
                                )
                                if user
                                else None,
                            )
                        )

                return knowledge_bases
        except Exception as e:
            log.exception(f"Error getting knowledge bases for space: {e}")
            return []

    def get_spaces_by_knowledge_id(
        self,
        knowledge_id: str,
        db: Optional[Session] = None,
    ) -> List[SpaceModel]:
        try:
            with get_db_context(db) as db:
                space_knowledge_records = (
                    db.query(SpaceKnowledge).filter_by(knowledge_id=knowledge_id).all()
                )

                spaces = []
                for record in space_knowledge_records:
                    space = db.query(Space).filter_by(id=record.space_id).first()
                    if space:
                        spaces.append(SpaceModel.model_validate(space))

                return spaces
        except Exception as e:
            log.exception(f"Error getting spaces for knowledge: {e}")
            return []

    ####################
    # Contributor Methods
    ####################

    def invite_contributor(
        self,
        space_id: str,
        email: str,
        permission: int = SpacePermission.WRITER,
        db: Optional[Session] = None,
    ) -> Optional[SpaceContributorModel]:
        with get_db_context(db) as db:
            # Check if already invited
            existing = (
                db.query(SpaceContributor)
                .filter_by(space_id=space_id, email=email)
                .first()
            )
            if existing:
                return SpaceContributorModel.model_validate(existing)

            # Look up user by email to pre-fill user_id
            user = Users.get_user_by_email(email)
            user_id = user.id if user else None

            now = int(time.time())
            contributor = SpaceContributor(
                id=str(uuid.uuid4()),
                space_id=space_id,
                user_id=user_id,
                email=email,
                permission=permission,
                accepted=False,
                created_at=now,
                updated_at=now,
            )

            try:
                db.add(contributor)
                db.commit()
                db.refresh(contributor)
                return SpaceContributorModel.model_validate(contributor)
            except Exception as e:
                log.exception(f"Error inviting contributor: {e}")
                return None

    def respond_to_invitation(
        self,
        space_id: str,
        email: str,
        accept: bool,
        db: Optional[Session] = None,
    ) -> bool:
        try:
            with get_db_context(db) as db:
                contributor = (
                    db.query(SpaceContributor)
                    .filter_by(space_id=space_id, email=email, accepted=False)
                    .first()
                )
                if not contributor:
                    return False

                if accept:
                    contributor.accepted = True
                    contributor.updated_at = int(time.time())
                    # Ensure user_id is set
                    if not contributor.user_id:
                        user = Users.get_user_by_email(email)
                        if user:
                            contributor.user_id = user.id
                    db.commit()
                else:
                    db.delete(contributor)
                    db.commit()

                return True
        except Exception as e:
            log.exception(f"Error responding to invitation: {e}")
            return False

    def remove_contributor(
        self,
        space_id: str,
        email: str,
        db: Optional[Session] = None,
    ) -> bool:
        try:
            with get_db_context(db) as db:
                result = (
                    db.query(SpaceContributor)
                    .filter_by(space_id=space_id, email=email)
                    .delete()
                )
                db.commit()
                return result > 0
        except Exception as e:
            log.exception(f"Error removing contributor: {e}")
            return False

    def get_contributors_by_space_id(
        self,
        space_id: str,
        db: Optional[Session] = None,
    ) -> List[SpaceContributorResponse]:
        try:
            with get_db_context(db) as db:
                records = db.query(SpaceContributor).filter_by(space_id=space_id).all()
                contributors = []
                for record in records:
                    contributor_user = None
                    if record.user_id:
                        u = Users.get_user_by_id(record.user_id)
                        if u:
                            contributor_user = UserResponse(
                                **UserModel.model_validate(u).model_dump()
                            )
                    contributors.append(
                        SpaceContributorResponse(
                            id=record.id,
                            space_id=record.space_id,
                            user_id=record.user_id,
                            email=record.email,
                            permission=record.permission,
                            accepted=record.accepted,
                            user=contributor_user,
                        )
                    )
                return contributors
        except Exception as e:
            log.exception(f"Error getting contributors: {e}")
            return []

    def get_pending_invitations_for_user(
        self,
        email: str,
        db: Optional[Session] = None,
    ) -> List[SpaceContributorModel]:
        try:
            with get_db_context(db) as db:
                records = (
                    db.query(SpaceContributor)
                    .filter_by(email=email, accepted=False)
                    .all()
                )
                return [SpaceContributorModel.model_validate(r) for r in records]
        except Exception as e:
            log.exception(f"Error getting pending invitations: {e}")
            return []

    def is_contributor(
        self,
        space_id: str,
        email: str,
        db: Optional[Session] = None,
    ) -> bool:
        try:
            with get_db_context(db) as db:
                record = (
                    db.query(SpaceContributor)
                    .filter_by(space_id=space_id, email=email, accepted=True)
                    .first()
                )
                return record is not None
        except Exception:
            return False

    def get_contributor_permission(
        self,
        space_id: str,
        email: str,
        db: Optional[Session] = None,
    ) -> Optional[int]:
        try:
            with get_db_context(db) as db:
                record = (
                    db.query(SpaceContributor)
                    .filter_by(space_id=space_id, email=email)
                    .first()
                )
                return record.permission if record else None
        except Exception:
            return None

    ####################
    # File Methods
    ####################

    def add_file_to_space(
        self,
        space_id: str,
        file_id: str,
        user_id: str,
        db: Optional[Session] = None,
    ) -> Optional[SpaceFileModel]:
        with get_db_context(db) as db:
            existing = (
                db.query(SpaceFile)
                .filter_by(space_id=space_id, file_id=file_id)
                .first()
            )
            if existing:
                return SpaceFileModel.model_validate(existing)

            space_file = SpaceFile(
                id=str(uuid.uuid4()),
                space_id=space_id,
                file_id=file_id,
                user_id=user_id,
                created_at=int(time.time()),
            )

            try:
                db.add(space_file)
                db.commit()
                db.refresh(space_file)
                return SpaceFileModel.model_validate(space_file)
            except Exception as e:
                log.exception(f"Error adding file to space: {e}")
                return None

    def remove_file_from_space(
        self,
        space_id: str,
        file_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        try:
            with get_db_context(db) as db:
                result = (
                    db.query(SpaceFile)
                    .filter_by(space_id=space_id, file_id=file_id)
                    .delete()
                )
                db.commit()
                return result > 0
        except Exception as e:
            log.exception(f"Error removing file from space: {e}")
            return False

    def count_file_refs(self, file_id: str, db: Optional[Session] = None) -> int:
        """Return number of SpaceFile rows referencing file_id across all spaces.
        Returns -1 on error (caller should skip cleanup).
        """
        try:
            with get_db_context(db) as db:
                return db.query(SpaceFile).filter_by(file_id=file_id).count()
        except Exception as e:
            log.exception(f"Error counting file refs for {file_id}: {e}")
            return -1

    def get_files_by_space_id(
        self,
        space_id: str,
        db: Optional[Session] = None,
    ) -> List[FileModel]:
        try:
            with get_db_context(db) as db:
                space_file_records = (
                    db.query(SpaceFile).filter_by(space_id=space_id).all()
                )

                files = []
                for record in space_file_records:
                    file_record = (
                        db.query(FileRecord).filter_by(id=record.file_id).first()
                    )
                    if file_record:
                        files.append(FileModel.model_validate(file_record))

                return files
        except Exception as e:
            log.exception(f"Error getting files for space: {e}")
            return []

    ####################
    # Link Methods
    ####################

    def add_link_to_space(
        self,
        space_id: str,
        user_id: str,
        url: str,
        title: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[SpaceLinkModel]:
        with get_db_context(db) as db:
            space_link = SpaceLink(
                id=str(uuid.uuid4()),
                space_id=space_id,
                user_id=user_id,
                url=url,
                title=title,
                created_at=int(time.time()),
            )

            try:
                db.add(space_link)
                db.commit()
                db.refresh(space_link)
                return SpaceLinkModel.model_validate(space_link)
            except Exception as e:
                log.exception(f"Error adding link to space: {e}")
                return None

    def remove_link_from_space(
        self,
        space_id: str,
        link_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        try:
            with get_db_context(db) as db:
                result = (
                    db.query(SpaceLink)
                    .filter_by(space_id=space_id, id=link_id)
                    .delete()
                )
                db.commit()
                return result > 0
        except Exception as e:
            log.exception(f"Error removing link from space: {e}")
            return False

    def get_links_by_space_id(
        self,
        space_id: str,
        db: Optional[Session] = None,
    ) -> List[SpaceLinkModel]:
        try:
            with get_db_context(db) as db:
                records = db.query(SpaceLink).filter_by(space_id=space_id).all()
                return [SpaceLinkModel.model_validate(r) for r in records]
        except Exception as e:
            log.exception(f"Error getting links for space: {e}")
            return []

    ####################
    # Bookmark Methods
    ####################

    def add_bookmark(
        self,
        space_id: str,
        user_id: str,
        db: Optional[Session] = None,
    ) -> Optional[SpaceBookmarkModel]:
        with get_db_context(db) as db:
            existing = (
                db.query(SpaceBookmark)
                .filter_by(space_id=space_id, user_id=user_id)
                .first()
            )
            if existing:
                return SpaceBookmarkModel.model_validate(existing)

            bookmark = SpaceBookmark(
                id=str(uuid.uuid4()),
                space_id=space_id,
                user_id=user_id,
                created_at=int(time.time()),
            )

            try:
                db.add(bookmark)
                db.commit()
                db.refresh(bookmark)
                return SpaceBookmarkModel.model_validate(bookmark)
            except Exception as e:
                log.exception(f"Error adding bookmark: {e}")
                return None

    def remove_bookmark(
        self,
        space_id: str,
        user_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        try:
            with get_db_context(db) as db:
                result = (
                    db.query(SpaceBookmark)
                    .filter_by(space_id=space_id, user_id=user_id)
                    .delete()
                )
                db.commit()
                return result > 0
        except Exception as e:
            log.exception(f"Error removing bookmark: {e}")
            return False

    def get_bookmarks_by_user_id(
        self,
        user_id: str,
        db: Optional[Session] = None,
    ) -> List[SpaceModel]:
        try:
            with get_db_context(db) as db:
                bookmark_records = (
                    db.query(SpaceBookmark).filter_by(user_id=user_id).all()
                )
                spaces = []
                for record in bookmark_records:
                    space = db.query(Space).filter_by(id=record.space_id).first()
                    if space:
                        spaces.append(SpaceModel.model_validate(space))
                return spaces
        except Exception as e:
            log.exception(f"Error getting bookmarks: {e}")
            return []

    def is_bookmarked(
        self,
        space_id: str,
        user_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        try:
            with get_db_context(db) as db:
                record = (
                    db.query(SpaceBookmark)
                    .filter_by(space_id=space_id, user_id=user_id)
                    .first()
                )
                return record is not None
        except Exception:
            return False

    ####################
    # Template Methods
    ####################

    def get_templates(
        self,
        db: Optional[Session] = None,
    ) -> List[SpaceModel]:
        with get_db_context(db) as db:
            return [
                SpaceModel.model_validate(space)
                for space in db.query(Space)
                .filter_by(is_template=True)
                .order_by(Space.updated_at.desc())
                .all()
            ]

    def clone_space(
        self,
        template_id: str,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        emoji: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[SpaceModel]:
        with get_db_context(db) as db:
            template = db.query(Space).filter_by(id=template_id).first()
            if not template:
                return None

            # Create new space from template
            form_data = SpaceForm(
                name=name,
                description=description or template.description,
                emoji=emoji or template.emoji,
                instructions=template.instructions,
                model_id=template.model_id,
                enable_web_by_default=template.enable_web_by_default,
                is_template=False,
            )

            new_space = self.insert_new_space(user_id, form_data, db=db)
            if not new_space:
                return None

            # Copy files from template
            template_files = db.query(SpaceFile).filter_by(space_id=template_id).all()
            for sf in template_files:
                new_sf = SpaceFile(
                    id=str(uuid.uuid4()),
                    space_id=new_space.id,
                    file_id=sf.file_id,
                    user_id=user_id,
                    created_at=int(time.time()),
                )
                try:
                    db.add(new_sf)
                except Exception:
                    pass

            # Copy links from template
            template_links = db.query(SpaceLink).filter_by(space_id=template_id).all()
            for sl in template_links:
                new_sl = SpaceLink(
                    id=str(uuid.uuid4()),
                    space_id=new_space.id,
                    user_id=user_id,
                    url=sl.url,
                    title=sl.title,
                    created_at=int(time.time()),
                )
                try:
                    db.add(new_sl)
                except Exception:
                    pass

            try:
                db.commit()
            except Exception as e:
                log.exception(f"Error cloning space resources: {e}")

            return new_space

    ####################
    # Pin Methods
    ####################

    def pin_space(
        self,
        space_id: str,
        admin_user_id: str,
        db: Optional[Session] = None,
    ) -> Optional[SpacePinModel]:
        with get_db_context(db) as db:
            existing = db.query(SpacePin).filter_by(space_id=space_id).first()
            if existing:
                return SpacePinModel.model_validate(existing)

            pin = SpacePin(
                id=str(uuid.uuid4()),
                space_id=space_id,
                pinned_by=admin_user_id,
                created_at=int(time.time()),
            )

            try:
                db.add(pin)
                db.commit()
                db.refresh(pin)
                return SpacePinModel.model_validate(pin)
            except Exception as e:
                log.exception(f"Error pinning space: {e}")
                return None

    def unpin_space(
        self,
        space_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        try:
            with get_db_context(db) as db:
                result = db.query(SpacePin).filter_by(space_id=space_id).delete()
                db.commit()
                return result > 0
        except Exception as e:
            log.exception(f"Error unpinning space: {e}")
            return False

    def get_pinned_spaces(
        self,
        db: Optional[Session] = None,
    ) -> List[SpaceModel]:
        try:
            with get_db_context(db) as db:
                pin_records = db.query(SpacePin).all()
                spaces = []
                for record in pin_records:
                    space = db.query(Space).filter_by(id=record.space_id).first()
                    if space:
                        spaces.append(SpaceModel.model_validate(space))
                return spaces
        except Exception as e:
            log.exception(f"Error getting pinned spaces: {e}")
            return []

    def is_pinned(
        self,
        space_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        try:
            with get_db_context(db) as db:
                record = db.query(SpacePin).filter_by(space_id=space_id).first()
                return record is not None
        except Exception:
            return False

    ####################
    # Subscription Methods
    ####################

    def subscribe(
        self,
        space_id: str,
        user_id: str,
        db: Optional[Session] = None,
    ) -> Optional[SpaceSubscriptionModel]:
        with get_db_context(db) as db:
            existing = (
                db.query(SpaceSubscription)
                .filter_by(space_id=space_id, user_id=user_id)
                .first()
            )
            if existing:
                return SpaceSubscriptionModel.model_validate(existing)

            sub = SpaceSubscription(
                id=str(uuid.uuid4()),
                space_id=space_id,
                user_id=user_id,
                created_at=int(time.time()),
            )

            try:
                db.add(sub)
                db.commit()
                db.refresh(sub)
                return SpaceSubscriptionModel.model_validate(sub)
            except Exception as e:
                log.exception(f"Error subscribing to space: {e}")
                return None

    def unsubscribe(
        self,
        space_id: str,
        user_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        try:
            with get_db_context(db) as db:
                result = (
                    db.query(SpaceSubscription)
                    .filter_by(space_id=space_id, user_id=user_id)
                    .delete()
                )
                db.commit()
                return result > 0
        except Exception as e:
            log.exception(f"Error unsubscribing from space: {e}")
            return False

    def is_subscribed(
        self,
        space_id: str,
        user_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        try:
            with get_db_context(db) as db:
                record = (
                    db.query(SpaceSubscription)
                    .filter_by(space_id=space_id, user_id=user_id)
                    .first()
                )
                return record is not None
        except Exception:
            return False

    def get_subscribers(
        self,
        space_id: str,
        db: Optional[Session] = None,
    ) -> List[str]:
        """Get list of user_ids subscribed to a space."""
        try:
            with get_db_context(db) as db:
                records = db.query(SpaceSubscription).filter_by(space_id=space_id).all()
                return [r.user_id for r in records]
        except Exception as e:
            log.exception(f"Error getting subscribers: {e}")
            return []

    ####################
    # Notification Methods
    ####################

    def create_notification(
        self,
        space_id: str,
        user_id: str,
        event_type: str,
        event_data: Optional[dict] = None,
        db: Optional[Session] = None,
    ) -> Optional[SpaceNotificationModel]:
        with get_db_context(db) as db:
            notification = SpaceNotification(
                id=str(uuid.uuid4()),
                space_id=space_id,
                user_id=user_id,
                event_type=event_type,
                event_data=event_data,
                read=False,
                created_at=int(time.time()),
            )

            try:
                db.add(notification)
                db.commit()
                db.refresh(notification)
                return SpaceNotificationModel.model_validate(notification)
            except Exception as e:
                log.exception(f"Error creating notification: {e}")
                return None

    def create_notifications_for_subscribers(
        self,
        space_id: str,
        event_type: str,
        event_data: Optional[dict] = None,
        exclude_user_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> int:
        """Create notifications for all subscribers of a space, excluding the actor."""
        with get_db_context(db) as db:
            subscribers = self.get_subscribers(space_id, db=db)
            count = 0
            for sub_user_id in subscribers:
                if sub_user_id == exclude_user_id:
                    continue
                notification = SpaceNotification(
                    id=str(uuid.uuid4()),
                    space_id=space_id,
                    user_id=sub_user_id,
                    event_type=event_type,
                    event_data=event_data,
                    read=False,
                    created_at=int(time.time()),
                )
                try:
                    db.add(notification)
                    count += 1
                except Exception:
                    pass
            try:
                db.commit()
            except Exception as e:
                log.exception(f"Error creating notifications: {e}")
            return count

    def get_unread_notifications(
        self,
        user_id: str,
        db: Optional[Session] = None,
    ) -> List[SpaceNotificationModel]:
        try:
            with get_db_context(db) as db:
                records = (
                    db.query(SpaceNotification)
                    .filter_by(user_id=user_id, read=False)
                    .order_by(SpaceNotification.created_at.desc())
                    .all()
                )
                return [SpaceNotificationModel.model_validate(r) for r in records]
        except Exception as e:
            log.exception(f"Error getting unread notifications: {e}")
            return []

    def mark_notification_read(
        self,
        notification_id: str,
        user_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        try:
            with get_db_context(db) as db:
                record = (
                    db.query(SpaceNotification)
                    .filter_by(id=notification_id, user_id=user_id)
                    .first()
                )
                if not record:
                    return False
                record.read = True
                db.commit()
                return True
        except Exception as e:
            log.exception(f"Error marking notification read: {e}")
            return False

    def mark_all_notifications_read(
        self,
        user_id: str,
        db: Optional[Session] = None,
    ) -> int:
        try:
            with get_db_context(db) as db:
                result = (
                    db.query(SpaceNotification)
                    .filter_by(user_id=user_id, read=False)
                    .update({"read": True})
                )
                db.commit()
                return result
        except Exception as e:
            log.exception(f"Error marking all notifications read: {e}")
            return 0


Spaces = SpaceTable()

# Ensure all space-related tables exist (for fork additions not managed by Alembic)
try:
    Space.__table__.create(bind=engine, checkfirst=True)
    SpaceKnowledge.__table__.create(bind=engine, checkfirst=True)
    SpaceContributor.__table__.create(bind=engine, checkfirst=True)
    SpaceFile.__table__.create(bind=engine, checkfirst=True)
    SpaceLink.__table__.create(bind=engine, checkfirst=True)
    SpaceBookmark.__table__.create(bind=engine, checkfirst=True)
    SpacePin.__table__.create(bind=engine, checkfirst=True)
    SpaceSubscription.__table__.create(bind=engine, checkfirst=True)
    SpaceNotification.__table__.create(bind=engine, checkfirst=True)
    SpaceSharePointFolder.__table__.create(bind=engine, checkfirst=True)
except Exception:
    pass
