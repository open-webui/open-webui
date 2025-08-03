"""
Webhook Repository - InfluxDB-First Architecture
Deduplication handled by InfluxDB request_id tags, no SQLite tracking needed
"""

from typing import Dict, Any, Optional
import logging

log = logging.getLogger(__name__)


class WebhookRepository:
    """Repository for webhook processing data operations - InfluxDB-First"""
    
    @staticmethod
    def is_duplicate_generation(request_id: str, model: str, cost: float) -> bool:
        """InfluxDB-First: Deduplication handled by InfluxDB request_id tags"""
        # InfluxDB handles deduplication via request_id tags automatically
        # No need for SQLite tracking
        return False
    
    @staticmethod
    def mark_generation_processed(request_id: str, model: str, cost: float, 
                                 client_org_id: str, metadata: Dict[str, Any]) -> bool:
        """InfluxDB-First: No need to mark as processed, InfluxDB handles deduplication"""
        # InfluxDB handles deduplication via request_id tags automatically
        # This is a no-op in InfluxDB-First architecture
        return True