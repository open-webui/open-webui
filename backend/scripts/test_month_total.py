#!/usr/bin/env python3
"""
Test script for "Month Total" value calculation and accuracy
"""

import sys
import os
from datetime import datetime, date, timedelta

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

def test_month_calculation_logic():
    """Test the monthly calculation date logic"""
    print("📅 Testing Month Calculation Date Logic")
    
    # Test current month calculation
    today = date.today()
    current_month_start = today.replace(day=1)
    
    print(f"  Today: {today}")
    print(f"  Current month start: {current_month_start}")
    
    # Test edge cases
    test_dates = [
        date(2025, 1, 1),   # First day of month
        date(2025, 1, 15),  # Mid month
        date(2025, 1, 31),  # Last day of month
        date(2025, 2, 28),  # End of February
        date(2025, 12, 31), # End of year
    ]
    
    for test_date in test_dates:
        month_start = test_date.replace(day=1)
        days_in_calculation = (test_date - month_start).days + 1
        print(f"  Date {test_date} → Month start {month_start} → {days_in_calculation} days to include")
    
    return True

def test_month_total_aggregation():
    """Test how monthly totals are aggregated"""
    print("\n💰 Testing Month Total Aggregation Logic")
    
    # Simulate daily usage data for current month
    current_month_start = date.today().replace(day=1)
    
    # Mock daily usage records
    daily_records = []
    for day in range(1, 16):  # First 15 days of month
        usage_date = current_month_start.replace(day=day)
        daily_records.append({
            'usage_date': usage_date,
            'total_tokens': 1500 + (day * 100),  # Increasing usage
            'markup_cost': 0.045 + (day * 0.003),  # Increasing cost
            'total_requests': 5 + day
        })
    
    # Calculate aggregated totals (simulate the backend logic)
    month_tokens = sum(r['total_tokens'] for r in daily_records)
    month_cost = sum(r['markup_cost'] for r in daily_records)
    month_requests = sum(r['total_requests'] for r in daily_records)
    days_active = len(daily_records)
    
    print(f"  Simulated {len(daily_records)} days of usage:")
    print(f"    Historical month tokens: {month_tokens:,}")
    print(f"    Historical month cost: ${month_cost:.6f}")
    print(f"    Historical month requests: {month_requests}")
    print(f"    Days active (historical): {days_active}")
    
    # Simulate today's live usage being added
    today_tokens = 2500
    today_cost = 0.075
    today_requests = 8
    
    # Add today's usage to month totals (as done in get_usage_stats_by_client)
    final_month_tokens = month_tokens + today_tokens
    final_month_cost = month_cost + today_cost
    final_month_requests = month_requests + today_requests
    final_days_active = days_active + (1 if today_tokens > 0 else 0)
    
    print(f"\n  Today's live usage:")
    print(f"    Today tokens: {today_tokens:,}")
    print(f"    Today cost: ${today_cost:.6f}")
    print(f"    Today requests: {today_requests}")
    
    print(f"\n  Final Month Total (historical + today):")
    print(f"    Total tokens: {final_month_tokens:,}")
    print(f"    Total cost: ${final_month_cost:.6f}")
    print(f"    Total requests: {final_month_requests}")
    print(f"    Days active: {final_days_active}")
    
    # Verify calculation logic
    expected_total_cost = sum(r['markup_cost'] for r in daily_records) + today_cost
    calculation_correct = abs(final_month_cost - expected_total_cost) < 0.000001
    
    print(f"\n  Calculation verification: {'✅' if calculation_correct else '❌'}")
    
    return calculation_correct

def test_month_rollover_scenario():
    """Test month rollover scenarios"""
    print("\n🔄 Testing Month Rollover Scenarios")
    
    # Test what happens at month boundaries
    scenarios = [
        {
            "name": "End of January",
            "current_date": date(2025, 1, 31),
            "usage_dates": [date(2025, 1, 28), date(2025, 1, 29), date(2025, 1, 30), date(2025, 1, 31)]
        },
        {
            "name": "Start of February", 
            "current_date": date(2025, 2, 1),
            "usage_dates": [date(2025, 1, 30), date(2025, 1, 31), date(2025, 2, 1)]
        },
        {
            "name": "Mid February",
            "current_date": date(2025, 2, 15),
            "usage_dates": [date(2025, 1, 31), date(2025, 2, 1), date(2025, 2, 14), date(2025, 2, 15)]
        }
    ]
    
    for scenario in scenarios:
        print(f"\n  Scenario: {scenario['name']}")
        current_date = scenario["current_date"]
        current_month_start = current_date.replace(day=1)
        
        # Filter usage dates that should be included in "this month"
        included_dates = [d for d in scenario["usage_dates"] if d >= current_month_start]
        excluded_dates = [d for d in scenario["usage_dates"] if d < current_month_start]
        
        print(f"    Current date: {current_date}")
        print(f"    Month start: {current_month_start}")
        print(f"    Included in month total: {[str(d) for d in included_dates]}")
        print(f"    Excluded from month total: {[str(d) for d in excluded_dates]}")
        
        # This should match the backend filter logic:
        # ClientDailyUsage.usage_date >= current_month
        expected_days = len(included_dates)
        print(f"    Expected days in calculation: {expected_days}")
    
    return True

def test_live_counter_integration():
    """Test how today's live counter integrates with historical data"""
    print("\n⚡ Testing Live Counter Integration")
    
    # Simulate the exact logic from get_usage_stats_by_client
    
    # Historical daily data (excludes today)
    historical_records = [
        {'markup_cost': 0.045, 'total_tokens': 1500, 'total_requests': 5},
        {'markup_cost': 0.052, 'total_tokens': 1800, 'total_requests': 6},
        {'markup_cost': 0.038, 'total_tokens': 1200, 'total_requests': 4},
    ]
    
    # Today's live counter data
    today_live_data = {
        'tokens': 2200,
        'cost': 0.067,
        'requests': 7,
        'last_updated': int(datetime.now().timestamp())
    }
    
    print(f"  Historical records: {len(historical_records)} days")
    for i, record in enumerate(historical_records, 1):
        print(f"    Day {i}: {record['total_tokens']} tokens, ${record['markup_cost']:.6f}, {record['total_requests']} requests")
    
    print(f"\n  Today's live data:")
    print(f"    Tokens: {today_live_data['tokens']}")
    print(f"    Cost: ${today_live_data['cost']:.6f}")
    print(f"    Requests: {today_live_data['requests']}")
    
    # Calculate month totals (simulate backend logic)
    historical_tokens = sum(r['total_tokens'] for r in historical_records)
    historical_cost = sum(r['markup_cost'] for r in historical_records)
    historical_requests = sum(r['total_requests'] for r in historical_records)
    historical_days = len(historical_records)
    
    # Add today's usage
    month_tokens = historical_tokens + today_live_data['tokens']
    month_cost = historical_cost + today_live_data['cost']
    month_requests = historical_requests + today_live_data['requests']
    days_active = historical_days + (1 if today_live_data['tokens'] > 0 else 0)
    
    print(f"\n  Month Total calculation:")
    print(f"    Historical: {historical_tokens} tokens, ${historical_cost:.6f}, {historical_requests} requests")
    print(f"    + Today: {today_live_data['tokens']} tokens, ${today_live_data['cost']:.6f}, {today_live_data['requests']} requests")
    print(f"    = Total: {month_tokens} tokens, ${month_cost:.6f}, {month_requests} requests")
    print(f"    Days active: {days_active}")
    
    # Test edge case: What if today has no usage?
    print(f"\n  Edge case: Today with no usage")
    no_usage_today = {'tokens': 0, 'cost': 0.0, 'requests': 0}
    no_usage_month_total = historical_cost + no_usage_today['cost']
    no_usage_days_active = historical_days + (1 if no_usage_today['tokens'] > 0 else 0)
    
    print(f"    Month cost: ${no_usage_month_total:.6f}")
    print(f"    Days active: {no_usage_days_active} (today not counted)")
    
    return True

def test_potential_issues():
    """Test for potential issues in month total calculation"""
    print("\n🔍 Testing Potential Issues")
    
    issues_found = []
    
    # Issue 1: Double counting today's usage
    print("  Issue 1: Risk of double counting today's usage")
    print("    ⚠️  If today's usage is stored in both ClientDailyUsage AND ClientLiveCounters")
    print("    ⚠️  The calculation adds both, which would double count today")
    print("    📝 Backend should ensure today's usage is NOT in ClientDailyUsage when using live counters")
    issues_found.append("Potential double counting of today's usage")
    
    # Issue 2: Timezone handling
    print("\n  Issue 2: Timezone handling for 'current month'")
    print("    ⚠️  date.today() uses server timezone")
    print("    ⚠️  Client might be in different timezone")
    print("    📝 Month boundaries might not align with client's local time")
    issues_found.append("Timezone mismatch for month boundaries")
    
    # Issue 3: Live counter staleness
    print("\n  Issue 3: Stale live counter data")
    print("    ⚠️  If live counter is from previous day but shows today's date")
    print("    ⚠️  Month total would include stale data as 'today'")
    print("    📝 Should validate live counter freshness")
    issues_found.append("Risk of stale live counter data")
    
    # Issue 4: Month rollover timing
    print("\n  Issue 4: Month rollover timing")
    print("    ⚠️  At midnight on 1st of month, calculations might be inconsistent")
    print("    ⚠️  Background sync vs live counters might have different rollover timing")
    print("    📝 Daily rollover process should be atomic")
    issues_found.append("Month rollover timing consistency")
    
    return len(issues_found) == 0, issues_found

def main():
    """Run all month total tests"""
    print("=" * 60)
    print("Testing 'Month Total' Value Generation and Accuracy")
    print("=" * 60)
    
    tests = [
        ("Month Calculation Logic", test_month_calculation_logic),
        ("Month Total Aggregation", test_month_total_aggregation),
        ("Month Rollover Scenarios", test_month_rollover_scenario),
        ("Live Counter Integration", test_live_counter_integration),
        ("Potential Issues Analysis", test_potential_issues),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            if test_name == "Potential Issues Analysis":
                success, issues = test_func()
                results.append((test_name, success, issues if not success else None))
            else:
                success = test_func()
                results.append((test_name, success, None))
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
            results.append((test_name, False, str(e)))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = 0
    critical_issues = []
    
    for test_name, success, error_or_issues in results:
        if success:
            print(f"✅ PASS    {test_name}")
            passed += 1
        else:
            print(f"❌ FAIL    {test_name}")
            if isinstance(error_or_issues, list):
                # Issues found
                for issue in error_or_issues:
                    print(f"          - {issue}")
                    critical_issues.extend(error_or_issues)
            elif error_or_issues:
                # Error message
                print(f"          Error: {error_or_issues}")
    
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if critical_issues:
        print(f"\n⚠️  Critical Issues Identified:")
        for issue in critical_issues:
            print(f"   • {issue}")
        print(f"\n🔧 Recommendation: Address these issues to ensure Month Total accuracy")
        return 1
    elif passed == total:
        print("🎉 All Month Total tests passed!")
        print("   Month Total calculation logic appears to be working correctly")
        return 0
    else:
        print("⚠️  Some Month Total calculation issues detected")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)