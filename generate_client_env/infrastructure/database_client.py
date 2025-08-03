"""
Database client for infrastructure layer.

Handles all database operations for client organization management.
"""

import sqlite3
import os
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager


class DatabaseError(Exception):
    """Raised when database operations fail."""
    pass


class DatabaseClient:
    """Client for SQLite database operations."""
    
    def __init__(self, database_path: str):
        self.database_path = database_path
    
    def check_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Check if database exists and is accessible.
        
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        if not os.path.exists(self.database_path):
            return False, f"Database not found at: {self.database_path}"
        
        try:
            with self._get_connection() as conn:
                # Simple connectivity test
                conn.execute("SELECT 1")
            return True, None
        except Exception as e:
            return False, f"Database connection failed: {str(e)}"
    
    def get_existing_tables(self) -> List[str]:
        """
        Get list of existing tables in the database.
        
        Returns:
            List of table names
            
        Raises:
            DatabaseError: If operation fails
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """)
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            raise DatabaseError(f"Failed to get table list: {str(e)}")
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a specific table exists.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, (table_name,))
                return cursor.fetchone()[0] > 0
                
        except Exception:
            return False
    
    def insert_client_organization(self, org_data: Dict[str, Any]) -> bool:
        """
        Insert or replace client organization in database.
        
        Args:
            org_data: Organization data dictionary
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            DatabaseError: If operation fails
        """
        required_fields = ['id', 'name', 'openrouter_api_key', 'markup_rate', 'is_active', 'created_at', 'updated_at']
        
        # Validate required fields
        missing_fields = [field for field in required_fields if field not in org_data]
        if missing_fields:
            raise DatabaseError(f"Missing required fields: {', '.join(missing_fields)}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if client_organizations table exists
                if not self.table_exists('client_organizations'):
                    raise DatabaseError("client_organizations table not found")
                
                # Insert or replace organization
                cursor.execute("""
                    INSERT OR REPLACE INTO client_organizations 
                    (id, name, openrouter_api_key, markup_rate, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    org_data['id'],
                    org_data['name'],
                    org_data['openrouter_api_key'],
                    org_data['markup_rate'],
                    org_data['is_active'],
                    org_data['created_at'],
                    org_data['updated_at']
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            raise DatabaseError(f"Failed to insert client organization: {str(e)}")
    
    def get_client_organization(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get client organization by ID.
        
        Args:
            client_id: Client organization ID
            
        Returns:
            Organization data dictionary or None if not found
            
        Raises:
            DatabaseError: If operation fails
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, openrouter_api_key, markup_rate, is_active, created_at, updated_at
                    FROM client_organizations 
                    WHERE id = ?
                """, (client_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'name': row[1],
                        'openrouter_api_key': row[2],
                        'markup_rate': row[3],
                        'is_active': bool(row[4]),
                        'created_at': row[5],
                        'updated_at': row[6]
                    }
                return None
                
        except Exception as e:
            raise DatabaseError(f"Failed to get client organization: {str(e)}")
    
    def client_organization_exists(self, client_id: str) -> bool:
        """
        Check if client organization exists.
        
        Args:
            client_id: Client organization ID
            
        Returns:
            True if exists, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM client_organizations WHERE id = ?
                """, (client_id,))
                return cursor.fetchone()[0] > 0
                
        except Exception:
            return False
    
    def validate_database_schema(self) -> Tuple[bool, List[str], List[str]]:
        """
        Validate database schema against requirements.
        
        Returns:
            Tuple of (schema_valid: bool, existing_tables: List[str], missing_tables: List[str])
        """
        required_tables = [
            'client_organizations',
            'client_user_daily_usage', 
            'client_model_daily_usage',
            'processed_generations',
            'processed_generation_cleanup_log'
        ]
        
        try:
            existing_tables = self.get_existing_tables()
            missing_tables = [
                table for table in required_tables 
                if table not in existing_tables
            ]
            
            schema_valid = len(missing_tables) == 0
            return schema_valid, existing_tables, missing_tables
            
        except DatabaseError:
            return False, [], required_tables
    
    def create_missing_tables(self, missing_tables: List[str]) -> bool:
        """
        Create missing tables in the database.
        
        Args:
            missing_tables: List of table names to create
            
        Returns:
            bool: True if all tables created successfully, False otherwise
        """
        try:
            from ..domain.services import DatabaseSetupService
            
            table_sql = DatabaseSetupService.get_table_creation_sql()
            index_sql = DatabaseSetupService.get_index_creation_sql()
            
            with sqlite3.connect(self.database_path) as connection:
                cursor = connection.cursor()
                
                # Create missing tables
                for table_name in missing_tables:
                    if table_name in table_sql:
                        cursor.execute(table_sql[table_name])
                        
                # Create indexes for created tables
                for index_name, sql in index_sql.items():
                    try:
                        cursor.execute(sql)
                    except sqlite3.Error:
                        # Index creation is non-critical, continue if it fails
                        pass
                
                connection.commit()
                return True
                
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to create missing tables: {e}")
        except Exception as e:
            raise DatabaseError(f"Unexpected error creating tables: {e}")
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Get general database information.
        
        Returns:
            Dictionary with database metadata
        """
        try:
            schema_valid, existing_tables, missing_tables = self.validate_database_schema()
            
            return {
                'path': self.database_path,
                'exists': os.path.exists(self.database_path),
                'accessible': self.check_connection()[0],
                'table_count': len(existing_tables),
                'existing_tables': existing_tables,
                'missing_tables': missing_tables,
                'schema_valid': schema_valid
            }
            
        except Exception as e:
            return {
                'path': self.database_path,
                'exists': os.path.exists(self.database_path),
                'accessible': False,
                'error': str(e)
            }
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = None
        try:
            conn = sqlite3.connect(self.database_path)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()