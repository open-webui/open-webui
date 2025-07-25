"""
Production-ready user mapping utilities for mAI OpenRouter integration.
Provides secure, consistent user ID mapping between mAI and OpenRouter systems.
"""

import hashlib
import logging
import re
from typing import Optional, Dict, Tuple
from uuid import UUID

from open_webui.config import ORGANIZATION_NAME, OPENROUTER_EXTERNAL_USER

logger = logging.getLogger(__name__)

class UserMappingService:
    """
    Production service for mapping mAI users to OpenRouter external_user IDs.
    
    Features:
    - Unique per-user external IDs
    - Organization-scoped isolation
    - Backward compatibility
    - Security through ID hashing
    - Validation and error handling
    """
    
    def __init__(self):
        self.client_prefix = self._get_client_prefix()
        self.organization_name = ORGANIZATION_NAME or "default_org"
        
    def _get_client_prefix(self) -> str:
        """
        Get the client prefix from environment configuration.
        
        Returns:
            str: Client prefix for external user IDs
        """
        if OPENROUTER_EXTERNAL_USER:
            # Extract prefix from existing external user format
            # e.g., "mai_client_63a4eb6d" -> "mai_client_63a4eb6d"
            return OPENROUTER_EXTERNAL_USER
        
        # Fallback: generate from organization name
        if ORGANIZATION_NAME:
            # Create safe client prefix from organization name
            safe_name = re.sub(r'[^a-zA-Z0-9]', '_', ORGANIZATION_NAME.lower())
            return f"mai_client_{safe_name[:16]}"
        
        return "mai_client_default"
    
    def _validate_user_id(self, user_id: str) -> bool:
        """
        Validate that user_id is a proper UUID format.
        
        Args:
            user_id: User ID to validate
            
        Returns:
            bool: True if valid UUID format
        """
        try:
            UUID(user_id)
            return True
        except (ValueError, TypeError):
            logger.warning(f"Invalid user ID format: {user_id}")
            return False
    
    def _hash_user_id(self, user_id: str) -> str:
        """
        Create a consistent hash of the user ID for privacy.
        
        Args:
            user_id: Full user UUID
            
        Returns:
            str: 8-character hash of the user ID
        """
        # Use SHA-256 for consistent, secure hashing
        hash_obj = hashlib.sha256(user_id.encode('utf-8'))
        return hash_obj.hexdigest()[:8]
    
    def generate_external_user_id(self, user_id: str, user_name: Optional[str] = None) -> str:
        """
        Generate OpenRouter external_user ID for a specific mAI user.
        
        Format: {client_prefix}_user_{hashed_user_id}
        Example: mai_client_63a4eb6d_user_a1b2c3d4
        
        Args:
            user_id: mAI user UUID
            user_name: Optional user name for logging
            
        Returns:
            str: OpenRouter external_user ID
            
        Raises:
            ValueError: If user_id is invalid
        """
        if not user_id:
            raise ValueError("User ID cannot be empty")
        
        if not self._validate_user_id(user_id):
            raise ValueError(f"Invalid user ID format: {user_id}")
        
        # Create hashed user identifier for privacy
        user_hash = self._hash_user_id(user_id)
        
        # Generate external user ID
        external_user_id = f"{self.client_prefix}_user_{user_hash}"
        
        # Log for monitoring (without exposing full user ID)
        logger.info(
            f"Generated external_user_id for user {user_name or 'unknown'}: "
            f"{external_user_id} (org: {self.organization_name})"
        )
        
        return external_user_id
    
    def parse_external_user_id(self, external_user_id: str) -> Optional[Dict[str, str]]:
        """
        Parse an external_user_id back to its components.
        
        Args:
            external_user_id: OpenRouter external user ID
            
        Returns:
            dict: Parsed components or None if invalid format
        """
        try:
            # Pattern: mai_client_63a4eb6d_user_a1b2c3d4
            pattern = r'^(.+)_user_([a-f0-9]{8})$'
            match = re.match(pattern, external_user_id)
            
            if match:
                client_prefix, user_hash = match.groups()
                return {
                    'client_prefix': client_prefix,
                    'user_hash': user_hash,
                    'is_user_specific': True
                }
            
            # Check if it's a legacy organization-only ID
            if external_user_id.startswith('mai_client_'):
                return {
                    'client_prefix': external_user_id,
                    'user_hash': None,
                    'is_user_specific': False
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to parse external_user_id {external_user_id}: {e}")
            return None
    
    def is_user_specific_id(self, external_user_id: str) -> bool:
        """
        Check if external_user_id is user-specific or organization-wide.
        
        Args:
            external_user_id: OpenRouter external user ID
            
        Returns:
            bool: True if user-specific, False if organization-wide
        """
        parsed = self.parse_external_user_id(external_user_id)
        return parsed is not None and parsed.get('is_user_specific', False)
    
    def get_fallback_external_user_id(self) -> str:
        """
        Get fallback external_user_id for backward compatibility.
        
        Returns:
            str: Organization-wide external user ID
        """
        return self.client_prefix
    
    def validate_mapping_configuration(self) -> Tuple[bool, str]:
        """
        Validate that user mapping configuration is correct.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            # Check if client prefix is available
            if not self.client_prefix:
                return False, "Client prefix not configured"
            
            # Validate client prefix format
            if not re.match(r'^mai_client_[a-zA-Z0-9_]+$', self.client_prefix):
                return False, f"Invalid client prefix format: {self.client_prefix}"
            
            # Check organization name
            if not self.organization_name:
                return False, "Organization name not configured"
            
            logger.info(f"User mapping validation passed for org: {self.organization_name}")
            return True, "Configuration valid"
            
        except Exception as e:
            error_msg = f"Validation failed: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_mapping_info(self) -> Dict[str, str]:
        """
        Get current mapping configuration information.
        
        Returns:
            dict: Mapping configuration details
        """
        return {
            'client_prefix': self.client_prefix,
            'organization_name': self.organization_name,
            'format_pattern': f"{self.client_prefix}_user_{{user_hash}}",
            'example_id': f"{self.client_prefix}_user_a1b2c3d4"
        }

# Global instance for easy access
user_mapping_service = UserMappingService()

def get_external_user_id(user_id: str, user_name: Optional[str] = None) -> str:
    """
    Convenience function to get external user ID for a mAI user.
    
    Args:
        user_id: mAI user UUID
        user_name: Optional user name for logging
        
    Returns:
        str: OpenRouter external_user ID
    """
    return user_mapping_service.generate_external_user_id(user_id, user_name)

def validate_user_mapping() -> Tuple[bool, str]:
    """
    Convenience function to validate user mapping configuration.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    return user_mapping_service.validate_mapping_configuration()

def get_mapping_info() -> Dict[str, str]:
    """
    Convenience function to get mapping configuration info.
    
    Returns:
        dict: Mapping configuration details
    """
    return user_mapping_service.get_mapping_info()