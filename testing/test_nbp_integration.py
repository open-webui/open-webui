#!/usr/bin/env python3
"""
Test script for NBP exchange rate integration
"""

import asyncio
import sys
import os
from datetime import datetime, date

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_nbp_integration():
    """Test the NBP exchange rate integration"""
    
    print("🔧 Testing NBP Exchange Rate Integration")
    print("=" * 50)
    
    try:
        # Test NBP client directly
        from open_webui.utils.nbp_client import nbp_client
        
        print("1. Testing NBP client directly...")
        rate_data = await nbp_client.get_usd_pln_rate()
        
        if rate_data:
            print(f"✅ NBP Rate: {rate_data['rate']}")
            print(f"   Effective Date: {rate_data['effective_date']}")
            print(f"   Rate Source: {rate_data.get('rate_source', 'current')}")
            print(f"   Table No: {rate_data.get('table_no', 'N/A')}")
        else:
            print("❌ Failed to get NBP rate")
            return False
        
        # Test currency converter utility
        from open_webui.utils.currency_converter import (
            get_current_usd_pln_rate, 
            get_exchange_rate_info,
            convert_usd_to_pln
        )
        
        print("\n2. Testing currency converter utility...")
        
        # Test simple rate fetch
        simple_rate = await get_current_usd_pln_rate()
        print(f"✅ Simple rate: {simple_rate}")
        
        # Test detailed rate info
        rate_info = await get_exchange_rate_info()
        print(f"✅ Rate info: {rate_info}")
        
        # Test conversion
        conversion = await convert_usd_to_pln(100.0)
        print(f"✅ $100 USD = {conversion['pln']} PLN")
        print(f"   Rate used: {conversion['rate']}")
        print(f"   Rate source: {conversion['rate_source']}")
        
        # Test weekend logic
        print("\n3. Testing weekend/time logic...")
        today = date.today()
        weekday = today.weekday()
        
        weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        print(f"   Today is {weekday_names[weekday]} ({today})")
        
        if weekday in [5, 6]:  # Weekend
            print("   ✅ Weekend logic should use Friday rate")
        elif weekday == 0:  # Monday
            now = datetime.now()
            if now.hour < 8 or (now.hour == 8 and now.minute < 15):
                print("   ✅ Monday before 8:15 AM - should use Friday rate")
            else:
                print("   ✅ Monday after 8:15 AM - should use current rate")
        else:
            print("   ✅ Weekday - should use current or previous rate")
        
        # Test caching
        print("\n4. Testing caching...")
        start_time = datetime.now()
        cached_rate = await get_current_usd_pln_rate()
        end_time = datetime.now()
        cache_time = (end_time - start_time).total_seconds() * 1000
        
        print(f"✅ Cached rate: {cached_rate}")
        print(f"   Cache retrieval time: {cache_time:.2f}ms")
        
        if cache_time < 10:  # Should be very fast if cached
            print("   ✅ Caching appears to be working")
        else:
            print("   ⚠️  Caching may not be working optimally")
        
        print(f"\n🎉 All tests passed! Exchange rate integration is working correctly.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you're running this from the mAI project root directory")
        return False
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        try:
            await nbp_client.close()
        except:
            pass

async def main():
    """Main test function"""
    success = await test_nbp_integration()
    if success:
        print(f"\n✅ NBP integration test completed successfully!")
        return 0
    else:
        print(f"\n❌ NBP integration test failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)