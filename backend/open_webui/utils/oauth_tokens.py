import os
import json
import time
import logging
import uuid
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
import aiohttp

from open_webui.models.oauth_sessions import OAuthSessions
from open_webui.config import (
    OAUTH_TOKEN_ENCRYPTION_KEY,
    OAUTH_PROVIDERS,
)
from open_webui.env import (
    SRC_LOG_LEVELS,
    AIOHTTP_CLIENT_SESSION_SSL,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OAUTH"])


class OAuthTokenManager:
    def __init__(self):
        self.encryption_key = OAUTH_TOKEN_ENCRYPTION_KEY.value
        if not self.encryption_key:
            # Generate a new key and save it
            self.encryption_key = Fernet.generate_key().decode()
            OAUTH_TOKEN_ENCRYPTION_KEY.value = self.encryption_key
            OAUTH_TOKEN_ENCRYPTION_KEY.save()
            log.info("Generated new OAuth token encryption key")
        
        try:
            self.fernet = Fernet(self.encryption_key.encode())
        except Exception as e:
            log.error(f"Invalid encryption key format: {e}")
            # Generate a new key as fallback
            self.encryption_key = Fernet.generate_key().decode()
            OAUTH_TOKEN_ENCRYPTION_KEY.value = self.encryption_key
            OAUTH_TOKEN_ENCRYPTION_KEY.save()
            self.fernet = Fernet(self.encryption_key.encode())
            log.warning("Generated new encryption key due to invalid format")
    
    def encrypt_tokens(self, tokens: Dict[str, Any]) -> str:
        """Encrypt OAuth tokens for storage"""
        try:
            token_json = json.dumps(tokens)
            encrypted = self.fernet.encrypt(token_json.encode()).decode()
            return encrypted
        except Exception as e:
            log.error(f"Error encrypting tokens: {e}")
            raise
    
    def decrypt_tokens(self, encrypted_tokens: str) -> Dict[str, Any]:
        """Decrypt OAuth tokens from storage"""
        try:
            decrypted = self.fernet.decrypt(encrypted_tokens.encode()).decode()
            return json.loads(decrypted)
        except Exception as e:
            log.error(f"Error decrypting tokens: {e}")
            raise
    
    async def store_oauth_session(
        self, user_id: str, provider: str, tokens: Dict[str, Any]
    ) -> str:
        """Store OAuth session with encrypted tokens"""
        try:
            session_id = f"{user_id}_{provider}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            encrypted_tokens = self.encrypt_tokens(tokens)
            
            # Calculate expiration from token data
            expires_in = tokens.get('expires_in', 3600)
            expires_at = int(time.time()) + expires_in
            
            # Clean up any existing sessions for this user/provider first
            existing_sessions = OAuthSessions.get_sessions_by_user_id(user_id)
            for session in existing_sessions:
                if session.provider == provider:
                    OAuthSessions.delete_session(session.id)
            
            session = OAuthSessions.create_session(
                session_id=session_id,
                user_id=user_id,
                provider=provider,
                encrypted_tokens=encrypted_tokens,
                expires_at=expires_at
            )
            
            if session:
                log.info(f"Stored OAuth session for user {user_id}, provider {provider}")
                return session_id
            else:
                raise Exception("Failed to create session in database")
                
        except Exception as e:
            log.error(f"Error storing OAuth session: {e}")
            raise
    
    async def get_valid_oauth_tokens(
        self, user_id: str, provider: str
    ) -> Optional[Dict[str, Any]]:
        """Get valid OAuth tokens, refreshing if necessary"""
        try:
            session = OAuthSessions.get_active_session_by_user_and_provider(user_id, provider)
            
            if not session:
                log.debug(f"No active OAuth session found for user {user_id}, provider {provider}")
                return None
                
            tokens = self.decrypt_tokens(session.encrypted_tokens)
            
            # Check if tokens are expired or about to expire (within 5 minutes)
            buffer_time = 300  # 5 minutes
            if session.expires_at <= (int(time.time()) + buffer_time):
                log.info(f"OAuth tokens expired or expiring soon for user {user_id}, attempting refresh")
                
                # Try to refresh
                if 'refresh_token' in tokens:
                    refreshed_tokens = await self.refresh_oauth_tokens(provider, tokens['refresh_token'])
                    if refreshed_tokens:
                        # Update session with new tokens
                        encrypted_tokens = self.encrypt_tokens(refreshed_tokens)
                        expires_at = int(time.time()) + refreshed_tokens.get('expires_in', 3600)
                        
                        updated_session = OAuthSessions.update_session_tokens(
                            session.id, 
                            encrypted_tokens, 
                            expires_at
                        )
                        
                        if updated_session:
                            log.info(f"Successfully refreshed OAuth tokens for user {user_id}")
                            return refreshed_tokens
                        else:
                            log.error(f"Failed to update session with refreshed tokens")
                
                # Tokens expired and couldn't refresh
                OAuthSessions.delete_session(session.id)
                log.warning(f"Deleted expired OAuth session for user {user_id}, provider {provider}")
                return None
            
            return tokens
            
        except Exception as e:
            log.error(f"Error getting valid OAuth tokens: {e}")
            return None
    
    async def refresh_oauth_tokens(
        self, provider: str, refresh_token: str
    ) -> Optional[Dict[str, Any]]:
        """Refresh OAuth tokens using refresh token"""
        try:
            if provider not in OAUTH_PROVIDERS:
                log.warning(f"Unknown OAuth provider for refresh: {provider}")
                return None
            
            # Get provider configuration
            provider_config = OAUTH_PROVIDERS[provider]
            
            # Provider-specific refresh logic
            if provider == "google":
                return await self._refresh_google_tokens(refresh_token)
            elif provider == "microsoft":
                return await self._refresh_microsoft_tokens(refresh_token)
            elif provider == "github":
                # GitHub tokens don't expire, so no refresh needed
                log.debug("GitHub tokens don't expire, no refresh needed")
                return None
            elif provider == "oidc":
                return await self._refresh_oidc_tokens(refresh_token)
            else:
                log.warning(f"Refresh not implemented for provider: {provider}")
                return None
                
        except Exception as e:
            log.error(f"Error refreshing OAuth tokens for provider {provider}: {e}")
            return None
    
    async def _refresh_google_tokens(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh Google OAuth tokens"""
        try:
            from open_webui.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
            
            if not GOOGLE_CLIENT_ID.value or not GOOGLE_CLIENT_SECRET.value:
                log.error("Google client credentials not configured")
                return None
            
            async with aiohttp.ClientSession(trust_env=True) as session:
                data = {
                    'client_id': GOOGLE_CLIENT_ID.value,
                    'client_secret': GOOGLE_CLIENT_SECRET.value,
                    'refresh_token': refresh_token,
                    'grant_type': 'refresh_token'
                }
                
                async with session.post(
                    'https://oauth2.googleapis.com/token',
                    data=data,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        log.debug("Successfully refreshed Google tokens")
                        return result
                    else:
                        log.error(f"Google token refresh failed: {response.status}")
                        return None
                        
        except Exception as e:
            log.error(f"Error refreshing Google tokens: {e}")
            return None
    
    async def _refresh_microsoft_tokens(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh Microsoft OAuth tokens"""
        try:
            from open_webui.config import (
                MICROSOFT_CLIENT_ID, 
                MICROSOFT_CLIENT_SECRET, 
                MICROSOFT_CLIENT_TENANT_ID,
                MICROSOFT_CLIENT_LOGIN_BASE_URL
            )
            
            if not MICROSOFT_CLIENT_ID.value or not MICROSOFT_CLIENT_SECRET.value:
                log.error("Microsoft client credentials not configured")
                return None
            
            tenant_id = MICROSOFT_CLIENT_TENANT_ID.value or "common"
            base_url = MICROSOFT_CLIENT_LOGIN_BASE_URL.value
            
            async with aiohttp.ClientSession(trust_env=True) as session:
                data = {
                    'client_id': MICROSOFT_CLIENT_ID.value,
                    'client_secret': MICROSOFT_CLIENT_SECRET.value,
                    'refresh_token': refresh_token,
                    'grant_type': 'refresh_token'
                }
                
                url = f"{base_url}/{tenant_id}/oauth2/v2.0/token"
                
                async with session.post(
                    url,
                    data=data,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        log.debug("Successfully refreshed Microsoft tokens")
                        return result
                    else:
                        log.error(f"Microsoft token refresh failed: {response.status}")
                        return None
                        
        except Exception as e:
            log.error(f"Error refreshing Microsoft tokens: {e}")
            return None
    
    async def _refresh_oidc_tokens(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh OIDC OAuth tokens"""
        try:
            from open_webui.config import (
                OAUTH_CLIENT_ID,
                OAUTH_CLIENT_SECRET,
                OPENID_PROVIDER_URL
            )
            
            if not OAUTH_CLIENT_ID.value or not OAUTH_CLIENT_SECRET.value or not OPENID_PROVIDER_URL.value:
                log.error("OIDC client credentials not configured")
                return None
            
            # Get the token endpoint from the OIDC discovery document
            async with aiohttp.ClientSession(trust_env=True) as session:
                # First get the discovery document
                discovery_url = OPENID_PROVIDER_URL.value
                if not discovery_url.endswith('/.well-known/openid-configuration'):
                    if discovery_url.endswith('/'):
                        discovery_url += '.well-known/openid-configuration'
                    else:
                        discovery_url += '/.well-known/openid-configuration'
                
                async with session.get(discovery_url, ssl=AIOHTTP_CLIENT_SESSION_SSL) as discovery_response:
                    if discovery_response.status != 200:
                        log.error(f"Failed to get OIDC discovery document: {discovery_response.status}")
                        return None
                    
                    discovery_data = await discovery_response.json()
                    token_endpoint = discovery_data.get('token_endpoint')
                    
                    if not token_endpoint:
                        log.error("No token endpoint found in OIDC discovery document")
                        return None
                    
                    # Now refresh the tokens
                    data = {
                        'client_id': OAUTH_CLIENT_ID.value,
                        'client_secret': OAUTH_CLIENT_SECRET.value,
                        'refresh_token': refresh_token,
                        'grant_type': 'refresh_token'
                    }
                    
                    async with session.post(
                        token_endpoint,
                        data=data,
                        ssl=AIOHTTP_CLIENT_SESSION_SSL
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            log.debug("Successfully refreshed OIDC tokens")
                            return result
                        else:
                            log.error(f"OIDC token refresh failed: {response.status}")
                            return None
                            
        except Exception as e:
            log.error(f"Error refreshing OIDC tokens: {e}")
            return None
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired OAuth sessions"""
        try:
            count = OAuthSessions.cleanup_expired_sessions()
            return count
        except Exception as e:
            log.error(f"Error during session cleanup: {e}")
            return 0


# Global instance
oauth_token_manager = OAuthTokenManager()
