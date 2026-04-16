import time
import logging
import uuid
from typing import Optional, List
import base64
import hashlib
import json

from cryptography.fernet import Fernet

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from open_webui.internal.db import Base, get_async_db_context
from open_webui.env import OAUTH_SESSION_TOKEN_ENCRYPTION_KEY

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, Index

log = logging.getLogger(__name__)

####################
# DB MODEL
####################


class OAuthSession(Base):
    __tablename__ = 'oauth_session'

    id = Column(Text, primary_key=True, unique=True)
    user_id = Column(Text, nullable=False)
    provider = Column(Text, nullable=False)
    token = Column(Text, nullable=False)  # JSON with access_token, id_token, refresh_token
    expires_at = Column(BigInteger, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    # Add indexes for better performance
    __table_args__ = (
        Index('idx_oauth_session_user_id', 'user_id'),
        Index('idx_oauth_session_expires_at', 'expires_at'),
        Index('idx_oauth_session_user_provider', 'user_id', 'provider'),
    )


class OAuthSessionModel(BaseModel):
    id: str
    user_id: str
    provider: str
    token: dict
    expires_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class OAuthSessionResponse(BaseModel):
    id: str
    user_id: str
    provider: str
    expires_at: int


class OAuthSessionTable:
    def __init__(self):
        self.encryption_key = OAUTH_SESSION_TOKEN_ENCRYPTION_KEY
        if not self.encryption_key:
            raise Exception('OAUTH_SESSION_TOKEN_ENCRYPTION_KEY is not set')

        # check if encryption key is in the right format for Fernet (32 url-safe base64-encoded bytes)
        if len(self.encryption_key) != 44:
            key_bytes = hashlib.sha256(self.encryption_key.encode()).digest()
            self.encryption_key = base64.urlsafe_b64encode(key_bytes)
        else:
            self.encryption_key = self.encryption_key.encode()

        try:
            self.fernet = Fernet(self.encryption_key)
        except Exception as e:
            log.error(f'Error initializing Fernet with provided key: {e}')
            raise

    def _encrypt_token(self, token) -> str:
        """Encrypt OAuth tokens for storage"""
        try:
            token_json = json.dumps(token)
            encrypted = self.fernet.encrypt(token_json.encode()).decode()
            return encrypted
        except Exception as e:
            log.error(f'Error encrypting tokens: {e}')
            raise

    def _decrypt_token(self, token: str):
        """Decrypt OAuth tokens from storage"""
        try:
            decrypted = self.fernet.decrypt(token.encode()).decode()
            return json.loads(decrypted)
        except Exception as e:
            log.error(f'Error decrypting tokens: {type(e).__name__}: {e}')
            raise

    async def create_session(
        self,
        user_id: str,
        provider: str,
        token: dict,
        db: Optional[AsyncSession] = None,
    ) -> Optional[OAuthSessionModel]:
        """Create a new OAuth session"""
        try:
            async with get_async_db_context(db) as db:
                current_time = int(time.time())
                id = str(uuid.uuid4())

                result = OAuthSession(
                    **{
                        'id': id,
                        'user_id': user_id,
                        'provider': provider,
                        'token': self._encrypt_token(token),
                        'expires_at': token.get('expires_at') or int(time.time() + 3600),
                        'created_at': current_time,
                        'updated_at': current_time,
                    }
                )

                db.add(result)
                await db.commit()
                await db.refresh(result)

                if result:
                    # Make a copy of the model data before closing session
                    model = OAuthSessionModel(
                        id=result.id,
                        user_id=result.user_id,
                        provider=result.provider,
                        token=token,  # Return decrypted token
                        expires_at=result.expires_at,
                        created_at=result.created_at,
                        updated_at=result.updated_at,
                    )
                    return model
                else:
                    return None
        except Exception as e:
            log.error(f'Error creating OAuth session: {e}')
            return None

    async def get_session_by_id(
        self, session_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[OAuthSessionModel]:
        """Get OAuth session by ID"""
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(OAuthSession).filter_by(id=session_id))
                session = result.scalars().first()
                if session:
                    return OAuthSessionModel(
                        id=session.id,
                        user_id=session.user_id,
                        provider=session.provider,
                        token=self._decrypt_token(session.token),
                        expires_at=session.expires_at,
                        created_at=session.created_at,
                        updated_at=session.updated_at,
                    )

                return None
        except Exception as e:
            log.error(f'Error getting OAuth session by ID: {e}')
            return None

    async def get_session_by_id_and_user_id(
        self, session_id: str, user_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[OAuthSessionModel]:
        """Get OAuth session by ID and user ID"""
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(OAuthSession).filter_by(id=session_id, user_id=user_id))
                session = result.scalars().first()
                if session:
                    return OAuthSessionModel(
                        id=session.id,
                        user_id=session.user_id,
                        provider=session.provider,
                        token=self._decrypt_token(session.token),
                        expires_at=session.expires_at,
                        created_at=session.created_at,
                        updated_at=session.updated_at,
                    )

                return None
        except Exception as e:
            log.error(f'Error getting OAuth session by ID: {e}')
            return None

    async def get_session_by_provider_and_user_id(
        self, provider: str, user_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[OAuthSessionModel]:
        """Get OAuth session by provider and user ID"""
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(
                    select(OAuthSession)
                    .filter_by(provider=provider, user_id=user_id)
                    .order_by(OAuthSession.created_at.desc())
                )
                session = result.scalars().first()
                if session:
                    return OAuthSessionModel(
                        id=session.id,
                        user_id=session.user_id,
                        provider=session.provider,
                        token=self._decrypt_token(session.token),
                        expires_at=session.expires_at,
                        created_at=session.created_at,
                        updated_at=session.updated_at,
                    )

                return None
        except Exception as e:
            log.error(f'Error getting OAuth session by provider and user ID: {e}')
            return None

    async def get_sessions_by_user_id(self, user_id: str, db: Optional[AsyncSession] = None) -> List[OAuthSessionModel]:
        """Get all OAuth sessions for a user"""
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(OAuthSession).filter_by(user_id=user_id))
                sessions = result.scalars().all()

                results = []
                for session in sessions:
                    try:
                        results.append(
                            OAuthSessionModel(
                                id=session.id,
                                user_id=session.user_id,
                                provider=session.provider,
                                token=self._decrypt_token(session.token),
                                expires_at=session.expires_at,
                                created_at=session.created_at,
                                updated_at=session.updated_at,
                            )
                        )
                    except Exception as e:
                        log.warning(
                            f'Skipping OAuth session {session.id} due to decryption failure, deleting corrupted session: {type(e).__name__}: {e}'
                        )
                        await db.execute(delete(OAuthSession).filter_by(id=session.id))
                        await db.commit()

                return results

        except Exception as e:
            log.error(f'Error getting OAuth sessions by user ID: {e}')
            return []

    async def update_session_by_id(
        self, session_id: str, token: dict, db: Optional[AsyncSession] = None
    ) -> Optional[OAuthSessionModel]:
        """Update OAuth session tokens"""
        try:
            async with get_async_db_context(db) as db:
                current_time = int(time.time())

                await db.execute(
                    update(OAuthSession)
                    .filter_by(id=session_id)
                    .values(
                        token=self._encrypt_token(token),
                        expires_at=token.get('expires_at') or int(time.time() + 3600),
                        updated_at=current_time,
                    )
                )
                await db.commit()
                result = await db.execute(select(OAuthSession).filter_by(id=session_id))
                session = result.scalars().first()

                if session:
                    return OAuthSessionModel(
                        id=session.id,
                        user_id=session.user_id,
                        provider=session.provider,
                        token=self._decrypt_token(session.token),
                        expires_at=session.expires_at,
                        created_at=session.created_at,
                        updated_at=session.updated_at,
                    )

                return None
        except Exception as e:
            log.error(f'Error updating OAuth session tokens: {e}')
            return None

    async def delete_session_by_id(self, session_id: str, db: Optional[AsyncSession] = None) -> bool:
        """Delete an OAuth session"""
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(delete(OAuthSession).filter_by(id=session_id))
                await db.commit()
                return result.rowcount > 0
        except Exception as e:
            log.error(f'Error deleting OAuth session: {e}')
            return False

    async def delete_sessions_by_user_id(self, user_id: str, db: Optional[AsyncSession] = None) -> bool:
        """Delete all OAuth sessions for a user"""
        try:
            async with get_async_db_context(db) as db:
                await db.execute(delete(OAuthSession).filter_by(user_id=user_id))
                await db.commit()
                return True
        except Exception as e:
            log.error(f'Error deleting OAuth sessions by user ID: {e}')
            return False

    async def delete_sessions_by_provider(self, provider: str, db: Optional[AsyncSession] = None) -> bool:
        """Delete all OAuth sessions for a provider"""
        try:
            async with get_async_db_context(db) as db:
                await db.execute(delete(OAuthSession).filter_by(provider=provider))
                await db.commit()
                return True
        except Exception as e:
            log.error(f'Error deleting OAuth sessions by provider {provider}: {e}')
            return False


OAuthSessions = OAuthSessionTable()
