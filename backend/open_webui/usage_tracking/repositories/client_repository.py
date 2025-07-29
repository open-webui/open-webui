"""
Client Repository - Data access for client organizations
Handles all database operations related to client management
"""

import sqlite3
from typing import List, Optional
from open_webui.config import DATA_DIR
from ..models.entities import ClientInfo

DB_PATH = f"{DATA_DIR}/webui.db"


class ClientRepository:
    """Repository for client organization data operations"""
    
    @staticmethod
    def get_client_by_api_key(api_key: str) -> Optional[str]:
        """Get client organization ID by API key"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT id FROM client_organizations WHERE openrouter_api_key = ? AND is_active = 1",
                (api_key,)
            )
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()
    
    @staticmethod
    def get_all_active_clients() -> List[tuple]:
        """Get all active client organizations with API keys"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, name, openrouter_api_key 
                FROM client_organizations 
                WHERE is_active = 1 AND openrouter_api_key IS NOT NULL
            """)
            return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def get_client_info(client_id: str) -> Optional[ClientInfo]:
        """Get detailed client information"""
        try:
            from open_webui.models.organization_usage import ClientOrganizationDB
            client = ClientOrganizationDB.get_client_by_id(client_id)
            
            if client:
                return ClientInfo(
                    id=client.id,
                    name=client.name,
                    markup_rate=client.markup_rate,
                    is_active=client.is_active,
                    openrouter_api_key=client.openrouter_api_key
                )
            return None
        except Exception:
            return None
    
    @staticmethod
    def get_environment_client_id() -> Optional[str]:
        """Get client organization ID for environment-based setup"""
        try:
            from open_webui.models.organization_usage import ClientOrganizationDB
            from open_webui.config import ORGANIZATION_NAME
            import hashlib
            
            print(f"🔍 [DEBUG] ClientRepository.get_environment_client_id called")
            print(f"🔍 [DEBUG] ORGANIZATION_NAME: {ORGANIZATION_NAME}")
            
            # For environment-based setup, get the first (and should be only) active client
            orgs = ClientOrganizationDB.get_all_active_clients()
            print(f"🔍 [DEBUG] Found {len(orgs)} active client organizations")
            if orgs:
                client_id = orgs[0].id
                print(f"🔍 [DEBUG] Using first active client ID: {client_id}")
                return client_id
            
            # Fallback: create a default client org ID based on organization name
            if ORGANIZATION_NAME:
                org_hash = hashlib.md5(ORGANIZATION_NAME.encode()).hexdigest()[:8]
                fallback_id = f"env_client_{org_hash}"
                print(f"🔍 [DEBUG] No active clients found, using fallback ID: {fallback_id}")
                return fallback_id
            
            print(f"🔍 [DEBUG] No organization name set, using default ID")
            return "env_client_default"
        except Exception as e:
            print(f"❌ [DEBUG] Failed to get client org ID: {e}")
            return None