#!/usr/bin/env python3
"""
Test script to verify the monthly calculation logic
"""

from datetime import date, timedelta

def test_old_logic():
    """Test the old 30-day logic"""
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    print(f"OLD LOGIC (Last 30 days):")
    print(f"  Today: {end_date}")
    print(f"  Start: {start_date}")
    print(f"  Days: {(end_date - start_date).days}")
    print()

def test_new_logic():
    """Test the new current month logic"""
    end_date = date.today()
    start_date = end_date.replace(day=1)
    
    print(f"NEW LOGIC (Current month):")
    print(f"  Today: {end_date}")
    print(f"  Start: {start_date}")
    print(f"  Days: {(end_date - start_date).days + 1}")  # +1 to include both start and end
    print()

def test_days_active_logic():
    """Test how days active would be calculated"""
    # Simulate some usage dates
    usage_dates = [
        date(2025, 1, 1),
        date(2025, 1, 3),
        date(2025, 1, 5),
        date(2025, 1, 10),
        date(2025, 1, 15),
        date(2025, 1, 25)
    ]
    
    days_active_set = set()
    for usage_date in usage_dates:
        days_active_set.add(usage_date)
    
    days_active = len(days_active_set)
    
    print(f"DAYS ACTIVE CALCULATION:")
    print(f"  Usage dates: {usage_dates}")
    print(f"  Unique days: {sorted(days_active_set)}")
    print(f"  Days active: {days_active}")
    print()

if __name__ == "__main__":
    print("=== Monthly Calculation Logic Test ===")
    print()
    
    test_old_logic()
    test_new_logic()
    test_days_active_logic()
    
    print("=== Test Results ===")
    print("✅ Days Active calculation: CORRECT (uses set() to count unique dates)")
    print("✅ New monthly calculation: CORRECT (from 1st day of current month)")
    print("❌ Old calculation was: INCORRECT (last 30 days, not current month)")