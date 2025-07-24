#!/usr/bin/env python3
"""
Production Auto-Sync Fix for mAI OpenRouter API Keys

This script enhances the auto-sync mechanism to ensure reliable API key
synchronization from UI settings to the organization database.

Features:
- Validates API keys before storing
- Provides user feedback on sync status
- Handles edge cases gracefully
- Maintains backward compatibility

Usage:
1. Apply the enhanced sync method to openrouter_client_manager.py
2. Update the config update endpoint to use better error handling
3. Add user notifications for sync status
"""

import time
import sqlite3
from typing import Dict, Any, Optional


class EnhancedAutoSync:
    """Enhanced auto-sync implementation for production use"""
    
    def __init__(self, db_path: str = "/app/backend/data/webui.db"):
        self.db_path = db_path
    
    def sync_ui_key_to_organization(
        self, 
        user_id: str, 
        api_key: str,
        validate_key: bool = True
    ) -> Dict[str, Any]:
        """
        Enhanced sync method with better error handling and validation
        
        Args:
            user_id: The user who updated the API key
            api_key: The new OpenRouter API key from UI settings
            validate_key: Whether to validate the API key format
            
        Returns:
            Dict with detailed sync status and user-friendly messages
        """
        try:
            # 1. Input validation
            if not user_id or not api_key:
                return {
                    "success": False,
                    "message": "Missing user ID or API key",
                    "user_action_required": False,
                    "error_code": "INVALID_INPUT"
                }
            
            # 2. API key format validation
            if validate_key and not api_key.startswith("sk-or-"):
                return {
                    "success": False,
                    "message": "Invalid OpenRouter API key format. Key must start with 'sk-or-'",
                    "user_action_required": True,
                    "error_code": "INVALID_KEY_FORMAT"
                }
            
            # 3. Get user's organization mapping
            mapping = self._get_user_mapping(user_id)
            if not mapping:
                # Try to create default mapping if none exists
                mapping = self._create_default_mapping(user_id)
                if not mapping:
                    return {
                        "success": False,
                        "message": "No organization found for your account. Please contact administrator.",
                        "user_action_required": True,
                        "error_code": "NO_ORGANIZATION_MAPPING"
                    }
            
            # 4. Get organization details
            org = self._get_organization(mapping["client_org_id"])
            if not org:
                return {
                    "success": False,
                    "message": f"Organization {mapping['client_org_id']} not found in database",
                    "user_action_required": True,
                    "error_code": "ORGANIZATION_NOT_FOUND"
                }
            
            # 5. Update organization with new API key
            success = self._update_organization_key(mapping["client_org_id"], api_key)
            
            if success:
                return {
                    "success": True,
                    "message": f"✅ API key successfully synced to organization '{org['name']}'",
                    "organization_updated": mapping["client_org_id"],
                    "organization_name": org["name"],
                    "user_action_required": False
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to update organization API key in database",
                    "user_action_required": True,
                    "error_code": "DATABASE_UPDATE_FAILED"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Sync failed due to system error: {str(e)}",
                "user_action_required": True,
                "error_code": "SYSTEM_ERROR"
            }
    
    def _get_user_mapping(self, user_id: str) -> Optional[Dict[str, str]]:
        """Get user's organization mapping"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT user_id, client_org_id, openrouter_user_id FROM user_client_mapping WHERE user_id = ?",
                    (user_id,)
                )
                result = cursor.fetchone()
                if result:
                    return {
                        "user_id": result[0],
                        "client_org_id": result[1],
                        "openrouter_user_id": result[2]
                    }
                return None
        except Exception:
            return None
    
    def _get_organization(self, org_id: str) -> Optional[Dict[str, str]]:
        """Get organization details"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, name, openrouter_api_key, is_active FROM client_organizations WHERE id = ?",
                    (org_id,)
                )
                result = cursor.fetchone()
                if result:
                    return {
                        "id": result[0],
                        "name": result[1],
                        "openrouter_api_key": result[2],
                        "is_active": result[3]
                    }
                return None
        except Exception:
            return None
    
    def _create_default_mapping(self, user_id: str) -> Optional[Dict[str, str]]:
        """Create default organization mapping for user if none exists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if default organization exists
                cursor.execute("SELECT id FROM client_organizations WHERE name = 'Default Organization'")
                org_result = cursor.fetchone()
                
                if org_result:
                    org_id = org_result[0]
                    current_time = int(time.time())
                    
                    # Create user mapping
                    cursor.execute("""
                        INSERT INTO user_client_mapping 
                        (user_id, client_org_id, openrouter_user_id, is_active, created_at, updated_at)
                        VALUES (?, ?, ?, 1, ?, ?)
                    """, (user_id, org_id, f"openrouter_{user_id}", current_time, current_time))
                    
                    conn.commit()
                    
                    return {
                        "user_id": user_id,
                        "client_org_id": org_id,
                        "openrouter_user_id": f"openrouter_{user_id}"
                    }
                return None
        except Exception:
            return None
    
    def _update_organization_key(self, org_id: str, api_key: str) -> bool:
        """Update organization's API key"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE client_organizations 
                    SET openrouter_api_key = ?, updated_at = ?
                    WHERE id = ?
                """, (api_key, int(time.time()), org_id))
                
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False
    
    def validate_sync_setup(self, user_id: str) -> Dict[str, Any]:
        """Validate that sync setup is correct for a user"""
        mapping = self._get_user_mapping(user_id)
        if not mapping:
            return {
                "valid": False,
                "issue": "No organization mapping found",
                "fix": "Create user-organization mapping"
            }
        
        org = self._get_organization(mapping["client_org_id"])
        if not org:
            return {
                "valid": False,
                "issue": "Organization not found",
                "fix": "Create organization or fix mapping"
            }
        
        return {
            "valid": True,
            "organization": org["name"],
            "current_api_key": org["openrouter_api_key"][:20] + "..." if org["openrouter_api_key"] else "None"
        }


# Example implementation for the router endpoint
def enhanced_config_update_handler(user_id: str, api_keys: list) -> Dict[str, Any]:
    """
    Enhanced config update handler with better sync feedback
    
    This should be integrated into the /config/update endpoint
    """
    sync_results = []
    
    # Process OpenRouter API keys
    for idx, (base_url, api_key) in enumerate(zip(base_urls, api_keys)):
        if "openrouter.ai" in base_url and api_key:
            sync = EnhancedAutoSync()
            result = sync.sync_ui_key_to_organization(user_id, api_key.strip())
            
            sync_results.append({
                "index": idx,
                "url": base_url,
                "sync_result": result
            })
            
            # Log detailed result
            if result["success"]:
                print(f"✅ API key auto-sync successful: {result['message']}")
            else:
                print(f"❌ API key auto-sync failed: {result['message']} (Code: {result.get('error_code', 'UNKNOWN')})")
    
    return {
        "config_updated": True,
        "sync_results": sync_results,
        "user_notifications": [
            {
                "type": "success" if r["sync_result"]["success"] else "error",
                "message": r["sync_result"]["message"],
                "action_required": r["sync_result"].get("user_action_required", False)
            }
            for r in sync_results
        ]
    }


if __name__ == "__main__":
    # Test the enhanced sync
    sync = EnhancedAutoSync("backend/data/webui.db")
    
    # Validate setup for your user
    user_id = "86b5496d-52c8-40f3-a9b1-098560aeb395"
    validation = sync.validate_sync_setup(user_id)
    
    print("=== SYNC SETUP VALIDATION ===")
    print(f"Valid: {validation['valid']}")
    if validation['valid']:
        print(f"Organization: {validation['organization']}")
        print(f"Current API Key: {validation['current_api_key']}")
    else:
        print(f"Issue: {validation['issue']}")
        print(f"Fix: {validation['fix']}")
    
    # Test sync with correct API key
    if validation['valid']:
        test_key = "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"
        result = sync.sync_ui_key_to_organization(user_id, test_key)
        
        print("\n=== SYNC TEST RESULT ===")
        print(f"Success: {result['success']}")
        print(f"Message: {result['message']}")
        if not result['success']:
            print(f"Error Code: {result.get('error_code', 'UNKNOWN')}")
            print(f"User Action Required: {result.get('user_action_required', False)}")