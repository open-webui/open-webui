import logging
import time
import uuid
from typing import Optional, List

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, ForeignKey

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# API Key DB Schema
####################


class ApiKey(Base):
    __tablename__ = "api_key"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user.id"), nullable=False)
    api_key = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)  # Optional name for the key
    
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)
    last_used_at = Column(BigInteger, nullable=True)


####################
# Pydantic Models
####################


class ApiKeyModel(BaseModel):
    id: str
    user_id: str
    api_key: str
    name: Optional[str] = None
    
    created_at: int
    updated_at: int
    last_used_at: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ApiKeyResponse(BaseModel):
    id: str
    name: Optional[str] = None
    api_key: str
    created_at: int
    last_used_at: Optional[int] = None
    expires_at: Optional[int] = None
    is_expired: bool = False


class ApiKeyCreateResponse(BaseModel):
    id: str
    api_key: str
    name: Optional[str] = None
    created_at: int


####################
# API Keys Table
####################


class ApiKeysTable:
    def create_api_key(
        self, user_id: str, api_key: str, name: Optional[str] = None
    ) -> Optional[ApiKeyModel]:
        try:
            with get_db() as db:
                id = str(uuid.uuid4())
                current_time = int(time.time())
                
                new_api_key = ApiKey(
                    id=id,
                    user_id=user_id,
                    api_key=api_key,
                    name=name,
                    created_at=current_time,
                    updated_at=current_time,
                )
                
                db.add(new_api_key)
                db.commit()
                db.refresh(new_api_key)
                
                return ApiKeyModel.model_validate(new_api_key)
        except Exception as e:
            log.error(f"Error creating API key: {e}")
            return None

    def get_api_keys_by_user_id(self, user_id: str) -> List[ApiKeyModel]:
        try:
            with get_db() as db:
                api_keys = db.query(ApiKey).filter_by(user_id=user_id).all()
                return [ApiKeyModel.model_validate(key) for key in api_keys]
        except Exception as e:
            log.error(f"Error getting API keys for user {user_id}: {e}")
            return []

    def get_api_key_by_key(self, api_key: str) -> Optional[ApiKeyModel]:
        try:
            with get_db() as db:
                key = db.query(ApiKey).filter_by(api_key=api_key).first()
                return ApiKeyModel.model_validate(key) if key else None
        except Exception as e:
            log.error(f"Error getting API key: {e}")
            return None

    def get_api_key_by_id(self, id: str) -> Optional[ApiKeyModel]:
        try:
            with get_db() as db:
                key = db.query(ApiKey).filter_by(id=id).first()
                return ApiKeyModel.model_validate(key) if key else None
        except Exception as e:
            log.error(f"Error getting API key by id: {e}")
            return None

    def update_api_key_last_used(self, api_key: str) -> bool:
        try:
            with get_db() as db:
                current_time = int(time.time())
                result = db.query(ApiKey).filter_by(api_key=api_key).update({
                    "last_used_at": current_time,
                    "updated_at": current_time,
                })
                db.commit()
                return result == 1
        except Exception as e:
            log.error(f"Error updating API key last used: {e}")
            return False

    def delete_api_key_by_id(self, id: str, user_id: str) -> bool:
        try:
            with get_db() as db:
                result = db.query(ApiKey).filter_by(id=id, user_id=user_id).delete()
                db.commit()
                return result == 1
        except Exception as e:
            log.error(f"Error deleting API key: {e}")
            return False

    def delete_all_api_keys_by_user_id(self, user_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(ApiKey).filter_by(user_id=user_id).delete()
                db.commit()
                return True
        except Exception as e:
            log.error(f"Error deleting all API keys for user {user_id}: {e}")
            return False

    def is_api_key_expired(self, api_key_model: ApiKeyModel, expiry: int) -> bool:
        """Check if an API key has expired based on expiry time"""
        if expiry <= 0:  # No expiration if expiry is 0 or negative
            return False
        
        current_time = int(time.time())
        expiration_time = api_key_model.created_at + expiry
        return current_time > expiration_time

    def get_expiration_timestamp(self, api_key_model: ApiKeyModel, expiry: int) -> Optional[int]:
        """Get the expiration timestamp for an API key"""
        if expiry <= 0:  # No expiration if expiry is 0 or negative
            return None
        return api_key_model.created_at + expiry

    def cleanup_expired_api_keys(self, expiry: int) -> int:
        """Remove all expired API keys and return the count of deleted keys"""
        if expiry <= 0:  # No cleanup if expiry is disabled
            return 0
            
        try:
            with get_db() as db:
                current_time = int(time.time())
                cutoff_time = current_time - expiry
                
                # Delete all keys created before the cutoff time
                result = db.query(ApiKey).filter(ApiKey.created_at < cutoff_time).delete()
                db.commit()
                
                if result > 0:
                    log.info(f"Cleaned up {result} expired API keys")
                
                return result
        except Exception as e:
            log.error(f"Error cleaning up expired API keys: {e}")
            return 0

    def get_active_api_keys_by_user_id(self, user_id: str, expiry: int) -> List[ApiKeyModel]:
        """Get only non-expired API keys for a user"""
        all_keys = self.get_api_keys_by_user_id(user_id)
        if expiry <= 0:  # No expiration check if expiry is disabled
            return all_keys
        
        return [key for key in all_keys if not self.is_api_key_expired(key, expiry)]


ApiKeys = ApiKeysTable() 