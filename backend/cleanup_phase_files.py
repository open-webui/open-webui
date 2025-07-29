#!/usr/bin/env python3
"""
Safe cleanup script for Phase 1-5 development files.
Removes files that are no longer needed in production.
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime


def get_backend_root():
    """Get the backend root directory"""
    script_dir = Path(__file__).parent
    return script_dir


def backup_files(files_to_delete, backup_dir):
    """Create backups of files before deletion"""
    backup_path = backup_dir / f"phase_cleanup_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_path.mkdir(parents=True, exist_ok=True)
    
    backed_up = []
    for file_path in files_to_delete:
        if file_path.exists():
            # Preserve directory structure in backup
            relative_path = file_path.relative_to(get_backend_root())
            backup_file = backup_path / relative_path
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                shutil.copy2(file_path, backup_file)
                backed_up.append(str(relative_path))
            except Exception as e:
                print(f"⚠️  Warning: Could not backup {file_path}: {e}")
    
    return backup_path, backed_up


def main():
    """Main cleanup function"""
    print("🧹 Phase 1-5 Development Files Cleanup Script")
    print("=" * 60)
    
    backend_root = get_backend_root()
    print(f"Backend root: {backend_root}")
    
    # Define files to delete (relative to backend root)
    files_to_delete = [
        # Test Files (7)
        "test_organization_model_access.py",
        "test_automatic_initialization.py", 
        "test_security_improvements.py",
        "backend/test_automatic_initialization.py",
        "backend/test_organization_access_comprehensive.py",
        "backend/test_security_improvements.py",
        "backend/performance_test_300_users.py",
        
        # Setup Scripts (6)
        "setup_organization_model_access.py",
        "backend/setup_organization_model_access.py",
        "backend/backend/setup_organization_model_access.py",
        "add_organization_indexes.py",
        "backend/add_organization_indexes.py",
        "register_openrouter_models.py",
        "backend/fix_olaf_model_access.py",
        
        # Patch Scripts (5)
        "patch_organization_model_access.py",
        "patch_usage_tracking_init.py",
        "backend/patch_usage_tracking_init.py",
        "secure_models_patch.py",
        "backend/secure_models_patch.py",
        
        # Extended/Development Files (2)
        "extended_usage_tracking_init.py",
        "backend/extended_usage_tracking_init.py",
        
        # Verification Scripts (1)
        "backend/verify_organization_indexes.py"
    ]
    
    # Convert to Path objects and check existence
    file_paths = []
    existing_files = []
    missing_files = []
    
    for file_rel_path in files_to_delete:
        file_path = backend_root / file_rel_path
        file_paths.append(file_path)
        
        if file_path.exists():
            existing_files.append(file_path)
        else:
            missing_files.append(file_rel_path)
    
    print(f"\n📋 Analysis:")
    print(f"   Files to delete: {len(files_to_delete)}")
    print(f"   Files found: {len(existing_files)}")
    print(f"   Files missing: {len(missing_files)}")
    
    if missing_files:
        print(f"\n📝 Missing files (already deleted or moved):")
        for file_path in missing_files[:5]:  # Show first 5
            print(f"   - {file_path}")
        if len(missing_files) > 5:
            print(f"   ... and {len(missing_files) - 5} more")
    
    if not existing_files:
        print("\n✅ No files to delete - cleanup already complete!")
        return 0
    
    print(f"\n📂 Files to be deleted:")
    for file_path in existing_files:
        relative_path = file_path.relative_to(backend_root)
        file_size = file_path.stat().st_size if file_path.exists() else 0
        print(f"   - {relative_path} ({file_size:,} bytes)")
    
    # Safety check - ensure we're not deleting critical files
    critical_files = [
        "open_webui/models/models.py",
        "open_webui/utils/usage_tracking_init.py",
        "open_webui/routers/health_check.py",
        "PRODUCTION_DEPLOYMENT_GUIDE.md",
        "backend/migrate_to_organizations.py",
        "backend/monitor_organization_performance.py"
    ]
    
    for critical_file in critical_files:
        critical_path = backend_root / critical_file
        if critical_path in existing_files:
            print(f"\n❌ ERROR: Critical file detected in deletion list: {critical_file}")
            print("This file should NOT be deleted. Aborting for safety.")
            return 1
    
    # Confirm deletion
    print(f"\n⚠️  WARNING: This will permanently delete {len(existing_files)} files!")
    print("These files are development artifacts and not needed in production.")
    print("The functionality has been integrated into the main codebase.")
    
    response = input("\nDo you want to proceed? (yes/no): ").lower().strip()
    
    if response not in ['yes', 'y']:
        print("❌ Cleanup cancelled by user")
        return 0
    
    # Create backup
    print("\n💾 Creating backup before deletion...")
    backup_path, backed_up = backup_files(existing_files, backend_root)
    
    if backed_up:
        print(f"✅ Backup created: {backup_path}")
        print(f"   Backed up {len(backed_up)} files")
    
    # Delete files
    print(f"\n🗑️  Deleting files...")
    deleted_count = 0
    errors = []
    
    for file_path in existing_files:
        try:
            relative_path = file_path.relative_to(backend_root)
            file_path.unlink()
            print(f"   ✅ Deleted: {relative_path}")
            deleted_count += 1
        except Exception as e:
            error_msg = f"Failed to delete {relative_path}: {e}"
            errors.append(error_msg)
            print(f"   ❌ {error_msg}")
    
    # Clean up empty directories
    print(f"\n📁 Cleaning up empty directories...")
    empty_dirs_removed = 0
    
    # Check for nested backend directory
    nested_backend = backend_root / "backend" / "backend"
    if nested_backend.exists() and nested_backend.is_dir():
        try:
            # Only remove if empty
            if not any(nested_backend.iterdir()):
                nested_backend.rmdir()
                print(f"   ✅ Removed empty directory: backend/backend")
                empty_dirs_removed += 1
            else:
                print(f"   ⚠️  Directory not empty: backend/backend")
        except Exception as e:
            print(f"   ❌ Could not remove directory backend/backend: {e}")
    
    # Summary
    print(f"\n" + "=" * 60)
    print(f"🎉 Cleanup Summary:")
    print(f"   Files deleted: {deleted_count}")
    print(f"   Directories removed: {empty_dirs_removed}")
    print(f"   Errors: {len(errors)}")
    
    if backed_up:
        print(f"   Backup location: {backup_path}")
    
    if errors:
        print(f"\n❌ Errors encountered:")
        for error in errors:
            print(f"   - {error}")
    
    if deleted_count > 0:
        print(f"\n✅ Phase 1-5 development files cleaned up successfully!")
        print(f"Production files preserved:")
        print(f"   - PRODUCTION_DEPLOYMENT_GUIDE.md")
        print(f"   - backend/migrate_to_organizations.py")
        print(f"   - backend/monitor_organization_performance.py")
        print(f"   - backend/open_webui/routers/health_check.py")
    
    return 0 if not errors else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Cleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)