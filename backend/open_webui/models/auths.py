import logging
import uuid
from typing import Optional

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from open_webui.internal.db import Base, JSONField, get_async_db_context
from open_webui.models.users import User, UserModel, UserProfileImageResponse, Users
from open_webui.utils.validate import validate_profile_image_url
from pydantic import BaseModel, field_validator
from sqlalchemy import Boolean, Column, String, Text

log = logging.getLogger(__name__)

####################
# DB MODEL
####################


class Auth(Base):
    __tablename__ = 'auth'

    id = Column(String, primary_key=True, unique=True)
    email = Column(String)
    password = Column(Text)
    active = Column(Boolean)


class AuthModel(BaseModel):
    id: str
    email: str
    password: str
    active: bool = True


####################
# Forms
####################


class Token(BaseModel):
    token: str
    token_type: str


class ApiKey(BaseModel):
    api_key: Optional[str] = None


class SigninResponse(Token, UserProfileImageResponse):
    pass


class SigninForm(BaseModel):
    email: str
    password: str


class LdapForm(BaseModel):
    user: str
    password: str


class ProfileImageUrlForm(BaseModel):
    profile_image_url: str


class UpdatePasswordForm(BaseModel):
    password: str
    new_password: str


class SignupForm(BaseModel):
    name: str
    email: str
    password: str
    profile_image_url: Optional[str] = '/user.png'

    @field_validator('profile_image_url')
    @classmethod
    def check_profile_image_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_profile_image_url(v)
        return v


class AddUserForm(SignupForm):
    role: Optional[str] = 'pending'


class AuthsTable:
    async def insert_new_auth(
        self,
        email: str,
        password: str,
        name: str,
        profile_image_url: str = '/user.png',
        role: str = 'pending',
        oauth: Optional[dict] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[UserModel]:
        async with get_async_db_context(db) as db:
            log.info('insert_new_auth')

            id = str(uuid.uuid4())

            auth = AuthModel(**{'id': id, 'email': email, 'password': password, 'active': True})
            result = Auth(**auth.model_dump())
            db.add(result)

            user = await Users.insert_new_user(id, name, email, profile_image_url, role, oauth=oauth, db=db)

            await db.commit()
            await db.refresh(result)

            if result and user:
                return user
            else:
                return None

    async def authenticate_user(
        self, email: str, verify_password: callable, db: Optional[AsyncSession] = None
    ) -> Optional[UserModel]:
        log.info(f'authenticate_user: {email}')

        user = await Users.get_user_by_email(email, db=db)
        if not user:
            return None

        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Auth).filter_by(id=user.id, active=True))
                auth = result.scalars().first()
                if auth:
                    if verify_password(auth.password):
                        return user
                    else:
                        return None
                else:
                    return None
        except Exception:
            return None

    async def authenticate_user_by_api_key(
        self, api_key: str, db: Optional[AsyncSession] = None
    ) -> Optional[UserModel]:
        log.info(f'authenticate_user_by_api_key')
        # if no api_key, return None
        if not api_key:
            return None

        try:
            user = await Users.get_user_by_api_key(api_key, db=db)
            return user if user else None
        except Exception:
            return False

    async def authenticate_user_by_email(self, email: str, db: Optional[AsyncSession] = None) -> Optional[UserModel]:
        log.info(f'authenticate_user_by_email: {email}')
        try:
            async with get_async_db_context(db) as db:
                # Single JOIN query instead of two separate queries
                result = await db.execute(
                    select(Auth, User).join(User, Auth.id == User.id).filter(Auth.email == email, Auth.active == True)
                )
                row = result.first()
                if row:
                    _, user = row
                    return UserModel.model_validate(user)
                return None
        except Exception:
            return None

    async def update_user_password_by_id(self, id: str, new_password: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(update(Auth).filter_by(id=id).values(password=new_password))
                await db.commit()
                return True if result.rowcount == 1 else False
        except Exception:
            return False

    async def update_email_by_id(self, id: str, email: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(update(Auth).filter_by(id=id).values(email=email))
                await db.commit()
                if result.rowcount == 1:
                    await Users.update_user_by_id(id, {'email': email}, db=db)
                    return True
                return False
        except Exception:
            return False

    async def delete_auth_by_id(self, id: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                # Delete User
                result = await Users.delete_user_by_id(id, db=db)

                if result:
                    await db.execute(delete(Auth).filter_by(id=id))
                    await db.commit()

                    return True
                else:
                    return False
        except Exception:
            return False


Auths = AuthsTable()
