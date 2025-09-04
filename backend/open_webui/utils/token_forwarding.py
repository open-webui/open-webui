import logging
from typing import Optional, Dict, Any
from fastapi import Request

from open_webui.models.users import UserModel
from open_webui.utils.oauth_tokens import oauth_token_manager
from open_webui.config import (
    ENABLE_OAUTH_TOKEN_FORWARDING,
    OAUTH_TOKEN_FORWARDING_SERVICES,
)
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OAUTH"])


class TokenForwardingService:
    @staticmethod
    async def get_oauth_token_for_service(
        request: Request,
        user: UserModel,
        service: str
    ) -> Optional[str]:
        """
        Get OAuth token for specific service if forwarding is enabled
        
        Args:
            request: FastAPI request object
            user: User model
            service: Service name (openai, tools, mcp)
            
        Returns:
            OAuth token string if available, None otherwise
        """
        try:
            # Check if OAuth token forwarding is enabled
            if not ENABLE_OAUTH_TOKEN_FORWARDING.value:
                log.debug("OAuth token forwarding is disabled")
                return None
            
            # Check if the service is in the allowed list
            allowed_services = OAUTH_TOKEN_FORWARDING_SERVICES.value
            if service not in allowed_services:
                log.debug(f"Service '{service}' not in allowed services: {allowed_services}")
                return None
            
            log.debug(f"Attempting to get OAuth token for service '{service}' and user '{user.id}'")
            
            # Try server-side session first (new method)
            oauth_session_id = request.cookies.get("oauth_session_id")
            if oauth_session_id:
                # Extract provider from session ID
                # Session ID format: {user_id}_{provider}_{timestamp}_{random}
                parts = oauth_session_id.split("_")
                if len(parts) >= 2:
                    provider = parts[1]
                    
                    tokens = await oauth_token_manager.get_valid_oauth_tokens(user.id, provider)
                    if tokens:
                        token = TokenForwardingService._select_token_for_service(service, tokens)
                        if token:
                            log.debug(f"Retrieved OAuth token from server-side session for service '{service}'")
                            return token
                        else:
                            log.debug(f"No suitable token found in server-side session for service '{service}'")
                    else:
                        log.debug(f"No valid tokens found in server-side session for user '{user.id}', provider '{provider}'")
                else:
                    log.warning(f"Invalid oauth_session_id format: {oauth_session_id}")
            
            # Fallback to cookie-based approach for backward compatibility
            oauth_id_token = request.cookies.get("oauth_id_token")
            if oauth_id_token and service in ["tools", "mcp"]:
                log.debug(f"Retrieved OAuth token from cookie for service '{service}' (backward compatibility)")
                return oauth_id_token
            
            log.debug(f"No OAuth token available for service '{service}' and user '{user.id}'")
            return None
            
        except Exception as e:
            log.error(f"Error getting OAuth token for service '{service}': {e}")
            return None
    
    @staticmethod
    def _select_token_for_service(service: str, tokens: Dict[str, Any]) -> Optional[str]:
        """
        Select the appropriate token based on service requirements
        
        Args:
            service: Service name
            tokens: Dictionary of available tokens
            
        Returns:
            Selected token string or None
        """
        try:
            if service == "openai":
                # OpenAI services typically prefer access tokens for API authentication
                # but can also use ID tokens for user identification
                return tokens.get("access_token") or tokens.get("id_token")
            
            elif service == "tools":
                # Tools typically need ID tokens for user information
                # but can also use access tokens for API calls
                return tokens.get("id_token") or tokens.get("access_token")
            
            elif service == "mcp":
                # MCP (Model Context Protocol) services prefer access tokens
                # but can fall back to ID tokens
                return tokens.get("access_token") or tokens.get("id_token")
            
            else:
                log.warning(f"Unknown service '{service}', returning access_token by default")
                return tokens.get("access_token") or tokens.get("id_token")
                
        except Exception as e:
            log.error(f"Error selecting token for service '{service}': {e}")
            return None
    
    @staticmethod
    async def get_oauth_user_info(request: Request, user: UserModel) -> Optional[Dict[str, Any]]:
        """
        Get OAuth user information from tokens
        
        Args:
            request: FastAPI request object
            user: User model
            
        Returns:
            User info dictionary or None
        """
        try:
            oauth_session_id = request.cookies.get("oauth_session_id")
            if oauth_session_id:
                parts = oauth_session_id.split("_")
                if len(parts) >= 2:
                    provider = parts[1]
                    
                    tokens = await oauth_token_manager.get_valid_oauth_tokens(user.id, provider)
                    if tokens and "id_token" in tokens:
                        # Parse the ID token to get user info
                        # Note: In a full implementation, you would decode the JWT properly
                        # For now, we'll return what we can from the stored tokens
                        return {
                            "provider": provider,
                            "has_tokens": True,
                            "token_types": list(tokens.keys())
                        }
            
            return None
            
        except Exception as e:
            log.error(f"Error getting OAuth user info: {e}")
            return None
    
    @staticmethod
    async def revoke_oauth_session(request: Request, user: UserModel) -> bool:
        """
        Revoke OAuth session for a user
        
        Args:
            request: FastAPI request object
            user: User model
            
        Returns:
            True if successful, False otherwise
        """
        try:
            oauth_session_id = request.cookies.get("oauth_session_id")
            if oauth_session_id:
                parts = oauth_session_id.split("_")
                if len(parts) >= 2:
                    provider = parts[1]
                    
                    # Get the session to clean up
                    from open_webui.models.oauth_sessions import OAuthSessions
                    session = OAuthSessions.get_active_session_by_user_and_provider(user.id, provider)
                    if session:
                        # Delete the session
                        result = OAuthSessions.delete_session(session.id)
                        if result:
                            log.info(f"Revoked OAuth session for user '{user.id}', provider '{provider}'")
                            return True
                        else:
                            log.error(f"Failed to delete OAuth session for user '{user.id}', provider '{provider}'")
            
            return False
            
        except Exception as e:
            log.error(f"Error revoking OAuth session: {e}")
            return False
    
    @staticmethod
    async def cleanup_user_sessions(user_id: str) -> int:
        """
        Clean up all OAuth sessions for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            from open_webui.models.oauth_sessions import OAuthSessions
            sessions = OAuthSessions.get_sessions_by_user_id(user_id)
            count = 0
            
            for session in sessions:
                if OAuthSessions.delete_session(session.id):
                    count += 1
            
            if count > 0:
                log.info(f"Cleaned up {count} OAuth sessions for user '{user_id}'")
            
            return count
            
        except Exception as e:
            log.error(f"Error cleaning up user sessions: {e}")
            return 0


# Global instance
token_forwarding_service = TokenForwardingService()
