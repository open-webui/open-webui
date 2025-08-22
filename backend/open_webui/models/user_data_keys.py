from typing import Optional

from open_webui.internal.db import Base, get_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, String, Text

####################
# UserDataKey DB Schema
####################


class UserDataKey(Base):
    __tablename__ = "user_data_key"

    user_id = Column(String, primary_key=True)
    encrypted_data_key = Column(Text, nullable=False)


class UserDataKeyModel(BaseModel):
    user_id: str
    encrypted_data_key: str

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class UserDataKeyResponse(BaseModel):
    user_id: str
    encrypted_data_key: str


class UserDataKeyCreateForm(BaseModel):
    user_id: str
    encrypted_data_key: str


class UserDataKeyUpdateForm(BaseModel):
    encrypted_data_key: str


class UserDataKeysTable:
    def create_user_data_key(
        self, user_id: str, encrypted_data_key: str
    ) -> Optional[UserDataKeyModel]:
        try:
            with get_db() as db:
                user_data_key = UserDataKey(
                    user_id=user_id, encrypted_data_key=encrypted_data_key
                )
                db.add(user_data_key)
                db.commit()
                db.refresh(user_data_key)
                return UserDataKeyModel.model_validate(user_data_key)
        except Exception:
            return None

    def get_user_data_key_by_user_id(self, user_id: str) -> Optional[UserDataKeyModel]:
        try:
            with get_db() as db:
                user_data_key = db.query(UserDataKey).filter_by(user_id=user_id).first()
                if user_data_key:
                    return UserDataKeyModel.model_validate(user_data_key)
                return None
        except Exception:
            return None

    def update_user_data_key_by_user_id(
        self, user_id: str, encrypted_data_key: str
    ) -> Optional[UserDataKeyModel]:
        try:
            with get_db() as db:
                db.query(UserDataKey).filter_by(user_id=user_id).update(
                    {"encrypted_data_key": encrypted_data_key}
                )
                db.commit()
                user_data_key = db.query(UserDataKey).filter_by(user_id=user_id).first()
                return UserDataKeyModel.model_validate(user_data_key)
        except Exception:
            return None

    def delete_user_data_key_by_user_id(self, user_id: str) -> bool:
        try:
            with get_db() as db:
                result = db.query(UserDataKey).filter_by(user_id=user_id).delete()
                db.commit()
                return result > 0
        except Exception:
            return False


UserDataKeys = UserDataKeysTable()
