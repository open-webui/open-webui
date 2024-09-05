import logging
import time
import uuid
from typing import Optional

from open_webui.apps.webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Tag DB Schema
####################


class Tag(Base):
    __tablename__ = "tag"

    id = Column(String, primary_key=True)
    name = Column(String)
    user_id = Column(String)
    data = Column(Text, nullable=True)


class ChatIdTag(Base):
    __tablename__ = "chatidtag"

    id = Column(String, primary_key=True)
    tag_name = Column(String)
    chat_id = Column(String)
    user_id = Column(String)
    timestamp = Column(BigInteger)


class TagModel(BaseModel):
    id: str
    name: str
    user_id: str
    data: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ChatIdTagModel(BaseModel):
    id: str
    tag_name: str
    chat_id: str
    user_id: str
    timestamp: int

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class ChatIdTagForm(BaseModel):
    tag_name: str
    chat_id: str


class TagChatIdsResponse(BaseModel):
    chat_ids: list[str]


class ChatTagsResponse(BaseModel):
    tags: list[str]


class TagTable:
    def insert_new_tag(self, name: str, user_id: str) -> Optional[TagModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            tag = TagModel(**{"id": id, "user_id": user_id, "name": name})
            try:
                result = Tag(**tag.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return TagModel.model_validate(result)
                else:
                    return None
            except Exception:
                return None

    def get_tag_by_name_and_user_id(
        self, name: str, user_id: str
    ) -> Optional[TagModel]:
        try:
            with get_db() as db:
                tag = db.query(Tag).filter_by(name=name, user_id=user_id).first()
                return TagModel.model_validate(tag)
        except Exception:
            return None

    def add_tag_to_chat(
        self, user_id: str, form_data: ChatIdTagForm
    ) -> Optional[ChatIdTagModel]:
        tag = self.get_tag_by_name_and_user_id(form_data.tag_name, user_id)
        if tag is None:
            tag = self.insert_new_tag(form_data.tag_name, user_id)

        id = str(uuid.uuid4())
        chatIdTag = ChatIdTagModel(
            **{
                "id": id,
                "user_id": user_id,
                "chat_id": form_data.chat_id,
                "tag_name": tag.name,
                "timestamp": int(time.time()),
            }
        )
        try:
            with get_db() as db:
                result = ChatIdTag(**chatIdTag.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return ChatIdTagModel.model_validate(result)
                else:
                    return None
        except Exception:
            return None

    def get_tags_by_user_id(self, user_id: str) -> list[TagModel]:
        with get_db() as db:
            tag_names = [
                chat_id_tag.tag_name
                for chat_id_tag in (
                    db.query(ChatIdTag)
                    .filter_by(user_id=user_id)
                    .order_by(ChatIdTag.timestamp.desc())
                    .all()
                )
            ]

            return [
                TagModel.model_validate(tag)
                for tag in (
                    db.query(Tag)
                    .filter_by(user_id=user_id)
                    .filter(Tag.name.in_(tag_names))
                    .all()
                )
            ]

    def get_tags_by_chat_id_and_user_id(
        self, chat_id: str, user_id: str
    ) -> list[TagModel]:
        with get_db() as db:
            tag_names = [
                chat_id_tag.tag_name
                for chat_id_tag in (
                    db.query(ChatIdTag)
                    .filter_by(user_id=user_id, chat_id=chat_id)
                    .order_by(ChatIdTag.timestamp.desc())
                    .all()
                )
            ]

            return [
                TagModel.model_validate(tag)
                for tag in (
                    db.query(Tag)
                    .filter_by(user_id=user_id)
                    .filter(Tag.name.in_(tag_names))
                    .all()
                )
            ]

    def get_chat_ids_by_tag_name_and_user_id(
        self, tag_name: str, user_id: str
    ) -> list[ChatIdTagModel]:
        with get_db() as db:
            return [
                ChatIdTagModel.model_validate(chat_id_tag)
                for chat_id_tag in (
                    db.query(ChatIdTag)
                    .filter_by(user_id=user_id, tag_name=tag_name)
                    .order_by(ChatIdTag.timestamp.desc())
                    .all()
                )
            ]

    def count_chat_ids_by_tag_name_and_user_id(
        self, tag_name: str, user_id: str
    ) -> int:
        with get_db() as db:
            return (
                db.query(ChatIdTag)
                .filter_by(tag_name=tag_name, user_id=user_id)
                .count()
            )

    def delete_tag_by_tag_name_and_user_id(self, tag_name: str, user_id: str) -> bool:
        try:
            with get_db() as db:
                res = (
                    db.query(ChatIdTag)
                    .filter_by(tag_name=tag_name, user_id=user_id)
                    .delete()
                )
                log.debug(f"res: {res}")
                db.commit()

                tag_count = self.count_chat_ids_by_tag_name_and_user_id(
                    tag_name, user_id
                )
                if tag_count == 0:
                    # Remove tag item from Tag col as well
                    db.query(Tag).filter_by(name=tag_name, user_id=user_id).delete()
                    db.commit()
                return True
        except Exception as e:
            log.error(f"delete_tag: {e}")
            return False

    def delete_tag_by_tag_name_and_chat_id_and_user_id(
        self, tag_name: str, chat_id: str, user_id: str
    ) -> bool:
        try:
            with get_db() as db:
                res = (
                    db.query(ChatIdTag)
                    .filter_by(tag_name=tag_name, chat_id=chat_id, user_id=user_id)
                    .delete()
                )
                log.debug(f"res: {res}")
                db.commit()

                tag_count = self.count_chat_ids_by_tag_name_and_user_id(
                    tag_name, user_id
                )
                if tag_count == 0:
                    # Remove tag item from Tag col as well
                    db.query(Tag).filter_by(name=tag_name, user_id=user_id).delete()
                    db.commit()

                return True
        except Exception as e:
            log.error(f"delete_tag: {e}")
            return False

    def delete_tags_by_chat_id_and_user_id(self, chat_id: str, user_id: str) -> bool:
        tags = self.get_tags_by_chat_id_and_user_id(chat_id, user_id)

        for tag in tags:
            self.delete_tag_by_tag_name_and_chat_id_and_user_id(
                tag.tag_name, chat_id, user_id
            )

        return True


Tags = TagTable()
