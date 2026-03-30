import logging
import uuid

from open_webui.internal.db import Base, get_db_context
from open_webui.models.users import User, UserModel, UserProfileImageResponse, Users
from open_webui.utils.validate import validate_profile_image_url
from pydantic import BaseModel, field_validator
from sqlalchemy import Boolean, Column, String, Text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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
    api_key: str | None = None


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
    profile_image_url: str | None = '/user.png'

    @field_validator('profile_image_url')
    @classmethod
    def check_profile_image_url(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_profile_image_url(v)
        return v


class AddUserForm(SignupForm):
    role: str | None = 'pending'


class AuthsTable:
    def insert_new_auth(
        self,
        email: str,
        password: str,
        name: str,
        profile_image_url: str = '/user.png',
        role: str = 'pending',
        oauth: dict | None = None,
        db: Session | None = None,
        id: str | None = None,
    ) -> UserModel | None:
        with get_db_context(db) as db:
            log.info('insert_new_auth')

            if id is None:
                id = str(uuid.uuid4())

            try:
                auth = AuthModel(**{'id': id, 'email': email, 'password': password, 'active': True})
                result = Auth(**auth.model_dump())
                db.add(result)

                user = Users.insert_new_user(id, name, email, profile_image_url, role, oauth=oauth, db=db)

                db.commit()
                db.refresh(result)

                if result and user:
                    return user
                else:
                    return None
            except IntegrityError as e:
                db.rollback()
                # Handle case where auth ID already exists (e.g., user deleted from UI
                # but auth record remained, common with stable AD SID-based IDs)
                if 'UNIQUE constraint failed' in str(e) or 'duplicate key' in str(e).lower():
                    log.info(f'Auth ID {id} already exists, reactivating and updating existing records')
                    try:
                        existing_auth = db.query(Auth).filter_by(id=id).first()
                        if existing_auth:
                            existing_auth.email = email
                            existing_auth.password = password
                            existing_auth.active = True
                        else:
                            new_auth = Auth(
                                **AuthModel(id=id, email=email, password=password, active=True).model_dump()
                            )
                            db.add(new_auth)
                        db.commit()

                        user = Users.get_user_by_id(id, db=db)
                        if not user:
                            user = Users.insert_new_user(id, name, email, profile_image_url, role, oauth=oauth, db=db)
                        else:
                            Users.update_user_by_id(
                                id,
                                {'email': email, 'name': name, 'profile_image_url': profile_image_url},
                                db=db,
                            )

                        return user
                    except Exception as recovery_err:
                        log.error(f'Failed to recover from duplicate auth ID: {str(recovery_err)}')
                        return None
                else:
                    log.error(f'Failed to insert auth: {str(e)}')
                    return None

    def authenticate_user(self, email: str, verify_password: callable, db: Session | None = None) -> UserModel | None:
        log.info(f'authenticate_user: {email}')

        user = Users.get_user_by_email(email, db=db)
        if not user:
            return None

        try:
            with get_db_context(db) as db:
                auth = db.query(Auth).filter_by(id=user.id, active=True).first()
                if auth:
                    if verify_password(auth.password):
                        return user
                    else:
                        return None
                else:
                    return None
        except Exception:
            return None

    def authenticate_user_by_api_key(self, api_key: str, db: Session | None = None) -> UserModel | None:
        log.info('authenticate_user_by_api_key')
        # if no api_key, return None
        if not api_key:
            return None

        try:
            user = Users.get_user_by_api_key(api_key, db=db)
            return user if user else None
        except Exception:
            return False

    def authenticate_user_by_email(self, email: str, db: Session | None = None) -> UserModel | None:
        log.info(f'authenticate_user_by_email: {email}')
        try:
            with get_db_context(db) as db:
                # Single JOIN query instead of two separate queries
                result = (
                    db.query(Auth, User)
                    .join(User, Auth.id == User.id)
                    .filter(Auth.email == email, Auth.active == True)
                    .first()
                )
                if result:
                    _, user = result
                    return UserModel.model_validate(user)
                return None
        except Exception:
            return None

    def update_user_password_by_id(self, id: str, new_password: str, db: Session | None = None) -> bool:
        try:
            with get_db_context(db) as db:
                result = db.query(Auth).filter_by(id=id).update({'password': new_password})
                db.commit()
                return True if result == 1 else False
        except Exception:
            return False

    def update_email_by_id(self, id: str, email: str, db: Session | None = None) -> bool:
        try:
            with get_db_context(db) as db:
                result = db.query(Auth).filter_by(id=id).update({'email': email})
                db.commit()
                if result == 1:
                    Users.update_user_by_id(id, {'email': email}, db=db)
                    return True
                return False
        except Exception:
            return False

    def delete_auth_by_id(self, id: str, db: Session | None = None) -> bool:
        try:
            with get_db_context(db) as db:
                # Delete User
                result = Users.delete_user_by_id(id, db=db)

                if result:
                    db.query(Auth).filter_by(id=id).delete()
                    db.commit()

                    return True
                else:
                    return False
        except Exception:
            return False


Auths = AuthsTable()
