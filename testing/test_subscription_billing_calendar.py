#!/usr/bin/env python3
"""Test subscription billing calculations for different month lengths"""

import calendar
from datetime import datetime
from typing import List, Dict, Any

def calculate_billing_proportion(created_date: datetime, billing_date: datetime) -> float:
    """Calculate billing proportion based on when user was added"""
    if created_date.year == billing_date.year and created_date.month == billing_date.month:
        days_in_month = calendar.monthrange(billing_date.year, billing_date.month)[1]
        days_remaining = days_in_month - created_date.day + 1
        return days_remaining / days_in_month
    else:
        return 1.0  # Full month billing

def get_pricing_tier(user_count: int) -> int:
    """Get pricing tier based on user count"""
    pricing_tiers = [
        {"min": 1, "max": 3, "price": 79},
        {"min": 4, "max": 9, "price": 69},
        {"min": 10, "max": 19, "price": 59},
        {"min": 20, "max": float('inf'), "price": 54}
    ]
    
    for tier in pricing_tiers:
        if tier["min"] <= user_count <= tier["max"]:
            return tier["price"]
    return 79  # Default

def test_month_billing(year: int, month: int, test_name: str) -> None:
    """Test billing for a specific month"""
    days_in_month = calendar.monthrange(year, month)[1]
    print(f"\n{test_name} - {calendar.month_name[month]} {year} ({days_in_month} days)")
    print("-" * 60)
    
    # Test different user addition dates
    test_days = [1, 15, days_in_month]  # First day, middle, last day
    user_count = 5  # 4-9 users tier = 69 PLN
    tier_price = get_pricing_tier(user_count)
    
    for day in test_days:
        created_date = datetime(year, month, day)
        billing_date = datetime(year, month, days_in_month)
        
        proportion = calculate_billing_proportion(created_date, billing_date)
        days_remaining = days_in_month - day + 1
        user_cost = tier_price * proportion
        
        print(f"User added on day {day:2d}: {days_remaining:2d} days remaining, "
              f"{proportion:5.1%} billing ({user_cost:6.2f} PLN)")

def main():
    """Run billing tests for different month types"""
    print("Subscription Billing Calendar Tests")
    print("===================================")
    print("Testing with 5 users (69 PLN per user/month tier)")
    
    # Test different month types
    test_month_billing(2024, 2, "Leap Year February")    # 29 days
    test_month_billing(2023, 2, "Regular February")      # 28 days
    test_month_billing(2024, 4, "30-day Month (April)")  # 30 days
    test_month_billing(2024, 1, "31-day Month (January)")# 31 days
    
    # Test pricing tier transitions
    print("\n\nPricing Tier Tests")
    print("==================")
    test_users = [1, 3, 4, 9, 10, 19, 20, 50]
    for users in test_users:
        tier_price = get_pricing_tier(users)
        print(f"{users:3d} users: {tier_price} PLN per user/month")

if __name__ == "__main__":
    main()