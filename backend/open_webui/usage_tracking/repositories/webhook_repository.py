"""
Webhook Repository - Data access for webhook processing
Handles duplicate prevention and webhook state management
"""

from typing import Dict, Any, Optional


class WebhookRepository:
    """Repository for webhook processing data operations"""
    
    @staticmethod
    def is_duplicate_generation(request_id: str, model: str, cost: float) -> bool:
        """Check if a generation has already been processed (duplicate prevention)"""
        try:
            from open_webui.models.organization_usage import ProcessedGenerationDB
            return ProcessedGenerationDB.is_duplicate(request_id, model, cost)
        except Exception:
            # In case of error, assume not duplicate to avoid blocking valid requests
            return False
    
    @staticmethod
    def mark_generation_processed(request_id: str, model: str, cost: float, 
                                 client_org_id: str, metadata: Dict[str, Any]) -> bool:
        """Mark a generation as processed for duplicate prevention"""
        try:
            from open_webui.models.organization_usage import ProcessedGenerationDB
            return ProcessedGenerationDB.mark_processed(
                request_id, model, cost, client_org_id, metadata
            )
        except Exception:
            # Continue processing even if marking fails
            print(f"Warning: Failed to mark generation as processed: {request_id}")
            return False