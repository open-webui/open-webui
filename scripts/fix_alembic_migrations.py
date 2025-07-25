#!/usr/bin/env python3
"""
Alembic Migration Cleanup Script for mAI

This script safely resolves Alembic migration conflicts that occur when 
migration files have been deleted but the database still references them.

Features:
- Backs up current database before making changes
- Checks current migration state
- Resets Alembic state to point to latest available migration
- Preserves all user data during cleanup
- Provides detailed logging of all operations

Usage:
    python scripts/fix_alembic_migrations.py [--dry-run] [--backup-path PATH]

Requirements:
    - Run from mAI project root directory
    - SQLite database should be accessible
    - Write permissions for backup creation
"""

import os
import sys
import sqlite3
import shutil
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add the backend path to import mAI modules
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

class AlembicCleanup:
    """Handles safe Alembic migration cleanup for mAI"""
    
    def __init__(self, dry_run: bool = False, backup_path: Optional[str] = None):
        self.dry_run = dry_run
        self.backup_path = backup_path or f"database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        self.project_root = Path(__file__).parent.parent
        self.backend_path = self.project_root / "backend"
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(f"alembic_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def find_database_path(self) -> Optional[str]:
        """Find the SQLite database file"""
        possible_paths = [
            self.backend_path / "open_webui" / "webui.db",
            self.backend_path / "data" / "webui.db", 
            self.backend_path / "webui.db",
            self.project_root / "webui.db",
            # Docker volume paths
            "/app/backend/data/webui.db",
            "./backend/data/webui.db"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                self.logger.info(f"📂 Found database at: {path}")
                return str(path)
                
        self.logger.error("❌ Could not find database file")
        return None
    
    def backup_database(self, db_path: str) -> bool:
        """Create a backup of the database"""
        try:
            if os.path.exists(self.backup_path):
                backup_with_timestamp = f"{self.backup_path}_{datetime.now().strftime('%H%M%S')}"
                self.logger.warning(f"⚠️  Backup exists, using: {backup_with_timestamp}")
                self.backup_path = backup_with_timestamp
                
            if not self.dry_run:
                shutil.copy2(db_path, self.backup_path)
                self.logger.info(f"✅ Database backed up to: {self.backup_path}")
            else:
                self.logger.info(f"🔍 [DRY RUN] Would backup database to: {self.backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Backup failed: {e}")
            return False
    
    def get_current_migration_state(self, db_path: str) -> Optional[str]:
        """Get the current migration revision from the database"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if alembic_version table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='alembic_version'
            """)
            
            if not cursor.fetchone():
                self.logger.info("📋 No alembic_version table found - database not initialized")
                conn.close()
                return None
                
            # Get current revision
            cursor.execute("SELECT version_num FROM alembic_version")
            result = cursor.fetchone()
            conn.close()
            
            if result:
                current_revision = result[0]
                self.logger.info(f"📍 Current migration revision: {current_revision}")
                return current_revision
            else:
                self.logger.info("📋 No migration revision found in database")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error checking migration state: {e}")
            return None
    
    def get_available_migrations(self) -> List[Dict[str, Any]]:
        """Get list of available migration files"""
        try:
            migrations_dir = self.backend_path / "open_webui" / "migrations" / "versions"
            migration_files = []
            
            for file_path in migrations_dir.glob("*.py"):
                if file_path.name == "__init__.py":
                    continue
                    
                # Extract revision ID from filename
                filename = file_path.name
                if "_" in filename:
                    revision_id = filename.split("_", 1)[0]
                    
                    # Read the migration file to get more details
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                            
                        # Extract down_revision
                        down_revision = None
                        for line in content.split('\n'):
                            if 'down_revision' in line and '=' in line:
                                down_revision = line.split('=')[1].strip().strip('"\'')
                                if down_revision == "None":
                                    down_revision = None
                                break
                        
                        migration_files.append({
                            'revision': revision_id,
                            'file': str(file_path),
                            'filename': filename,
                            'down_revision': down_revision
                        })
                        
                    except Exception as e:
                        self.logger.warning(f"⚠️  Could not parse migration file {filename}: {e}")
            
            # Sort by filename to get chronological order
            migration_files.sort(key=lambda x: x['filename'])
            
            self.logger.info(f"📂 Found {len(migration_files)} migration files")
            for migration in migration_files:
                self.logger.info(f"   📄 {migration['revision']}: {migration['filename']}")
                
            return migration_files
            
        except Exception as e:
            self.logger.error(f"❌ Error reading migrations: {e}")
            return []
    
    def find_latest_migration(self, migrations: List[Dict[str, Any]]) -> Optional[str]:
        """Find the latest migration that doesn't depend on missing migrations"""
        if not migrations:
            return None
            
        # Build dependency map
        revision_map = {m['revision']: m for m in migrations}
        available_revisions = set(revision_map.keys())
        
        # Find migrations that don't have down_revision or whose down_revision exists
        valid_migrations = []
        for migration in migrations:
            down_rev = migration['down_revision']
            if down_rev is None or down_rev in available_revisions:
                valid_migrations.append(migration)
        
        if valid_migrations:
            # Return the last valid migration (chronologically)
            latest = valid_migrations[-1]
            self.logger.info(f"🎯 Latest valid migration: {latest['revision']} ({latest['filename']})")
            return latest['revision']
        else:
            self.logger.warning("⚠️  No valid migrations found")
            return None
    
    def reset_migration_state(self, db_path: str, target_revision: str) -> bool:
        """Reset the database migration state to target revision"""
        try:
            if self.dry_run:
                self.logger.info(f"🔍 [DRY RUN] Would reset migration state to: {target_revision}")
                return True
                
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create alembic_version table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """)
            
            # Clear existing version
            cursor.execute("DELETE FROM alembic_version")
            
            # Insert new version
            cursor.execute("INSERT INTO alembic_version (version_num) VALUES (?)", (target_revision,))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"✅ Migration state reset to: {target_revision}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error resetting migration state: {e}")
            return False
    
    def check_missing_revision(self, db_path: str, missing_revision: str = "e41f3b2a9d75") -> bool:
        """Check if the database references the known missing revision"""
        current_revision = self.get_current_migration_state(db_path)
        if current_revision == missing_revision:
            self.logger.warning(f"⚠️  Database references missing revision: {missing_revision}")
            return True
        return False
    
    def run_cleanup(self) -> bool:
        """Main cleanup process"""
        self.logger.info("🚀 Starting Alembic migration cleanup")
        
        if self.dry_run:
            self.logger.info("🔍 Running in DRY RUN mode - no changes will be made")
        
        # Step 1: Find database
        db_path = self.find_database_path()
        if not db_path:
            return False
        
        # Step 2: Check if we have the specific missing revision issue
        if not self.check_missing_revision(db_path):
            self.logger.info("✅ No missing revision issue detected")
            return True
        
        # Step 3: Backup database
        if not self.backup_database(db_path):
            return False
        
        # Step 4: Get available migrations
        migrations = self.get_available_migrations()
        if not migrations:
            self.logger.error("❌ No migration files found")
            return False
        
        # Step 5: Find latest valid migration
        target_revision = self.find_latest_migration(migrations)
        if not target_revision:
            self.logger.error("❌ Could not determine target migration")
            return False
        
        # Step 6: Reset migration state
        self.logger.info(f"🔄 Resetting migration state to latest valid revision: {target_revision}")
        
        if not self.reset_migration_state(db_path, target_revision):
            return False
        
        self.logger.info("🎉 Alembic cleanup completed successfully!")
        self.logger.info(f"📁 Backup available at: {self.backup_path}")
        
        return True

def main():
    parser = argparse.ArgumentParser(
        description="Fix mAI Alembic migration issues safely",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Preview what would be changed
    python scripts/fix_alembic_migrations.py --dry-run
    
    # Run the cleanup with custom backup path
    python scripts/fix_alembic_migrations.py --backup-path ./my_backup.db
    
    # Run the cleanup
    python scripts/fix_alembic_migrations.py
        """
    )
    
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Preview changes without modifying the database'
    )
    
    parser.add_argument(
        '--backup-path',
        type=str,
        help='Custom path for database backup'
    )
    
    args = parser.parse_args()
    
    # Ensure we're in the right directory
    project_root = Path(__file__).parent.parent
    if not (project_root / "backend" / "open_webui").exists():
        print("❌ Error: Please run this script from the mAI project root directory")
        sys.exit(1)
    
    # Run cleanup
    cleanup = AlembicCleanup(dry_run=args.dry_run, backup_path=args.backup_path)
    success = cleanup.run_cleanup()
    
    if success:
        if args.dry_run:
            print("\n✅ Dry run completed successfully!")
            print("💡 Run without --dry-run to apply changes")
        else:
            print("\n✅ Alembic cleanup completed successfully!")
            print("🚀 Try running your Docker container now")
        sys.exit(0)
    else:
        print("\n❌ Alembic cleanup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()