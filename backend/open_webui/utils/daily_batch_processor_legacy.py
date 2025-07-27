#!/usr/bin/env python3
"""
Daily Batch Processor for mAI Usage Tracking - Backward Compatibility Module
Redirects to the new refactored implementation using Service Layer Pattern

This module maintains 100% backward compatibility while the actual implementation
has been refactored for improved performance and maintainability.

Original file: 456 lines (monolithic)
New structure: Service Layer Pattern with focused modules under 100 lines each

Performance improvements:
- Async database operations with connection pooling
- Parallel processing of independent tasks
- Optimized batch operations
- Better error recovery and transaction management
"""

# For backward compatibility, maintain the original imports
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Import from the new package - avoid circular import
from open_webui.utils.daily_batch_processor.orchestrator import run_daily_batch as _run_daily_batch

# Backward compatibility wrapper
class DailyBatchProcessor:
    """
    Daily batch processor for usage data aggregation
    
    DEPRECATED: This class is maintained for backward compatibility only.
    New code should use the refactored implementation directly:
    
    from open_webui.utils.daily_batch_processor import run_daily_batch
    """
    
    def __init__(self):
        log.info("DailyBatchProcessor initialized (using refactored implementation)")
        
    async def run_daily_batch(self) -> Dict[str, Any]:
        """
        Main daily batch processing function
        Delegates to the refactored implementation
        """
        # Use the refactored implementation
        return await _run_daily_batch()

# Public API - direct function
async def run_daily_batch() -> Dict[str, Any]:
    """
    Entry point for daily batch processing
    Can be called from cron job or scheduler
    
    This is the primary API - use this instead of DailyBatchProcessor class
    """
    return await _run_daily_batch()


if __name__ == "__main__":
    """
    Direct execution for testing or manual runs
    Usage: python daily_batch_processor.py
    """
    import sys
    
    print("🕰️ mAI Daily Batch Processor (Refactored)")
    print("=" * 40)
    print(f"Starting batch processing at {datetime.now().isoformat()}")
    
    try:
        result = asyncio.run(run_daily_batch())
        
        if result["success"]:
            print(f"✅ Batch processing completed successfully in {result['batch_duration_seconds']}s")
            print(f"📊 Operations completed: {len(result['operations'])}")
            
            for op in result["operations"]:
                status = "✅" if op["success"] else "❌"
                print(f"  {status} {op['operation']}")
        else:
            print(f"❌ Batch processing failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Batch processing interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)