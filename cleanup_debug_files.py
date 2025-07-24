#!/usr/bin/env python3
"""
Cleanup script for removing temporary debug files from usage tracking troubleshooting.
This script identifies and removes files that were created during debugging but are not part of the final solution.
"""

import os
import sys
from pathlib import Path

def get_files_to_remove():
    """Identify files that should be removed"""
    
    # Files created during debugging that are no longer needed
    debug_files_to_remove = [
        # Debugging scripts created during troubleshooting
        "debug_usage_simple.py",
        "fix_usage_tracking.py", 
        "check_system_status.py",
        "create_test_usage.py",
        "create_tables.py",
        
        # Documentation of debugging process (temporary)
        "fix_migration.md",
        
        # Duplicate/incorrect migration files
        "backend/open_webui/migrations/versions/a1b2c3d4e5f6_option1_fixed_schema.py",
        
        # Old debug file
        "remove_debug_files.py"
    ]
    
    # Check which files actually exist
    existing_files = []
    for file_path in debug_files_to_remove:
        if os.path.exists(file_path):
            existing_files.append(file_path)
            
    return existing_files

def get_files_to_keep():
    """Files that should be preserved as they are part of the solution"""
    
    keep_files = [
        # Core migration that implements the working solution
        "backend/open_webui/migrations/versions/e7f8g9h0i1j2_client_usage_tables.py",
        "backend/open_webui/migrations/versions/merge_heads_option1.py",
        
        # Updated router with usage recording
        "backend/open_webui/routers/openai.py",
        
        # Setup scripts for production
        "setup_client_org.py",
        "production-deployment.md",
        
        # Core backend models and utilities
        "backend/open_webui/models/organization_usage.py",
        "backend/open_webui/routers/client_organizations.py",
        "backend/open_webui/utils/openrouter_client_manager.py",
        
        # Frontend components
        "src/lib/components/admin/Settings/Usage.svelte",
        "src/lib/components/admin/Settings/MyOrganizationUsage.svelte",
        "src/lib/apis/organizations/index.ts"
    ]
    
    return keep_files

def show_cleanup_plan():
    """Display what will be removed and what will be kept"""
    
    files_to_remove = get_files_to_remove()
    files_to_keep = get_files_to_keep()
    
    print("🧹 Usage Tracking Debug Files Cleanup Plan")
    print("=" * 50)
    
    print(f"\n🗑️  Files to REMOVE ({len(files_to_remove)} files):")
    print("   These are temporary debugging files created during troubleshooting:")
    for file_path in files_to_remove:
        size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        print(f"   ❌ {file_path} ({size} bytes)")
    
    print(f"\n✅ Files to KEEP (core solution files):")
    print("   These are the working solution components:")
    for file_path in files_to_keep:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"   ✅ {file_path} ({size} bytes)")
        else:
            print(f"   ⚠️  {file_path} (not found - may be in different location)")
    
    print(f"\n📊 Summary:")
    print(f"   - Files to remove: {len(files_to_remove)}")
    print(f"   - Core solution files: {len([f for f in files_to_keep if os.path.exists(f)])}")
    
    if files_to_remove:
        total_size = sum(os.path.getsize(f) for f in files_to_remove if os.path.exists(f))
        print(f"   - Total size to free: {total_size:,} bytes")
    
    return files_to_remove

def cleanup_files(files_to_remove, dry_run=True):
    """Remove the debug files"""
    
    if not files_to_remove:
        print("✅ No files to remove!")
        return
    
    if dry_run:
        print(f"\n🔍 DRY RUN - Files that would be removed:")
        for file_path in files_to_remove:
            print(f"   - {file_path}")
        print(f"\nTo actually remove files, run: python3 {sys.argv[0]} --execute")
        return
    
    print(f"\n🗑️  Removing {len(files_to_remove)} debug files...")
    
    removed_count = 0
    failed_count = 0
    
    for file_path in files_to_remove:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"   ✅ Removed: {file_path}")
                removed_count += 1
            else:
                print(f"   ⚠️  Not found: {file_path}")
        except Exception as e:
            print(f"   ❌ Failed to remove {file_path}: {e}")
            failed_count += 1
    
    print(f"\n📊 Cleanup Results:")
    print(f"   - Successfully removed: {removed_count} files")
    if failed_count > 0:
        print(f"   - Failed to remove: {failed_count} files")
    
    print(f"\n✅ Cleanup complete!")

def verify_solution_intact():
    """Verify that the core solution files are still present"""
    
    critical_files = [
        "backend/open_webui/models/organization_usage.py",
        "backend/open_webui/routers/client_organizations.py", 
        "src/lib/components/admin/Settings/Usage.svelte"
    ]
    
    print(f"\n🔍 Verifying core solution files...")
    all_present = True
    
    for file_path in critical_files:
        if os.path.exists(file_path):
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ MISSING: {file_path}")
            all_present = False
    
    if all_present:
        print(f"   ✅ All critical solution files are present!")
    else:
        print(f"   ⚠️  Some critical files are missing - solution may be broken!")
    
    return all_present

def main():
    """Main cleanup function"""
    
    print("🚀 Starting debug files cleanup...")
    
    # Show what will be done
    files_to_remove = show_cleanup_plan()
    
    # Check if we should actually execute
    execute = len(sys.argv) > 1 and sys.argv[1] == "--execute"
    
    # Perform cleanup
    cleanup_files(files_to_remove, dry_run=not execute)
    
    # Verify solution is intact
    if execute:
        verify_solution_intact()
        
        print(f"\n🎉 Debug cleanup complete!")
        print(f"   The usage tracking system solution is preserved and ready.")
        print(f"   All temporary troubleshooting files have been removed.")
    
    return 0 if not files_to_remove or execute else 1

if __name__ == "__main__":
    exit(main())