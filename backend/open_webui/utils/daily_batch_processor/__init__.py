"""
Daily Batch Processor for mAI Usage Tracking
Refactored with Service Layer Pattern for improved performance and maintainability

Phase 2: Unified InfluxDB-First Architecture Integration
Public API remains unchanged for backward compatibility.
"""

import os
from .orchestrator import BatchOrchestrator, run_daily_batch as legacy_run_daily_batch
from .influxdb_orchestrator import InfluxDBBatchOrchestrator

# Check if InfluxDB-First is enabled to determine which processor to use
INFLUXDB_FIRST_ENABLED = os.getenv("INFLUXDB_FIRST_ENABLED", "true").lower() == "true"

async def run_daily_batch():
    """
    Unified entry point for daily batch processing
    
    Architecture Decision:
    - If INFLUXDB_FIRST_ENABLED=true: Use InfluxDB-First orchestrator
    - If INFLUXDB_FIRST_ENABLED=false: Use legacy SQLite orchestrator
    
    Returns:
        Batch processing result
    """
    if INFLUXDB_FIRST_ENABLED:
        # Use InfluxDB-First orchestrator
        orchestrator = InfluxDBBatchOrchestrator()
        result = await orchestrator.run_daily_batch()
        return result.model_dump()
    else:
        # Use legacy orchestrator
        return await legacy_run_daily_batch()

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
        """Delegate to the unified implementation"""
        return await run_daily_batch()

__all__ = [
    'BatchOrchestrator', 
    'InfluxDBBatchOrchestrator',
    'run_daily_batch', 
    'DailyBatchProcessor'
]