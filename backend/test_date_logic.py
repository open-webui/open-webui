#!/usr/bin/env python3
"""
Test script to debug the date range calculation used in get_usage_by_user
"""
from datetime import date

def test_current_month_logic():
    """Test the date range calculation logic used in the API"""
    
    # This mimics the logic in get_usage_by_user method
    end_date = date.today()
    start_date = end_date.replace(day=1)  # First day of current month
    
    print(f"Today: {date.today()}")
    print(f"Current month start: {start_date}")
    print(f"Current month end (today): {end_date}")
    print(f"Date range: {start_date} to {end_date}")
    
    # Check if the data we found (2025-07-27) falls in this range
    data_date = date(2025, 7, 27)
    print(f"\nTesting data date: {data_date}")
    print(f"Is data date >= start_date? {data_date >= start_date}")
    print(f"Is data date <= end_date? {data_date <= end_date}")
    print(f"Data date in range? {start_date <= data_date <= end_date}")

if __name__ == "__main__":
    test_current_month_logic()