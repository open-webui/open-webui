import json
import logging
import time
from typing import Optional
import uuid

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from open_webui.models.files import FileMetadataResponse
from open_webui.models.users import Users, UserResponse


from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON

from open_webui.utils.access_control import has_access

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Characters DB Schema
####################


class Character(Base):  # SQLAlchemy Model (inherits from declarative base)
    __tablename__ = "character"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)

    title = Column(Text)
    system_prompt = Column(Text)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class CharacterModel(BaseModel): # Pydantic Model
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    title: str
    system_prompt: str

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class CharacterUserModel(CharacterModel):
    user: Optional[UserResponse] = None


class CharacterResponse(CharacterModel):
    pass


class CharacterUserResponse(CharacterUserModel):
    pass

class CharacterForm(BaseModel):
    title: str
    system_prompt: str


class CharacterTable:
    def insert_new_character(
        self, user_id: str, title: str, system_prompt: str,
    ) -> Optional[CharacterModel]:
        with get_db() as db:
            character = CharacterModel(
                **{
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "title": title,
                    "system_prompt": system_prompt,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            try:
                result = Character(**character.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                
                if result:
                    return CharacterModel.model_validate(result)
                else:
                    print('!!NONE')
                    return None
            except Exception as e:
                print('!!ERROR', e)
                return None

    def get_characters(self) -> list[CharacterUserModel]:
        with get_db() as db:
            characters = []
            for character in (
                db.query(Character).order_by(Character.updated_at.desc()).all()
            ):
                user = Users.get_user_by_id(character.user_id)
                characters.append(
                    CharacterUserModel.model_validate(
                        {
                            **CharacterModel.model_validate(character).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )
            return characters

    def get_characters_by_user_id(
        self, user_id: str, permission: str = "write"
    ) -> list[CharacterUserModel]:
        characters = self.get_characters()
        return [
            characters
            for character in characters
            if character.user_id == user_id
            or has_access(user_id, permission, character.access_control)
        ]

    def get_character_by_id(self, id: str) -> Optional[CharacterModel]:
        try:
            with get_db() as db:
                character = db.query(Character).filter_by(id=id).first()
                return CharacterModel.model_validate(character) if character else None
        except Exception:
            return None

    def update_character_by_id(
        self, id: str, form_data: CharacterForm, overwrite: bool = False
    ) -> Optional[CharacterModel]:
        try:
            with get_db() as db:
                db.query(Character).filter_by(id=id).update(
                    {
                        **form_data.model_dump(),
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()
                return self.get_character_by_id(id=id)
        except Exception as e:
            log.exception(e)
            return None

    def delete_character_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Character).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception:
            return False

Characters = CharacterTable()
