"""
Daily Batch Processor for mAI Usage Tracking
Refactored with Service Layer Pattern for improved performance and maintainability

Public API remains unchanged for backward compatibility.
"""

from .orchestrator import BatchOrchestrator, run_daily_batch

# Backward compatibility class
class DailyBatchProcessor:
    """
    Daily batch processor for usage data aggregation
    
    DEPRECATED: This class is maintained for backward compatibility only.
    New code should use run_daily_batch() directly.
    """
    
    def __init__(self):
        pass
        
    async def run_daily_batch(self):
        """Delegate to the refactored implementation"""
        return await run_daily_batch()

__all__ = ['BatchOrchestrator', 'run_daily_batch', 'DailyBatchProcessor']