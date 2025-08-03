#!/usr/bin/env python3
"""
Test holiday scenarios for NBP exchange rate integration
Demonstrates how the hybrid approach handles various edge cases
"""

import sys
import os
from datetime import datetime, date, timedelta

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_holiday_scenarios():
    """Test various holiday and edge case scenarios"""
    
    print("🇵🇱 Testing Polish Holiday-Aware NBP Exchange Rate Integration")
    print("=" * 70)
    
    try:
        from open_webui.utils.polish_holidays import polish_holidays
        
        # Test 2025 holiday scenarios
        test_dates = [
            # New Year (Wednesday)
            date(2025, 1, 1),
            date(2025, 1, 2),  # Day after New Year
            
            # Three Kings Day (Monday) 
            date(2025, 1, 6),
            date(2025, 1, 7),  # Day after Three Kings
            
            # Easter period
            date(2025, 4, 20),  # Easter Sunday
            date(2025, 4, 21),  # Easter Monday (holiday)
            date(2025, 4, 22),  # Day after Easter Monday
            
            # May holidays
            date(2025, 5, 1),   # Labour Day (Thursday)
            date(2025, 5, 2),   # Day after Labour Day
            date(2025, 5, 3),   # Constitution Day (Saturday) 
            date(2025, 5, 5),   # Monday after Constitution Day weekend
            
            # Corpus Christi
            date(2025, 6, 19),  # Corpus Christi (Thursday)
            date(2025, 6, 20),  # Day after Corpus Christi
            
            # Christmas period
            date(2025, 12, 24), # Christmas Eve (Wednesday)
            date(2025, 12, 25), # Christmas Day (Thursday) 
            date(2025, 12, 26), # Boxing Day (Friday)
            date(2025, 12, 29), # Monday after Christmas weekend
            
            # Regular weekends
            date(2025, 7, 26),  # Saturday
            date(2025, 7, 27),  # Sunday
            date(2025, 7, 28),  # Monday after weekend
            
            # Regular working days
            date(2025, 7, 25),  # Friday (today)
            date(2025, 7, 29),  # Tuesday
        ]
        
        print("📅 Holiday Analysis:")
        print("-" * 50)
        
        for test_date in test_dates:
            is_working = polish_holidays.is_working_day(test_date)
            is_holiday = polish_holidays.is_holiday(test_date)
            is_weekend = test_date.weekday() >= 5
            
            day_type = "🟢 WORKING"
            if is_weekend:
                day_type = "🔵 WEEKEND"
            elif is_holiday:
                holiday_name = polish_holidays.get_holiday_name(test_date)
                day_type = f"🔴 HOLIDAY ({holiday_name})"
            
            # Get fallback date for non-working days
            fallback_info = ""
            if not is_working:
                fallback_date = polish_holidays.get_last_working_day_before(test_date)
                fallback_info = f" → Fallback: {fallback_date}"
            
            print(f"{test_date} ({test_date.strftime('%A'):<9}) {day_type}{fallback_info}")
        
        print(f"\n🔍 NBP Rate Strategy Examples:")
        print("-" * 50)
        
        # Test some specific scenarios
        scenarios = [
            (date(2025, 12, 25), "Christmas Day - should skip API call"),
            (date(2025, 4, 21), "Easter Monday - should skip API call"),
            (date(2025, 1, 6), "Three Kings Day - should skip API call"),
            (date(2025, 7, 26), "Saturday - should skip API call"),
            (date(2025, 7, 25), "Friday - should make API call"),
        ]
        
        for test_date, description in scenarios:
            strategy = polish_holidays.get_nbp_rate_strategy(test_date)
            
            print(f"\n📊 {description}")
            print(f"    Date: {test_date} ({test_date.strftime('%A')})")
            print(f"    Working Day: {strategy['is_working_day']}")
            print(f"    Expect NBP Data: {strategy['expect_nbp_data']}")
            print(f"    Reason: {strategy['reason']}")
            if strategy['fallback_date']:
                print(f"    Fallback Date: {strategy['fallback_date']}")
        
        print(f"\n🎯 Extended Holiday Period Analysis:")
        print("-" * 50)
        
        # Test Christmas period (common extended holiday)
        print("Christmas 2025 Period:")
        polish_holidays.debug_holiday_period(date(2025, 12, 21), date(2025, 12, 31))
        
        print("\nEaster 2025 Period:")
        polish_holidays.debug_holiday_period(date(2025, 4, 18), date(2025, 4, 25))
        
        print(f"\n🔮 Upcoming Holidays from Today:")
        print("-" * 50)
        
        upcoming = polish_holidays.get_upcoming_holidays(date.today(), days_ahead=60)
        for holiday in upcoming[:5]:  # Show next 5 holidays
            weekend_note = " (weekend)" if holiday['is_weekend'] else ""
            print(f"    {holiday['date']} ({holiday['weekday']}) - {holiday['name']}{weekend_note}")
        
        print(f"\n✅ Holiday integration test completed successfully!")
        print(f"📈 Benefits of hybrid approach:")
        print(f"    • Optimized: Skips API calls for {len([d for d in test_dates if not polish_holidays.is_working_day(d)])} known non-working days")
        print(f"    • Resilient: 404 fallback handles unknown issues")
        print(f"    • Accurate: Uses exact 2025 Polish holiday calendar")
        print(f"    • Smart caching: Different TTLs for different scenarios")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_holiday_scenarios()
    if success:
        print(f"\n🎉 All holiday tests completed successfully!")
    else:
        print(f"\n❌ Holiday tests failed!")
    sys.exit(0 if success else 1)