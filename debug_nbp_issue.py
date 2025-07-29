#!/usr/bin/env python3
"""
Debug script for NBP exchange rate issue
Tests the NBP client directly to understand why yesterday's rate is showing
"""

import asyncio
import sys
import os
from datetime import datetime, date, timedelta
import logging

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from open_webui.utils.nbp_client import nbp_client
from open_webui.utils.currency_converter import get_exchange_rate_info
from open_webui.utils.polish_holidays import polish_holidays

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

async def debug_nbp_issue():
    """Debug the NBP exchange rate issue"""
    print("=" * 60)
    print("🔍 NBP Exchange Rate Debug Report")
    print(f"Current time: {datetime.now()}")
    print(f"Today's date: {date.today()}")
    print("=" * 60)
    
    # Test 1: Check working day logic
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    print(f"\n📅 Working Day Analysis:")
    print(f"Today ({today}):")
    print(f"  - Is working day: {polish_holidays.is_working_day(today)}")
    print(f"  - Is weekend: {today.weekday() >= 5}")
    print(f"  - Is holiday: {polish_holidays.is_holiday(today)}")
    
    print(f"Yesterday ({yesterday}):")
    print(f"  - Is working day: {polish_holidays.is_working_day(yesterday)}")
    print(f"  - Is weekend: {yesterday.weekday() >= 5}")
    print(f"  - Is holiday: {polish_holidays.is_holiday(yesterday)}")
    
    # Test 2: Test NBP API directly for both dates
    print(f"\n🌐 Direct NBP API Tests:")
    
    # Test today's rate
    print(f"\nTesting today ({today}):")
    today_data = await nbp_client._fetch_exchange_rate_for_date(today)
    if today_data:
        print(f"  ✅ Found rate: {today_data['rate']} (effective: {today_data['effective_date']})")
    else:
        print(f"  ❌ No data available")
    
    # Test yesterday's rate
    print(f"\nTesting yesterday ({yesterday}):")
    yesterday_data = await nbp_client._fetch_exchange_rate_for_date(yesterday)
    if yesterday_data:
        print(f"  ✅ Found rate: {yesterday_data['rate']} (effective: {yesterday_data['effective_date']})")
    else:
        print(f"  ❌ No data available")
    
    # Test 3: Check cache state
    print(f"\n💾 Cache Analysis:")
    cache_key = "usd_pln_rate"
    cached_data = nbp_client._cache.get(cache_key)
    if cached_data:
        print(f"  📦 Cached data found:")
        print(f"    - Rate: {cached_data['rate']}")
        print(f"    - Effective date: {cached_data['effective_date']}")
        print(f"    - Rate source: {cached_data.get('rate_source', 'unknown')}")
        print(f"    - Skip reason: {cached_data.get('skip_reason', 'N/A')}")
    else:
        print(f"  🗑️  No cached data")
    
    # Test 4: Full NBP client call (this uses caching and logic)
    print(f"\n🏦 Full NBP Client Test:")
    rate_data = await nbp_client.get_usd_pln_rate()
    if rate_data:
        print(f"  ✅ Rate retrieved:")
        print(f"    - Rate: {rate_data['rate']}")
        print(f"    - Effective date: {rate_data['effective_date']}")
        print(f"    - Rate source: {rate_data.get('rate_source', 'unknown')}")
        print(f"    - Skip reason: {rate_data.get('skip_reason', 'N/A')}")
    else:
        print(f"  ❌ Failed to get rate")
    
    # Test 5: Currency converter (what the frontend actually calls)
    print(f"\n💱 Currency Converter Test:")
    converter_data = await get_exchange_rate_info()
    print(f"  Rate: {converter_data['usd_pln']}")
    print(f"  Effective date: {converter_data['effective_date']}")
    print(f"  Rate source: {converter_data['rate_source']}")
    print(f"  Is fallback: {converter_data['is_fallback']}")
    
    # Test 6: Clear cache and test again
    print(f"\n🧹 Cache Clear Test:")
    nbp_client._cache.clear()
    print("  Cache cleared")
    
    fresh_data = await nbp_client.get_usd_pln_rate()
    if fresh_data:
        print(f"  ✅ Fresh rate retrieved:")
        print(f"    - Rate: {fresh_data['rate']}")
        print(f"    - Effective date: {fresh_data['effective_date']}")
        print(f"    - Rate source: {fresh_data.get('rate_source', 'unknown')}")
    else:
        print(f"  ❌ Failed to get fresh rate")
    
    # Test 7: Time-based analysis
    print(f"\n⏰ Time Analysis:")
    now = datetime.now()
    from datetime import time as datetime_time
    publish_time = datetime.combine(today, datetime_time(8, 15))
    print(f"  Current time: {now.strftime('%H:%M:%S')}")
    print(f"  NBP publish time: {publish_time.strftime('%H:%M:%S')}")
    print(f"  After publish time: {now >= publish_time}")
    
    await nbp_client.close()

if __name__ == "__main__":
    asyncio.run(debug_nbp_issue())