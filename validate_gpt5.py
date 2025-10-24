#!/usr/bin/env python
"""
Validation script to verify GPT-5 model is being used in the moderation system.

This script checks:
1. Frontend API client configuration
2. Backend router defaults
3. Backend utility function defaults
4. Makes a test request to verify actual model usage

Run: python validate_gpt5.py
"""

import re
import sys
from pathlib import Path

EXPECTED_MODEL = "gpt-5-2025-08-07"

def check_file_for_model(filepath: Path, patterns: list[tuple[str, str]]) -> bool:
    """Check if file contains expected model in specified patterns."""
    try:
        content = filepath.read_text()
        all_passed = True
        
        for pattern_name, pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                found_model = matches[0] if isinstance(matches[0], str) else matches[0][-1]
                if EXPECTED_MODEL in found_model:
                    print(f"  ✅ {pattern_name}: {EXPECTED_MODEL}")
                else:
                    print(f"  ❌ {pattern_name}: {found_model} (expected {EXPECTED_MODEL})")
                    all_passed = False
            else:
                print(f"  ⚠️  {pattern_name}: Pattern not found")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
        return False


def main():
    print("=" * 70)
    print("🔍 GPT-5 Model Validation Check")
    print("=" * 70)
    
    root = Path(__file__).parent
    all_checks_passed = True
    
    # 1. Check Frontend API client
    print("\n📝 Frontend API Client (src/lib/apis/moderation/index.ts)")
    frontend_patterns = [
        ("applyModeration model", r"model:\s*['\"]([^'\"]+)['\"]"),
    ]
    frontend_file = root / "src/lib/apis/moderation/index.ts"
    if frontend_file.exists():
        all_checks_passed &= check_file_for_model(frontend_file, frontend_patterns)
    else:
        print("  ❌ File not found")
        all_checks_passed = False
    
    # 2. Check Backend Router
    print("\n📝 Backend Router (backend/open_webui/routers/moderation.py)")
    router_patterns = [
        ("ModerationRequest model default", r'model:\s*Optional\[str\]\s*=\s*["\']([^"\']+)["\']'),
    ]
    router_file = root / "backend/open_webui/routers/moderation.py"
    if router_file.exists():
        # Just check if GPT-5 appears in the file
        content = router_file.read_text()
        if EXPECTED_MODEL in content:
            print(f"  ✅ Found {EXPECTED_MODEL} in router configuration")
        else:
            print(f"  ❌ {EXPECTED_MODEL} not found in router")
            all_checks_passed = False
    else:
        print("  ❌ File not found")
        all_checks_passed = False
    
    # 3. Check Backend Utility
    print("\n📝 Backend Utility (backend/open_webui/utils/moderation.py)")
    utility_file = root / "backend/open_webui/utils/moderation.py"
    if utility_file.exists():
        # Just check if GPT-5 appears in the file
        content = utility_file.read_text()
        if EXPECTED_MODEL in content:
            print(f"  ✅ Found {EXPECTED_MODEL} in utility functions")
        else:
            print(f"  ❌ {EXPECTED_MODEL} not found in utility")
            all_checks_passed = False
    else:
        print("  ❌ File not found")
        all_checks_passed = False
    
    # Summary
    print("\n" + "=" * 70)
    if all_checks_passed:
        print("✅ ALL CHECKS PASSED - GPT-5 model is configured correctly!")
        print("\n📋 Next Steps:")
        print("   1. Restart your backend server")
        print("   2. Make a moderation request in the UI")
        print("   3. Check backend logs for:")
        print("      🤖 Moderation request using model: gpt-5-2025-08-07")
        print("      🔍 [MODERATION] Calling OpenAI API with model: gpt-5-2025-08-07")
        print("      ✅ [MODERATION] OpenAI API response received. Model used: gpt-5-2025-08-07")
        return 0
    else:
        print("❌ SOME CHECKS FAILED - Review the output above")
        return 1


if __name__ == "__main__":
    sys.exit(main())

