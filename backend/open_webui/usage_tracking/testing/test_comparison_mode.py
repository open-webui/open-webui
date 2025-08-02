#!/usr/bin/env python3
"""
Test script to verify InfluxDB vs SQLite comparison mode
"""
import asyncio
import sys
import os
from datetime import date, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from open_webui.utils.influxdb_sqlite_comparison import DataConsistencyValidator


async def test_comparison_mode():
    """Test the comparison mode functionality"""
    print("Testing InfluxDB vs SQLite Comparison Mode")
    print("=" * 50)
    
    validator = DataConsistencyValidator()
    
    # Test 1: Validate today's data
    print("\n1. Testing today's data validation:")
    today = date.today()
    try:
        report = await validator.run_comprehensive_validation(today, today)
        
        if report["success"]:
            print(f"   ✅ Validation successful")
            print(f"   Days checked: {report['summary']['days_checked']}")
            print(f"   Total discrepancies: {report['summary']['total_discrepancies']}")
            print(f"   Clients checked: {len(report['client_summaries'])}")
        else:
            print(f"   ❌ Validation failed: {report.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"   ❌ Error during validation: {e}")
    
    # Test 2: Generate a week's report
    print("\n2. Testing weekly report generation:")
    try:
        report_path = await validator.generate_discrepancy_report(
            "test_validation_report.md",
            days_back=3  # Just 3 days for testing
        )
        print(f"   ✅ Report generated: {report_path}")
        
        # Show first few lines of the report
        with open(report_path, 'r') as f:
            lines = f.readlines()[:20]
            print("\n   Report preview:")
            for line in lines:
                print(f"   {line.rstrip()}")
    except Exception as e:
        print(f"   ❌ Error generating report: {e}")
    
    # Test 3: Check specific date range
    print("\n3. Testing specific date range:")
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=2)
    
    try:
        report = await validator.run_comprehensive_validation(start_date, end_date)
        
        if report["success"]:
            print(f"   ✅ Date range validation successful")
            print(f"   Period: {start_date} to {end_date}")
            
            # Show recommendations
            print("\n   Recommendations:")
            for rec in report.get("recommendations", []):
                print(f"   - {rec}")
                
            # Show any discrepancies found
            total_disc = report["summary"]["total_discrepancies"]
            if total_disc > 0:
                print(f"\n   Found {total_disc} discrepancies across {report['summary']['days_checked']} days")
                print(f"   Affected clients: {report['summary']['clients_with_discrepancies']}")
                print(f"   Affected models: {report['summary']['models_with_discrepancies']}")
        else:
            print(f"   ❌ Validation failed: {report.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"   ❌ Error during date range validation: {e}")
    
    print("\n✅ Comparison mode testing complete!")


if __name__ == "__main__":
    asyncio.run(test_comparison_mode())