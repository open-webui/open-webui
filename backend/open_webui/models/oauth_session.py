import time
import logging
from typing import Optional, List

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, Index

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# DB MODEL
####################


class OAuthSession(Base):
    __tablename__ = "oauth_session"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    provider = Column(String(50), nullable=False)
    encrypted_tokens = Column(Text, nullable=False)  # JSON with access_token, id_token, refresh_token
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
    encrypted_tokens: str
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


class OAuthSessionsTable:
    def create_session(
        self,
        session_id: str,
        user_id: str,
        provider: str,
        encrypted_tokens: str,
        expires_at: int,
    ) -> Optional[OAuthSessionModel]:
        """Create a new OAuth session"""
        try:
            with get_db() as db:
                current_time = int(time.time())
                
                oauth_session = OAuthSessionModel(
                    **{
                        "id": session_id,
                        "user_id": user_id,
                        "provider": provider,
                        "encrypted_tokens": encrypted_tokens,
                        "expires_at": expires_at,
                        "created_at": current_time,
                        "updated_at": current_time,
                    }
                )
                
                result = OAuthSession(**oauth_session.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                
                if result:
                    return OAuthSessionModel.model_validate(result)
                else:
                    return None
        except Exception as e:
            log.error(f"Error creating OAuth session: {e}")
            return None

    def get_session_by_id(self, session_id: str) -> Optional[OAuthSessionModel]:
        """Get OAuth session by ID"""
        try:
            with get_db() as db:
                session = db.query(OAuthSession).filter_by(id=session_id).first()
                if session:
                    return OAuthSessionModel.model_validate(session)
                return None
        except Exception as e:
            log.error(f"Error getting OAuth session by ID: {e}")
            return None

    def get_active_session_by_user_and_provider(
        self, user_id: str, provider: str
    ) -> Optional[OAuthSessionModel]:
        """Get the most recent active OAuth session for a user and provider"""
        try:
            with get_db() as db:
                current_time = int(time.time())
                session = (
                    db.query(OAuthSession)
                    .filter_by(user_id=user_id, provider=provider)
                    .filter(OAuthSession.expires_at > current_time)
                    .order_by(OAuthSession.created_at.desc())
                    .first()
                )
                if session:
                    return OAuthSessionModel.model_validate(session)
                return None
        except Exception as e:
            log.error(f"Error getting active OAuth session: {e}")
            return None

    def get_sessions_by_user_id(self, user_id: str) -> List[OAuthSessionModel]:
        """Get all OAuth sessions for a user"""
        try:
            with get_db() as db:
                sessions = db.query(OAuthSession).filter_by(user_id=user_id).all()
                return [OAuthSessionModel.model_validate(session) for session in sessions]
        except Exception as e:
            log.error(f"Error getting OAuth sessions by user ID: {e}")
            return []

    def update_session_tokens(
        self, session_id: str, encrypted_tokens: str, expires_at: int
    ) -> Optional[OAuthSessionModel]:
        """Update OAuth session tokens"""
        try:
            with get_db() as db:
                current_time = int(time.time())
                
                db.query(OAuthSession).filter_by(id=session_id).update({
                    "encrypted_tokens": encrypted_tokens,
                    "expires_at": expires_at,
                    "updated_at": current_time,
                })
                db.commit()
                
                session = db.query(OAuthSession).filter_by(id=session_id).first()
                if session:
                    return OAuthSessionModel.model_validate(session)
                return None
        except Exception as e:
            log.error(f"Error updating OAuth session tokens: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete an OAuth session"""
        try:
            with get_db() as db:
                result = db.query(OAuthSession).filter_by(id=session_id).delete()
                db.commit()
                return result > 0
        except Exception as e:
            log.error(f"Error deleting OAuth session: {e}")
            return False

    def delete_sessions_by_user_id(self, user_id: str) -> bool:
        """Delete all OAuth sessions for a user"""
        try:
            with get_db() as db:
                result = db.query(OAuthSession).filter_by(user_id=user_id).delete()
                db.commit()
                return True
        except Exception as e:
            log.error(f"Error deleting OAuth sessions by user ID: {e}")
            return False

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired OAuth sessions"""
        try:
            with get_db() as db:
                current_time = int(time.time())
                result = db.query(OAuthSession).filter(
                    OAuthSession.expires_at <= current_time
                ).delete()
                db.commit()
                log.info(f"Cleaned up {result} expired OAuth sessions")
                return result
        except Exception as e:
            log.error(f"Error cleaning up expired OAuth sessions: {e}")
            return 0


OAuthSessions = OAuthSessionsTable()
