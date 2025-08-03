#!/usr/bin/env python3
"""
Test script to verify NBP service mock mode functionality
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.nbp_client import NBPClient
from app.services.cache_service import CacheService


async def test_mock_mode():
    """Test NBP client in mock mode"""
    print("Testing NBP Service Mock Mode")
    print("=" * 50)
    
    # Initialize services
    cache_service = CacheService()
    nbp_client = NBPClient(mock_mode=True, cache_service=cache_service)
    
    # Test 1: Get current rate
    print("\n1. Testing current rate fetch:")
    current_rate = await nbp_client.get_rate()
    print(f"   Currency: {current_rate.currency}")
    print(f"   Rate: {current_rate.rate} PLN")
    print(f"   Date: {current_rate.date}")
    print(f"   Source: {current_rate.source}")
    assert current_rate.source == "mock", "Should be using mock data"
    assert current_rate.currency == "USD", "Currency should be USD"
    assert 3.5 <= current_rate.rate <= 4.5, "Rate should be realistic"
    
    # Test 2: Get rate for specific date
    print("\n2. Testing specific date fetch:")
    specific_rate = await nbp_client.get_rate("2025-01-15")
    print(f"   Currency: {specific_rate.currency}")
    print(f"   Rate: {specific_rate.rate} PLN")
    print(f"   Date: {specific_rate.date}")
    print(f"   Source: {specific_rate.source}")
    assert specific_rate.date == "2025-01-15", "Date should match requested"
    assert specific_rate.source == "mock", "Should be using mock data"
    
    # Test 3: Get rates for date range
    print("\n3. Testing date range fetch:")
    rates_range = await nbp_client.get_rates_range("2025-01-01", "2025-01-07")
    print(f"   Total rates: {len(rates_range)}")
    print(f"   First rate: {rates_range[0].date} - {rates_range[0].rate} PLN")
    print(f"   Last rate: {rates_range[-1].date} - {rates_range[-1].rate} PLN")
    # Should exclude weekends
    assert len(rates_range) <= 5, "Should exclude weekends"
    
    # Test 4: Verify mock rates are consistent for same date
    print("\n4. Testing rate consistency:")
    rate1 = await nbp_client.get_rate("2025-01-20")
    rate2 = await nbp_client.get_rate("2025-01-20")
    print(f"   First fetch: {rate1.rate} PLN")
    print(f"   Second fetch: {rate2.rate} PLN")
    assert rate1.rate == rate2.rate, "Rates should be consistent for same date"
    
    print("\n✅ All mock mode tests passed!")
    
    # Cleanup
    await nbp_client.close()


if __name__ == "__main__":
    asyncio.run(test_mock_mode())