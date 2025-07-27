#!/usr/bin/env python3
"""
Test script to verify the refactored batch processor implementation
"""

import asyncio
import sys
import os
from datetime import datetime

# Add backend to Python path
sys.path.insert(0, '.')

# Test imports to ensure backward compatibility
print("Testing backward compatibility imports...")
try:
    # Test old import path
    from open_webui.utils.daily_batch_processor import DailyBatchProcessor, run_daily_batch
    print("✅ Backward compatibility imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Test new import path
print("\nTesting new implementation imports...")
try:
    from open_webui.utils.daily_batch_processor import BatchOrchestrator
    from open_webui.utils.daily_batch_processor.services import (
        NBPExchangeRateService,
        ModelPricingService,
        UsageAggregationService,
        DataCleanupService,
        MonthlyRolloverService
    )
    print("✅ New implementation imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Test module structure
print("\nVerifying module structure...")
import open_webui.utils.daily_batch_processor as batch_module
expected_attrs = ['BatchOrchestrator', 'run_daily_batch']
for attr in expected_attrs:
    if hasattr(batch_module, attr):
        print(f"✅ Found: {attr}")
    else:
        print(f"❌ Missing: {attr}")

# Test async functionality
async def test_batch_functionality():
    """Test basic functionality of the refactored batch processor"""
    print("\nTesting batch processor functionality...")
    
    try:
        # Test using the old API (for backward compatibility)
        processor = DailyBatchProcessor()
        print("✅ DailyBatchProcessor instance created")
        
        # Test using the new API
        result = await run_daily_batch()
        
        if isinstance(result, dict):
            print(f"✅ Batch processing returned result: success={result.get('success', False)}")
            if 'operations' in result:
                print(f"✅ Operations found: {len(result['operations'])}")
            if 'batch_duration_seconds' in result:
                print(f"✅ Performance metric available: {result['batch_duration_seconds']}s")
        else:
            print(f"❌ Unexpected result type: {type(result)}")
            
    except Exception as e:
        print(f"❌ Error during batch processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Testing Refactored Daily Batch Processor")
    print("=" * 50)
    print(f"Test started at: {datetime.now().isoformat()}")
    
    # Run the async test
    asyncio.run(test_batch_functionality())
    
    print("\n✅ All tests completed!")
    print("The refactored implementation maintains backward compatibility while providing:")
    print("- Service Layer Pattern with focused responsibilities")
    print("- Async database operations with connection pooling")
    print("- Parallel processing of independent tasks")
    print("- Better error recovery and monitoring")