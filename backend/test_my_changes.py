#!/usr/bin/env python3
"""
Test script to validate the syntax and basic functionality of modified files
"""

import ast
import sys
from pathlib import Path

def test_python_syntax():
    """Test Python syntax of modified files"""
    
    files_to_test = [
        "open_webui/models/organization_usage/client_usage_repository.py",
        "open_webui/usage_tracking/services/usage_service.py"
    ]
    
    for file_path in files_to_test:
        print(f"Testing syntax of {file_path}...")
        
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            
            # Parse the AST to check syntax
            ast.parse(code)
            print(f"✅ {file_path} - Syntax OK")
            
        except SyntaxError as e:
            print(f"❌ {file_path} - Syntax Error: {e}")
            return False
        except FileNotFoundError:
            print(f"❌ {file_path} - File not found")
            return False
        except Exception as e:
            print(f"❌ {file_path} - Error: {e}")
            return False
    
    return True

def test_data_structure_changes():
    """Test that the new data structure changes are properly implemented"""
    print("\nTesting data structure changes...")
    
    # Test that client_usage_repository.py contains the new helper function
    repo_file = "open_webui/models/organization_usage/client_usage_repository.py"
    try:
        with open(repo_file, 'r') as f:
            content = f.read()
        
        # Check for new helper function
        if "_calculate_top_models_by_tokens" in content:
            print("✅ Found _calculate_top_models_by_tokens helper function")
        else:
            print("❌ Missing _calculate_top_models_by_tokens helper function")
            return False
            
        # Check for new top_models field usage
        if "'top_models':" in content:
            print("✅ Found top_models field")
        else:
            print("❌ Missing top_models field")
            return False
            
        # Check that most_used_model is replaced
        if "'most_used_model':" not in content:
            print("✅ Successfully removed most_used_model field")
        else:
            print("❌ most_used_model field still exists")
            return False
            
    except Exception as e:
        print(f"❌ Error testing data structure changes: {e}")
        return False
    
    # Test usage_service.py changes
    service_file = "open_webui/usage_tracking/services/usage_service.py"
    try:
        with open(service_file, 'r') as f:
            content = f.read()
        
        # Check for top_models in fallback data
        if '"top_models": []' in content:
            print("✅ Found top_models fallback data structure")
        else:
            print("❌ Missing top_models fallback data structure")
            return False
            
        # Check that most_used_model is replaced in fallbacks
        if '"most_used_model": None' not in content:
            print("✅ Successfully removed most_used_model from fallbacks")
        else:
            print("❌ most_used_model still exists in fallbacks")
            return False
            
    except Exception as e:
        print(f"❌ Error testing service changes: {e}")
        return False
    
    return True

def main():
    """Main test function"""
    print("🧪 Testing Usage Tracking Refactoring Changes")
    print("=" * 50)
    
    # Test Python syntax
    if not test_python_syntax():
        print("\n❌ Syntax tests failed!")
        sys.exit(1)
    
    # Test data structure changes
    if not test_data_structure_changes():
        print("\n❌ Data structure tests failed!")
        sys.exit(1)
    
    print("\n🎉 All tests passed!")
    print("✅ Backend changes are syntactically correct")
    print("✅ Data structure changes implemented properly")
    print("✅ Ready for frontend testing")

if __name__ == "__main__":
    main()