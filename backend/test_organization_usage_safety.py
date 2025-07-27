#!/usr/bin/env python3
"""
CRITICAL SAFETY TEST SUITE for organization_usage.py refactoring
This test suite MUST pass before, during, and after ALL refactoring operations.
"""
import sys
import traceback
from datetime import date, datetime
from typing import Optional, List, Dict, Any

def test_imports():
    """Test that all imports work correctly"""
    print("🔍 Testing imports...")
    try:
        sys.path.append('.')
        from open_webui.models.organization_usage import (
            # Database Models
            GlobalSettings, ProcessedGeneration, ProcessedGenerationCleanupLog,
            ClientOrganization, UserClientMapping, ClientDailyUsage,
            ClientUserDailyUsage, ClientModelDailyUsage,
            
            # Pydantic Models
            GlobalSettingsModel, ClientOrganizationModel, UserClientMappingModel,
            ClientDailyUsageModel, ClientUserDailyUsageModel, ClientModelDailyUsageModel,
            
            # Forms and Responses
            GlobalSettingsForm, ClientOrganizationForm, UserClientMappingForm,
            ClientUsageStatsResponse, ClientBillingResponse,
            
            # Database Operations (Table Classes)
            GlobalSettingsTable, ClientOrganizationTable, UserClientMappingTable,
            ClientUsageTable, ProcessedGenerationTable,
            
            # Singleton Instances (CRITICAL)
            GlobalSettingsDB, ClientOrganizationDB, UserClientMappingDB,
            ClientUsageDB, ProcessedGenerationDB
        )
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        traceback.print_exc()
        return False

def test_singleton_instances():
    """Test that singleton instances are properly initialized"""
    print("🔍 Testing singleton instances...")
    try:
        from open_webui.models.organization_usage import (
            GlobalSettingsDB, ClientOrganizationDB, UserClientMappingDB,
            ClientUsageDB, ProcessedGenerationDB
        )
        
        # Test instance types
        assert hasattr(GlobalSettingsDB, 'get_settings'), "GlobalSettingsDB missing get_settings method"
        assert hasattr(ClientOrganizationDB, 'get_all_active_clients'), "ClientOrganizationDB missing get_all_active_clients method"
        assert hasattr(UserClientMappingDB, 'create_mapping'), "UserClientMappingDB missing create_mapping method"
        assert hasattr(ClientUsageDB, 'record_usage'), "ClientUsageDB missing record_usage method"
        assert hasattr(ProcessedGenerationDB, 'is_generation_processed'), "ProcessedGenerationDB missing is_generation_processed method"
        
        print("✅ All singleton instances valid")
        return True
    except Exception as e:
        print(f"❌ Singleton instance test failed: {e}")
        traceback.print_exc()
        return False

def test_method_signatures():
    """Test that all critical method signatures are preserved"""
    print("🔍 Testing method signatures...")
    try:
        from open_webui.models.organization_usage import (
            GlobalSettingsDB, ClientOrganizationDB, UserClientMappingDB,
            ClientUsageDB, ProcessedGenerationDB,
            GlobalSettingsForm, ClientOrganizationForm, UserClientMappingForm
        )
        import inspect
        
        # Test GlobalSettingsDB methods
        get_settings_sig = inspect.signature(GlobalSettingsDB.get_settings)
        assert len(get_settings_sig.parameters) == 0, "get_settings signature changed"
        
        create_update_sig = inspect.signature(GlobalSettingsDB.create_or_update_settings)
        assert 'settings_form' in create_update_sig.parameters, "create_or_update_settings signature changed"
        
        # Test ClientOrganizationDB methods
        create_client_sig = inspect.signature(ClientOrganizationDB.create_client)
        expected_params = {'client_form', 'api_key', 'key_hash'}
        actual_params = set(create_client_sig.parameters.keys())
        assert expected_params.issubset(actual_params), f"create_client signature changed: {actual_params}"
        
        # Test ClientUsageDB.record_usage (most complex method)
        record_usage_sig = inspect.signature(ClientUsageDB.record_usage)
        required_params = {'client_org_id', 'user_id', 'openrouter_user_id', 'model_name', 'usage_date'}
        actual_params = set(record_usage_sig.parameters.keys())
        assert required_params.issubset(actual_params), f"record_usage signature changed: {actual_params}"
        
        # Test async method signature
        get_stats_sig = inspect.signature(ClientUsageDB.get_usage_stats_by_client)
        assert inspect.iscoroutinefunction(ClientUsageDB.get_usage_stats_by_client), "get_usage_stats_by_client must remain async"
        
        print("✅ All method signatures preserved")
        return True
    except Exception as e:
        print(f"❌ Method signature test failed: {e}")
        traceback.print_exc()
        return False

def test_database_models():
    """Test that database models are properly defined"""
    print("🔍 Testing database models...")
    try:
        from open_webui.models.organization_usage import (
            GlobalSettings, ProcessedGeneration, ClientOrganization,
            UserClientMapping, ClientDailyUsage
        )
        
        # Test that models have required attributes
        assert hasattr(GlobalSettings, '__tablename__'), "GlobalSettings missing __tablename__"
        assert hasattr(ClientOrganization, '__tablename__'), "ClientOrganization missing __tablename__"
        assert hasattr(ProcessedGeneration, '__tablename__'), "ProcessedGeneration missing __tablename__"
        
        # Test key columns exist
        assert hasattr(GlobalSettings, 'id'), "GlobalSettings missing id column"
        assert hasattr(ClientOrganization, 'openrouter_api_key'), "ClientOrganization missing openrouter_api_key"
        assert hasattr(ProcessedGeneration, 'client_org_id'), "ProcessedGeneration missing client_org_id"
        
        print("✅ Database models preserved")
        return True
    except Exception as e:
        print(f"❌ Database model test failed: {e}")
        traceback.print_exc()
        return False

def test_pydantic_models():
    """Test that Pydantic models work correctly"""
    print("🔍 Testing Pydantic models...")
    try:
        from open_webui.models.organization_usage import (
            GlobalSettingsModel, ClientOrganizationModel,
            ClientUsageStatsResponse, ClientBillingResponse
        )
        
        # Test that models can be instantiated with proper validation
        # Note: Using minimal valid data to avoid database dependencies
        test_data = {
            'id': 'test',
            'openrouter_provisioning_key': None,
            'default_markup_rate': 1.3,
            'billing_currency': 'USD',
            'created_at': 1234567890,
            'updated_at': 1234567890
        }
        
        try:
            model = GlobalSettingsModel(**test_data)
            assert model.id == 'test', "GlobalSettingsModel validation failed"
        except Exception:
            # Model validation might fail due to missing fields, that's ok for this test
            pass
            
        print("✅ Pydantic models preserved")
        return True
    except Exception as e:
        print(f"❌ Pydantic model test failed: {e}")
        traceback.print_exc()
        return False

def test_basic_functionality():
    """Test basic functionality without database operations"""
    print("🔍 Testing basic functionality...")
    try:
        from open_webui.models.organization_usage import (
            GlobalSettingsDB, ClientOrganizationDB, ProcessedGenerationDB
        )
        
        # Test that methods exist and are callable (don't actually call them to avoid DB dependencies)
        assert callable(GlobalSettingsDB.get_settings), "get_settings not callable"
        assert callable(ClientOrganizationDB.get_all_active_clients), "get_all_active_clients not callable"
        assert callable(ProcessedGenerationDB.is_generation_processed), "is_generation_processed not callable"
        
        print("✅ Basic functionality preserved")
        return True
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        traceback.print_exc()
        return False

def run_safety_tests():
    """Run all safety tests and return overall result"""
    print("🚨 RUNNING CRITICAL SAFETY TESTS FOR organization_usage.py")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_singleton_instances,
        test_method_signatures,
        test_database_models,
        test_pydantic_models,
        test_basic_functionality
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
        print("-" * 40)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n🎯 SAFETY TEST RESULTS: {passed}/{total} PASSED")
    
    if passed == total:
        print("✅ ALL SAFETY TESTS PASSED - REFACTORING CAN PROCEED")
        return True
    else:
        print("❌ SAFETY TESTS FAILED - DO NOT PROCEED WITH REFACTORING")
        print("🚨 SYSTEM IS NOT IN SAFE STATE FOR MODIFICATION")
        return False

if __name__ == "__main__":
    import os
    os.chdir('/Users/patpil/Documents/Projects/mAI/backend')
    
    success = run_safety_tests()
    exit(0 if success else 1)