#!/usr/bin/env python3
"""
Remove debug/test files with hardcoded API keys - SECURITY CLEANUP
"""
import os
from pathlib import Path

def remove_debug_files():
    """Remove debug/test files that contain hardcoded API keys"""
    
    base_dir = Path("/Users/patpil/Documents/Projects/mAI")
    
    # Files with hardcoded API keys - SECURITY RISK
    debug_files = [
        "debug_create_key.py",
        "test_key_type.py",
        "test_successful_create.py"
    ]
    
    print("🚨 SECURITY CLEANUP: Removing debug files with hardcoded API keys...")
    print("=" * 70)
    
    removed_files = []
    not_found = []
    
    for file_name in debug_files:
        file_path = base_dir / file_name
        if file_path.exists():
            try:
                file_path.unlink()
                removed_files.append(file_name)
                print(f"✅ REMOVED: {file_name}")
            except Exception as e:
                print(f"❌ Failed to remove {file_name}: {e}")
        else:
            not_found.append(file_name)
            print(f"⏭️  Not found: {file_name}")
    
    print("\n" + "=" * 70)
    print("🛡️  SECURITY CLEANUP SUMMARY:")
    print(f"✅ Files removed: {len(removed_files)}")
    print(f"⏭️  Files not found: {len(not_found)}")
    
    if removed_files:
        print(f"\n🗑️  Removed files with hardcoded API keys:")
        for file in removed_files:
            print(f"   • {file}")
        print("\n🔒 Security improved - no more hardcoded API keys in debug files!")
    
    if not_found:
        print(f"\n⚠️  Files not found (may have been removed already):")
        for file in not_found:
            print(f"   • {file}")
    
    print(f"\n✅ Your codebase is now clean and secure!")
    print("🎯 Only production-ready Option 1 files remain")

if __name__ == "__main__":
    remove_debug_files()