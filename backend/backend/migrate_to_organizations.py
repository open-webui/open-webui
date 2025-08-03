#!/usr/bin/env python3
"""
Migration script for existing deployments to organization model access.
Safely migrates existing users and models to the organization structure.
"""

import sqlite3
import os
import time
import argparse
import json
from datetime import datetime
import shutil


class OrganizationMigrator:
    """Handles migration of existing deployments to organization structure"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.backup_path = None
        self.migration_log = []
    
    def log(self, level: str, message: str):
        """Log migration events"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message
        }
        self.migration_log.append(log_entry)
        print(f"[{timestamp}] {level}: {message}")
    
    def create_backup(self) -> str:
        """Create a backup of the database before migration"""
        backup_dir = os.path.dirname(self.db_path)
        backup_name = f"webui.db.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.backup_path = os.path.join(backup_dir, backup_name)
        
        self.log("INFO", f"Creating backup at {self.backup_path}")
        shutil.copy2(self.db_path, self.backup_path)
        
        # Verify backup
        if os.path.exists(self.backup_path):
            backup_size = os.path.getsize(self.backup_path)
            original_size = os.path.getsize(self.db_path)
            if backup_size == original_size:
                self.log("INFO", f"Backup created successfully ({backup_size} bytes)")
                return self.backup_path
            else:
                raise Exception("Backup file size mismatch")
        else:
            raise Exception("Backup file not created")
    
    def verify_prerequisites(self) -> Dict[str, Any]:
        """Verify database is ready for migration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        checks = {
            "database_exists": os.path.exists(self.db_path),
            "has_users": False,
            "has_models": False,
            "organization_tables_exist": False,
            "already_migrated": False
        }
        
        try:
            # Check for users
            user_count = cursor.execute("SELECT COUNT(*) FROM user WHERE role != 'pending'").fetchone()[0]
            checks["has_users"] = user_count > 0
            checks["user_count"] = user_count
            
            # Check for models
            model_count = cursor.execute("SELECT COUNT(*) FROM model").fetchone()[0]
            checks["has_models"] = model_count > 0
            checks["model_count"] = model_count
            
            # Check if organization tables already exist
            tables = cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('organization_members', 'organization_models')
            """).fetchall()
            
            if len(tables) == 2:
                checks["organization_tables_exist"] = True
                
                # Check if already migrated
                org_member_count = cursor.execute("SELECT COUNT(*) FROM organization_members").fetchone()[0]
                checks["already_migrated"] = org_member_count > 0
                checks["existing_org_members"] = org_member_count
            
        except Exception as e:
            self.log("ERROR", f"Prerequisite check failed: {e}")
            checks["error"] = str(e)
        
        conn.close()
        return checks
    
    def create_organization_structure(self, conn: sqlite3.Connection):
        """Create organization tables and indexes"""
        cursor = conn.cursor()
        
        self.log("INFO", "Creating organization structure...")
        
        # Create organization_models table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organization_models (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at INTEGER,
                updated_at INTEGER,
                UNIQUE(organization_id, model_id)
            )
        """)
        
        # Create organization_members table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organization_members (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT DEFAULT 'member',
                is_active INTEGER DEFAULT 1,
                joined_at INTEGER,
                UNIQUE(organization_id, user_id)
            )
        """)
        
        # Create indexes
        indexes = [
            ("idx_org_members_user_active", "organization_members(user_id, is_active)"),
            ("idx_org_members_org_active", "organization_members(organization_id, is_active)"),
            ("idx_org_models_org_active", "organization_models(organization_id, is_active)"),
            ("idx_org_models_org_model", "organization_models(organization_id, model_id)", True)
        ]
        
        for index_name, index_def, *unique in indexes:
            unique_clause = "UNIQUE" if unique else ""
            try:
                cursor.execute(f"CREATE {unique_clause} INDEX IF NOT EXISTS {index_name} ON {index_def}")
                self.log("INFO", f"Created index: {index_name}")
            except Exception as e:
                self.log("WARNING", f"Index {index_name} may already exist: {e}")
        
        # Create user_available_models view
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS user_available_models AS
            SELECT DISTINCT
                om.user_id,
                orgmod.model_id,
                orgmod.organization_id,
                m.name as model_name,
                orgmod.is_active as model_active,
                om.is_active as member_active
            FROM organization_members om
            JOIN organization_models orgmod ON om.organization_id = orgmod.organization_id
            JOIN model m ON orgmod.model_id = m.id
            WHERE om.is_active = 1 AND orgmod.is_active = 1
        """)
        
        self.log("INFO", "Organization structure created successfully")
    
    def migrate_users_to_organization(self, conn: sqlite3.Connection, org_id: str, org_name: str) -> int:
        """Migrate all active users to the organization"""
        cursor = conn.cursor()
        
        self.log("INFO", f"Migrating users to organization: {org_name} ({org_id})")
        
        # Get all active users
        users = cursor.execute("""
            SELECT id, email, name, role 
            FROM user 
            WHERE role NOT IN ('pending', 'banned')
        """).fetchall()
        
        migrated_count = 0
        timestamp = int(time.time())
        
        for user_id, email, name, role in users:
            member_id = f"om_{user_id}_{org_id}"
            org_role = 'admin' if role == 'admin' else 'member'
            
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO organization_members 
                    (id, organization_id, user_id, role, is_active, joined_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (member_id, org_id, user_id, org_role, 1, timestamp))
                
                if cursor.rowcount > 0:
                    migrated_count += 1
                    self.log("DEBUG", f"Migrated user: {email} as {org_role}")
                
            except Exception as e:
                self.log("ERROR", f"Failed to migrate user {email}: {e}")
        
        self.log("INFO", f"Migrated {migrated_count} users to organization")
        return migrated_count
    
    def migrate_models_to_organization(self, conn: sqlite3.Connection, org_id: str, org_name: str) -> int:
        """Link all base models to the organization"""
        cursor = conn.cursor()
        
        self.log("INFO", f"Linking models to organization: {org_name} ({org_id})")
        
        # Get all base models (not user customizations)
        models = cursor.execute("""
            SELECT id, name, is_active 
            FROM model 
            WHERE base_model_id IS NULL
        """).fetchall()
        
        linked_count = 0
        timestamp = int(time.time())
        
        for model_id, model_name, is_active in models:
            org_model_id = f"orgmod_{org_id}_{model_id}"
            
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO organization_models 
                    (id, organization_id, model_id, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (org_model_id, org_id, model_id, is_active, timestamp, timestamp))
                
                if cursor.rowcount > 0:
                    linked_count += 1
                    self.log("DEBUG", f"Linked model: {model_name}")
                
            except Exception as e:
                self.log("ERROR", f"Failed to link model {model_name}: {e}")
        
        self.log("INFO", f"Linked {linked_count} models to organization")
        return linked_count
    
    def verify_migration(self, conn: sqlite3.Connection, org_id: str) -> Dict[str, Any]:
        """Verify migration was successful"""
        cursor = conn.cursor()
        
        verification = {}
        
        try:
            # Count migrated users
            verification["organization_members"] = cursor.execute("""
                SELECT COUNT(*) FROM organization_members 
                WHERE organization_id = ?
            """, (org_id,)).fetchone()[0]
            
            # Count linked models
            verification["organization_models"] = cursor.execute("""
                SELECT COUNT(*) FROM organization_models 
                WHERE organization_id = ?
            """, (org_id,)).fetchone()[0]
            
            # Check user model access
            verification["user_model_mappings"] = cursor.execute("""
                SELECT COUNT(*) FROM user_available_models
            """).fetchone()[0]
            
            # Sample user access check
            sample_user = cursor.execute("""
                SELECT user_id, COUNT(DISTINCT model_id) as accessible_models
                FROM user_available_models
                GROUP BY user_id
                LIMIT 1
            """).fetchone()
            
            if sample_user:
                verification["sample_user_id"] = sample_user[0]
                verification["sample_user_models"] = sample_user[1]
            
            verification["success"] = True
            
        except Exception as e:
            verification["success"] = False
            verification["error"] = str(e)
        
        return verification
    
    def perform_migration(self, org_id: str, org_name: str, skip_backup: bool = False) -> bool:
        """Perform the complete migration"""
        
        self.log("INFO", "="*60)
        self.log("INFO", f"Starting migration for: {org_name}")
        self.log("INFO", "="*60)
        
        # Step 1: Verify prerequisites
        self.log("INFO", "Step 1: Verifying prerequisites...")
        checks = self.verify_prerequisites()
        
        if not checks["has_users"]:
            self.log("ERROR", "No active users found to migrate")
            return False
        
        if checks.get("already_migrated", False):
            self.log("WARNING", f"Organization already has {checks.get('existing_org_members', 0)} members")
            response = input("Continue with migration anyway? (y/N): ")
            if response.lower() != 'y':
                self.log("INFO", "Migration cancelled by user")
                return False
        
        # Step 2: Create backup
        if not skip_backup:
            self.log("INFO", "Step 2: Creating backup...")
            try:
                self.create_backup()
            except Exception as e:
                self.log("ERROR", f"Backup failed: {e}")
                return False
        else:
            self.log("WARNING", "Skipping backup as requested")
        
        # Step 3: Perform migration
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = OFF")  # Disable FK constraints during migration
        
        try:
            # Start transaction
            conn.execute("BEGIN TRANSACTION")
            self.log("INFO", "Step 3: Starting migration transaction...")
            
            # Create structure
            self.create_organization_structure(conn)
            
            # Migrate users
            user_count = self.migrate_users_to_organization(conn, org_id, org_name)
            
            # Migrate models
            model_count = self.migrate_models_to_organization(conn, org_id, org_name)
            
            # Commit transaction
            conn.commit()
            self.log("INFO", "Migration transaction committed successfully")
            
            # Step 4: Verify migration
            self.log("INFO", "Step 4: Verifying migration...")
            verification = self.verify_migration(conn, org_id)
            
            if verification["success"]:
                self.log("INFO", "="*60)
                self.log("INFO", "✅ Migration completed successfully!")
                self.log("INFO", f"   Organization: {org_name}")
                self.log("INFO", f"   Members: {verification['organization_members']}")
                self.log("INFO", f"   Models: {verification['organization_models']}")
                self.log("INFO", f"   User-Model Mappings: {verification['user_model_mappings']}")
                self.log("INFO", "="*60)
                
                # Save migration log
                log_file = f"migration_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(log_file, 'w') as f:
                    json.dump({
                        "migration_summary": {
                            "organization_id": org_id,
                            "organization_name": org_name,
                            "users_migrated": user_count,
                            "models_linked": model_count,
                            "backup_path": self.backup_path,
                            "verification": verification
                        },
                        "migration_log": self.migration_log
                    }, f, indent=2)
                
                self.log("INFO", f"Migration log saved to: {log_file}")
                return True
            else:
                self.log("ERROR", f"Migration verification failed: {verification.get('error', 'Unknown error')}")
                conn.rollback()
                return False
                
        except Exception as e:
            self.log("ERROR", f"Migration failed: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def rollback_migration(self):
        """Rollback migration using backup"""
        if not self.backup_path or not os.path.exists(self.backup_path):
            self.log("ERROR", "No backup available for rollback")
            return False
        
        try:
            self.log("INFO", f"Rolling back using backup: {self.backup_path}")
            shutil.copy2(self.backup_path, self.db_path)
            self.log("INFO", "Rollback completed successfully")
            return True
        except Exception as e:
            self.log("ERROR", f"Rollback failed: {e}")
            return False


def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(
        description="Migrate existing mAI deployment to organization-based model access"
    )
    parser.add_argument("db_path", help="Path to webui.db database file")
    parser.add_argument("org_id", help="Organization ID (e.g., mai_client_company)")
    parser.add_argument("org_name", help="Organization display name")
    parser.add_argument("--skip-backup", action="store_true", help="Skip database backup")
    parser.add_argument("--rollback", action="store_true", help="Rollback previous migration")
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.db_path):
        print(f"❌ Database not found: {args.db_path}")
        return 1
    
    migrator = OrganizationMigrator(args.db_path)
    
    if args.rollback:
        # Perform rollback
        if migrator.rollback_migration():
            return 0
        else:
            return 1
    
    # Perform migration
    success = migrator.perform_migration(
        org_id=args.org_id,
        org_name=args.org_name,
        skip_backup=args.skip_backup
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())