from pydantic import BaseModel, ConfigDict
from peewee import *
from playhouse.shortcuts import model_to_dict
from typing import List, Union, Optional
import time
from utils.misc import get_gravatar_url

from apps.webui.internal.db import DB, JSONField
from apps.webui.models.chats import Chats

####################
# User DB Schema
####################


class User(Model):
    id = CharField(unique=True)
    name = CharField()
    email = CharField()
    role = CharField()
    profile_image_url = TextField()

    last_active_at = BigIntegerField()
    updated_at = BigIntegerField()
    created_at = BigIntegerField()

    api_key = CharField(null=True, unique=True)
    settings = JSONField(null=True)

    class Meta:
        database = DB


class UserSettings(BaseModel):
    ui: Optional[dict] = {}
    model_config = ConfigDict(extra="allow")
    pass


class UserModel(BaseModel):
    id: str
    name: str
    email: str
    role: str = "pending"
    profile_image_url: str

    last_active_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    api_key: Optional[str] = None
    settings: Optional[UserSettings] = None


####################
# Forms
####################


class UserRoleUpdateForm(BaseModel):
    id: str
    role: str


class UserUpdateForm(BaseModel):
    name: str
    email: str
    profile_image_url: str
    password: Optional[str] = None


class UsersTable:
    def __init__(self, db):
        self.db = db
        self.db.create_tables([User])

    def insert_new_user(
        self,
        id: str,
        name: str,
        email: str,
        profile_image_url: str = "/user.png",
        role: str = "pending",
    ) -> Optional[UserModel]:
        user = UserModel(
            **{
                "id": id,
                "name": name,
                "email": email,
                "role": role,
                "profile_image_url": profile_image_url,
                "last_active_at": int(time.time()),
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            }
        )
        result = User.create(**user.model_dump())
        if result:
            return user
        else:
            return None

    def get_user_by_id(self, id: str) -> Optional[UserModel]:
        try:
            user = User.get(User.id == id)
            return UserModel(**model_to_dict(user))
        except:
            return None

    def get_user_by_api_key(self, api_key: str) -> Optional[UserModel]:
        try:
            user = User.get(User.api_key == api_key)
            return UserModel(**model_to_dict(user))
        except:
            return None

    def get_user_by_email(self, email: str) -> Optional[UserModel]:
        try:
            user = User.get(User.email == email)
            return UserModel(**model_to_dict(user))
        except:
            return None

    def get_users(self, skip: int = 0, limit: int = 50) -> List[UserModel]:
        return [
            UserModel(**model_to_dict(user))
            for user in User.select()
            # .limit(limit).offset(skip)
        ]

    def get_num_users(self) -> Optional[int]:
        return User.select().count()

    def get_first_user(self) -> UserModel:
        try:
            user = User.select().order_by(User.created_at).first()
            return UserModel(**model_to_dict(user))
        except:
            return None

    def update_user_role_by_id(self, id: str, role: str) -> Optional[UserModel]:
        try:
            query = User.update(role=role).where(User.id == id)
            query.execute()

            user = User.get(User.id == id)
            return UserModel(**model_to_dict(user))
        except:
            return None

    def update_user_profile_image_url_by_id(
        self, id: str, profile_image_url: str
    ) -> Optional[UserModel]:
        try:
            query = User.update(profile_image_url=profile_image_url).where(
                User.id == id
            )
            query.execute()

            user = User.get(User.id == id)
            return UserModel(**model_to_dict(user))
        except:
            return None

    def update_user_last_active_by_id(self, id: str) -> Optional[UserModel]:
        try:
            query = User.update(last_active_at=int(time.time())).where(User.id == id)
            query.execute()

            user = User.get(User.id == id)
            return UserModel(**model_to_dict(user))
        except:
            return None

    def update_user_by_id(self, id: str, updated: dict) -> Optional[UserModel]:
        try:
            query = User.update(**updated).where(User.id == id)
            query.execute()

            user = User.get(User.id == id)
            return UserModel(**model_to_dict(user))
        except:
            return None

    def delete_user_by_id(self, id: str) -> bool:
        try:
            # Delete User Chats
            result = Chats.delete_chats_by_user_id(id)

            if result:
                # Delete User
                query = User.delete().where(User.id == id)
                query.execute()  # Remove the rows, return number of rows removed.

                return True
            else:
                return False
        except:
            return False

    def update_user_api_key_by_id(self, id: str, api_key: str) -> str:
        try:
            query = User.update(api_key=api_key).where(User.id == id)
            result = query.execute()

            return True if result == 1 else False
        except:
            return False

    def get_user_api_key_by_id(self, id: str) -> Optional[str]:
        try:
            user = User.get(User.id == id)
            return user.api_key
        except:
            return None


Users = UsersTable(DB)
