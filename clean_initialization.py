#!/usr/bin/env python3
"""
Complete cleanup script for mAI production initialization testing.

This script prepares a clean environment for testing the new production
client setup script (generate_client_env_production.py) by removing all
artifacts from previous initialization attempts.

Usage:
    python clean_initialization.py            # Standard cleanup
    python clean_initialization.py --deep     # Deep cleanup (includes more artifacts)
    python clean_initialization.py --dry-run  # Show what would be cleaned
"""

import os
import sqlite3
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime

def calculate_directory_size(path):
    """Calculate total size of a directory."""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except (OSError, FileNotFoundError):
                    pass
    except (OSError, FileNotFoundError):
        pass
    return total_size

def clean_environment_files(dry_run=False):
    """Remove generated environment files."""
    print("🧹 Cleaning environment files...")
    
    # Extended list including production test files
    env_files = [
        ".env",
        ".env.dev",
        "backend/.env",
        "backend/.env.backup",
        "docker-compose.yml",
        "docker-compose.override.yml",
    ]
    
    # Add pattern-based cleanup for backup files
    env_patterns = [
        ".env.backup.*",
        "*.env.bak",
    ]
    
    # Clean specific files
    for env_file in env_files:
        env_path = Path(env_file)
        if env_path.exists():
            try:
                if dry_run:
                    size = env_path.stat().st_size / 1024
                    print(f"🔍 Would remove: {env_file} ({size:.1f} KB)")
                else:
                    size = env_path.stat().st_size / 1024
                    env_path.unlink()
                    print(f"✅ Removed: {env_file} ({size:.1f} KB)")
            except Exception as e:
                print(f"❌ Failed to remove {env_file}: {e}")
        else:
            print(f"✅ Not found: {env_file}")
    
    # Clean pattern-based files
    for pattern in env_patterns:
        for file_path in Path(".").glob(pattern):
            try:
                if dry_run:
                    print(f"🔍 Would remove: {file_path}")
                else:
                    file_path.unlink()
                    print(f"✅ Removed: {file_path}")
            except Exception as e:
                print(f"❌ Failed to remove {file_path}: {e}")

def clean_database_usage_data(dry_run=False):
    """Clear all usage-related data from databases."""
    print("\n🗄️  Cleaning database usage data...")
    
    # Database locations to check
    db_paths = [
        "backend/data/webui.db",
        "backend/open_webui/data/webui.db",
        "data/webui.db",  # Production location
    ]
    
    # Extended usage tables including new production tables
    usage_tables = [
        'client_daily_usage',
        'client_live_counters', 
        'client_model_daily_usage',
        'client_organizations',
        'client_user_daily_usage',
        'processed_generations',
        'processed_generation_cleanup_log',
        'user_client_mapping',
        'usage_keys',  # If exists
        'organization_model_access',  # If exists
    ]
    
    for db_path in db_paths:
        db_file = Path(db_path)
        if db_file.exists() and not db_file.is_symlink():
            print(f"\n📋 Cleaning database: {db_path}")
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                for table in usage_tables:
                    try:
                        # First check if table exists
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        
                        if dry_run:
                            print(f"  🔍 Would delete {count} records from {table}")
                        else:
                            cursor.execute(f'DELETE FROM {table}')
                            rows_deleted = cursor.rowcount
                            print(f"  ✅ {table}: {rows_deleted} records deleted")
                    except sqlite3.OperationalError:
                        print(f"  ⚠️  {table}: Table doesn't exist (OK)")
                    except Exception as e:
                        print(f"  ❌ {table}: Error - {e}")
                
                conn.commit()
                conn.close()
                print(f"  ✅ Database {db_path} cleaned successfully")
                
            except Exception as e:
                print(f"  ❌ Failed to clean {db_path}: {e}")
        else:
            if db_file.is_symlink():
                print(f"⚠️  Skipping symlink: {db_path}")
            else:
                print(f"✅ Database not found: {db_path}")

def remove_symlinks(dry_run=False):
    """Remove any symlinks created during previous attempts."""
    print("\n🔗 Removing symlinks...")
    
    potential_symlinks = [
        "backend/data/webui.db",
        "data/webui.db",
    ]
    
    for symlink_path in potential_symlinks:
        symlink = Path(symlink_path)
        if symlink.is_symlink():
            try:
                if dry_run:
                    target = os.readlink(symlink)
                    print(f"🔍 Would remove symlink: {symlink_path} -> {target}")
                else:
                    symlink.unlink()
                    print(f"✅ Removed symlink: {symlink_path}")
            except Exception as e:
                print(f"❌ Failed to remove symlink {symlink_path}: {e}")
        else:
            print(f"✅ No symlink found: {symlink_path}")

def clean_python_artifacts(dry_run=False, deep=False):
    """Remove Python cache files from all relevant modules."""
    print("\n🐍 Cleaning Python artifacts...")
    
    # Base directories to clean
    search_dirs = ["generate_client_env"]
    
    if deep:
        # Add more directories in deep mode
        search_dirs.extend([
            "backend",
            ".",  # Root directory
        ])
    
    cache_dirs_count = 0
    pyc_files_count = 0
    
    for search_dir in search_dirs:
        # Remove __pycache__ directories
        pycache_dirs = list(Path(search_dir).rglob("__pycache__"))
        
        for pycache_dir in pycache_dirs:
            try:
                if dry_run:
                    size = calculate_directory_size(pycache_dir) / 1024
                    print(f"🔍 Would remove: {pycache_dir} ({size:.1f} KB)")
                else:
                    shutil.rmtree(pycache_dir)
                    print(f"✅ Removed: {pycache_dir}")
                cache_dirs_count += 1
            except Exception as e:
                print(f"❌ Failed to remove {pycache_dir}: {e}")
        
        # Remove .pyc files
        pyc_files = list(Path(search_dir).rglob("*.pyc"))
        for pyc_file in pyc_files:
            try:
                if dry_run:
                    print(f"🔍 Would remove: {pyc_file}")
                else:
                    pyc_file.unlink()
                pyc_files_count += 1
            except Exception:
                pass
    
    print(f"📊 Summary: {cache_dirs_count} cache dirs, {pyc_files_count} .pyc files {'would be' if dry_run else ''} removed")

def clean_docker_environment(dry_run=False):
    """Clean up any Docker-related artifacts."""
    print("\n🐳 Cleaning Docker environment...")
    
    # Check for Docker volumes (informational only)
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "volume", "ls", "--format", "{{.Name}}"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            volumes = [v for v in result.stdout.strip().split('\n') if 'mai' in v.lower()]
            if volumes:
                print("⚠️  Found Docker volumes (manual cleanup needed):")
                for volume in volumes:
                    print(f"     - {volume}")
                print("   Run: docker volume rm <volume_name> to remove")
            else:
                print("✅ No mAI-related Docker volumes found")
        else:
            print("✅ Docker not available or no volumes")
            
    except Exception as e:
        print(f"✅ Docker check skipped: {e}")

def verify_clean_state():
    """Verify that the environment is clean."""
    print("\n🔍 Verifying clean state...")
    
    # Check environment files
    env_exists = Path(".env").exists()
    print(f"Environment file: {'❌ Still exists' if env_exists else '✅ Clean'}")
    
    # Check database usage data
    db_path = Path("backend/data/webui.db")
    if db_path.exists() and not db_path.is_symlink():
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM client_organizations")
            org_count = cursor.fetchone()[0]
            conn.close()
            print(f"Database organizations: {'❌ ' + str(org_count) + ' found' if org_count > 0 else '✅ Clean'}")
        except Exception:
            print("Database organizations: ✅ Clean (table doesn't exist)")
    else:
        print("Database organizations: ✅ Clean (no database)")
    
    # Check symlinks
    symlink_exists = Path("backend/data/webui.db").is_symlink()
    print(f"Symlinks: {'❌ Still exist' if symlink_exists else '✅ Clean'}")

def clean_build_artifacts(dry_run=False, deep=False):
    """Remove build artifacts and dependencies."""
    print("\n🏗️  Cleaning build artifacts...")
    
    artifacts = [
        ("node_modules", "JavaScript dependencies"),
        (".svelte-kit", "SvelteKit build cache"),
        ("build", "Production build output"),
    ]
    
    if deep:
        artifacts.extend([
            ("backend/data/cache", "Application cache"),
            ("backend/data/uploads", "User uploads"),
            ("backend/static/tmp", "Temporary files"),
        ])
    
    for path, desc in artifacts:
        path_obj = Path(path)
        if path_obj.exists():
            try:
                if path_obj.is_dir():
                    size = calculate_directory_size(path) / (1024 * 1024)
                    if dry_run:
                        print(f"🔍 Would remove {desc}: {path} ({size:.1f} MB)")
                    else:
                        shutil.rmtree(path)
                        print(f"✅ Removed {desc}: {path} ({size:.1f} MB)")
                else:
                    if dry_run:
                        print(f"🔍 Would remove {desc}: {path}")
                    else:
                        path_obj.unlink()
                        print(f"✅ Removed {desc}: {path}")
            except Exception as e:
                print(f"❌ Failed to remove {desc}: {e}")
        else:
            print(f"✅ {desc}: Not found")

def create_git_checkpoint():
    """Create a git checkpoint before cleanup."""
    print("📋 Creating git checkpoint...")
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'add', '.'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            result = subprocess.run(
                ['git', 'commit', '-m', f'CHECKPOINT: Before production cleanup - {datetime.now().isoformat()}'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("✅ Git checkpoint created successfully")
            else:
                print("⚠️  No changes to commit (already clean?)")
        else:
            print("⚠️  Failed to stage files for checkpoint")
    except Exception as e:
        print(f"⚠️  Git checkpoint skipped: {e}")

def main():
    """Run the complete cleanup process."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Clean mAI environment for production initialization testing"
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Perform deep cleanup including more artifacts"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned without actually cleaning"
    )
    parser.add_argument(
        "--no-checkpoint",
        action="store_true",
        help="Skip git checkpoint creation"
    )
    
    args = parser.parse_args()
    
    print("🧹 mAI Production Initialization Cleanup")
    print("=" * 50)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    if args.deep:
        print("🔥 DEEP CLEANUP MODE - More artifacts will be removed")
    
    print("\nThis script prepares a clean environment for testing")
    print("the production client setup script.\n")
    
    # Create git checkpoint unless skipped
    if not args.no_checkpoint and not args.dry_run:
        create_git_checkpoint()
    
    # Run cleanup steps
    clean_environment_files(args.dry_run)
    remove_symlinks(args.dry_run)
    clean_database_usage_data(args.dry_run)
    clean_python_artifacts(args.dry_run, args.deep)
    clean_build_artifacts(args.dry_run, args.deep)
    clean_docker_environment(args.dry_run)
    
    # Verify cleanup
    if not args.dry_run:
        verify_clean_state()
    
    print("\n🎉 Cleanup Complete!")
    print("=" * 25)
    
    if args.dry_run:
        print("\nThis was a dry run. To actually clean, run without --dry-run")
    else:
        print("Your environment is now clean and ready for production testing.")
        print("\n📋 Next steps for production testing:")
        print("1. Activate virtual environment:")
        print("   source backend/venv-312/bin/activate")
        print("\n2. Test the new production setup script:")
        print("   python generate_client_env_production.py")
        print("\n3. Follow the interactive setup wizard!")

if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n⚠️  Cleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during cleanup: {e}")
        sys.exit(1)