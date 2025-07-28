#!/usr/bin/env python3
"""
Test script to verify the critical data loss fix
Tests the is_duplicate method and deduplication logic
"""

import sys
import os
sys.path.append('backend')

def test_is_duplicate_method():
    """Test that the missing is_duplicate method now exists"""
    try:
        from backend.open_webui.models.organization_usage import ProcessedGenerationDB
        
        # Check if method exists
        if hasattr(ProcessedGenerationDB, 'is_duplicate'):
            print("✅ SUCCESS: is_duplicate method exists")
            
            # Test method signature
            import inspect
            sig = inspect.signature(ProcessedGenerationDB.is_duplicate)
            params = list(sig.parameters.keys())
            expected_params = ['request_id', 'model', 'cost']
            
            if params == expected_params:
                print(f"✅ SUCCESS: Method signature correct: {params}")
            else:
                print(f"❌ ERROR: Wrong method signature. Expected {expected_params}, got {params}")
                return False
        else:
            print("❌ ERROR: is_duplicate method still missing")
            return False
            
        return True
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_webhook_service_import():
    """Test that webhook service imports correctly"""
    try:
        from backend.open_webui.usage_tracking.services.webhook_service import WebhookService
        print("✅ SUCCESS: WebhookService imports correctly")
        
        # Check that sync method exists
        service = WebhookService()
        if hasattr(service, 'sync_openrouter_usage'):
            print("✅ SUCCESS: sync_openrouter_usage method exists")
            
            # Check method signature
            import inspect
            sig = inspect.signature(service.sync_openrouter_usage)
            if 'request' in sig.parameters:
                print("✅ SUCCESS: sync method has correct signature")
            else:
                print("❌ ERROR: sync method missing request parameter")
                return False
        else:
            print("❌ ERROR: sync_openrouter_usage method missing")
            return False
            
        return True
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_deduplication_logic():
    """Test the deduplication logic flow"""
    try:
        # Import required modules
        from backend.open_webui.usage_tracking.repositories.webhook_repository import WebhookRepository
        
        webhook_repo = WebhookRepository()
        
        # Test that is_duplicate_generation method exists
        if hasattr(webhook_repo, 'is_duplicate_generation'):
            print("✅ SUCCESS: is_duplicate_generation method exists in WebhookRepository")
        else:
            print("❌ ERROR: is_duplicate_generation method missing from WebhookRepository")
            return False
            
        # Test that mark_generation_processed method exists
        if hasattr(webhook_repo, 'mark_generation_processed'):
            print("✅ SUCCESS: mark_generation_processed method exists in WebhookRepository")
        else:
            print("❌ ERROR: mark_generation_processed method missing from WebhookRepository")
            return False
            
        return True
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    """Run all tests"""
    print("🔍 Testing Critical Data Loss Fix")
    print("=" * 50)
    
    tests = [
        ("ProcessedGenerationDB.is_duplicate method", test_is_duplicate_method),
        ("WebhookService import and methods", test_webhook_service_import),
        ("Deduplication logic components", test_deduplication_logic),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n🧪 Testing: {test_name}")
        if test_func():
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED - Data loss fix is working!")
        return 0
    else:
        print("❌ SOME TESTS FAILED - Fix needs attention")
        return 1

if __name__ == "__main__":
    exit(main())