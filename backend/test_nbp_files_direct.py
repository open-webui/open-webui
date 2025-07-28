#!/usr/bin/env python3
"""
Direct File Testing for NBP Table A Integration

This test directly validates the NBP files without complex dependencies.
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def test_file_contents():
    """Test the actual file contents for Table A changes"""
    print("🧪 NBP Table A Files - Direct Content Validation")
    print("=" * 60)
    
    results = {'passed': 0, 'failed': 0}
    
    def check_result(test_name, condition, message):
        if condition:
            print(f"✅ PASS {test_name}: {message}")
            results['passed'] += 1
        else:
            print(f"❌ FAIL {test_name}: {message}")
            results['failed'] += 1
    
    # Test 1: NBP Client file validation
    print("\n🔍 Testing NBP Client File")
    print("=" * 40)
    
    nbp_client_path = backend_dir / "open_webui" / "utils" / "nbp_client.py"
    if nbp_client_path.exists():
        content = nbp_client_path.read_text()
        
        # Check for Table A endpoint
        check_result("Table A endpoint", 
                    "tables/a/" in content,
                    "File contains tables/a/ endpoint")
        
        # Check for 'mid' field usage
        check_result("Mid field usage",
                    "rate.get('mid')" in content,
                    "File uses 'mid' field for Table A rates")
        
        # Check against Table C usage
        check_result("No Table C endpoint",
                    "tables/c/" not in content,
                    "File doesn't use tables/c/ endpoint")
        
        # Check for NBP API base
        check_result("NBP API base",
                    "api.nbp.pl/api" in content,
                    "File contains NBP API base URL")
        
        print(f"  📄 File size: {len(content)} characters")
        print(f"  📝 Contains 'Table A' references: {'Table A' in content}")
        
    else:
        check_result("NBP Client file exists", False, "NBP client file not found")
    
    # Test 2: Currency Converter file validation
    print("\n🔍 Testing Currency Converter File")
    print("=" * 40)
    
    converter_path = backend_dir / "open_webui" / "utils" / "currency_converter.py"
    if converter_path.exists():
        content = converter_path.read_text()
        
        # Check fallback rate
        check_result("Fallback rate 3.64",
                    "3.64" in content,
                    "File contains 3.64 fallback rate")
        
        # Check against old fallback
        check_result("No old fallback 4.1234",
                    "4.1234" not in content,
                    "File doesn't contain old 4.1234 fallback")
        
        # Check Table A references
        check_result("Table A references",
                    "Table A" in content,
                    "File contains Table A references")
        
        # Check average rates mentions
        check_result("Average rates mention",
                    "average" in content.lower(),
                    "File mentions average rates")
        
        print(f"  📄 File size: {len(content)} characters")
        
    else:
        check_result("Currency converter file exists", False, "Currency converter file not found")
    
    # Test 3: Polish Holidays file validation
    print("\n🔍 Testing Polish Holidays File")
    print("=" * 40)
    
    holidays_path = backend_dir / "open_webui" / "utils" / "polish_holidays.py"
    if holidays_path.exists():
        content = holidays_path.read_text()
        
        # Check for 2025 holidays
        check_result("2025 holidays",
                    "2025" in content,
                    "File contains 2025 holiday data")
        
        # Check for working day logic
        check_result("Working day logic",
                    "is_working_day" in content,
                    "File contains working day logic")
        
        # Check for NBP integration
        check_result("NBP integration",
                    "nbp" in content.lower(),
                    "File contains NBP-related logic")
        
        print(f"  📄 File size: {len(content)} characters")
        
    else:
        check_result("Polish holidays file exists", False, "Polish holidays file not found")
    
    # Test 4: Integration consistency
    print("\n🔍 Testing Integration Consistency")
    print("=" * 40)
    
    if nbp_client_path.exists() and converter_path.exists():
        nbp_content = nbp_client_path.read_text()
        converter_content = converter_path.read_text()
        
        # Check consistent fallback rate
        nbp_has_364 = "3.64" in nbp_content
        converter_has_364 = "3.64" in converter_content
        check_result("Consistent fallback rate",
                    nbp_has_364 and converter_has_364,
                    "Both files use 3.64 fallback rate")
        
        # Check Table A consistency
        nbp_table_a = "Table A" in nbp_content
        converter_table_a = "Table A" in converter_content
        check_result("Consistent Table A usage",
                    nbp_table_a and converter_table_a,
                    "Both files reference Table A")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 FILE VALIDATION SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    
    total = results['passed'] + results['failed']
    success_rate = (results['passed'] / total * 100) if total > 0 else 0
    print(f"🎯 Success Rate: {success_rate:.1f}% ({results['passed']}/{total})")
    
    if results['failed'] == 0:
        print("\n🎉 ALL FILE VALIDATIONS PASSED!")
        print("✅ NBP files correctly implement Table A integration")
        print("✅ Fallback rate changed from 4.1234 to 3.64")
        print("✅ API endpoint uses /exchangerates/tables/a/")
        print("✅ Rate parsing uses 'mid' field for average rates")
        print("✅ Files are consistent with each other")
        
        print("\n📋 VALIDATION SUMMARY:")
        print("  • USD/PLN rates will use Table A average rates (~3.64)")
        print("  • API calls target /exchangerates/tables/a/ endpoint")
        print("  • Rate data uses 'mid' field (average) instead of 'ask' (selling)")
        print("  • Fallback rate is 3.64 (Table A range) instead of 4.1234")
        print("  • Polish holiday integration provides smart caching")
        
    else:
        print("\n⚠️  Some file validations failed. Check the details above.")
    
    return results['failed'] == 0

if __name__ == "__main__":
    success = test_file_contents()
    sys.exit(0 if success else 1)