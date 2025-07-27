"""
Dependency injection container for Usage Tracking
Service instantiation and dependency management
"""

from functools import lru_cache
from ..services.usage_service import UsageService
from ..services.billing_service import BillingService
from ..services.webhook_service import WebhookService
from ..services.pricing_service import PricingService


@lru_cache()
def get_usage_service() -> UsageService:
    """Get singleton UsageService instance"""
    return UsageService()


@lru_cache()
def get_billing_service() -> BillingService:
    """Get singleton BillingService instance"""
    return BillingService()


@lru_cache()
def get_webhook_service() -> WebhookService:
    """Get singleton WebhookService instance"""
    return WebhookService()


@lru_cache()
def get_pricing_service() -> PricingService:
    """Get singleton PricingService instance"""
    return PricingService()