"""
Optimized repository for usage data access
Provides efficient queries with proper indexing and bulk operations
"""

import logging
from datetime import date as DateType, datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from open_webui.models.organization_usage import (
    ClientDailyUsage, ClientUserDailyUsage, ClientModelDailyUsage,
    ClientOrganization
)
from open_webui.internal.db import get_db

log = logging.getLogger(__name__)


class UsageRepository:
    """Repository for efficient usage data access"""
    
    def get_client_info(self, db: Session, client_org_id: str) -> Optional[Dict[str, Any]]:
        """
        Get client organization information
        
        Args:
            db: Database session
            client_org_id: Client organization ID
            
        Returns:
            Client info dict or None
        """
        try:
            client = db.query(ClientOrganization).filter_by(
                id=client_org_id
            ).first()
            
            if client:
                return {
                    "id": client.id,
                    "name": client.name,
                    "timezone": getattr(client, 'timezone', "Europe/Warsaw"),
                    "markup_rate": client.markup_rate,
                    "is_active": client.is_active
                }
            return None
        except Exception as e:
            log.error(f"Failed to get client info: {e}")
            return None
    
    def get_daily_usage_bulk(
        self, 
        db: Session, 
        client_org_id: str,
        start_date: DateType,
        end_date: DateType
    ) -> List[ClientDailyUsage]:
        """
        Bulk fetch daily usage records for a date range
        
        Args:
            db: Database session
            client_org_id: Client organization ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of daily usage records
        """
        try:
            return db.query(ClientDailyUsage).filter(
                and_(
                    ClientDailyUsage.client_org_id == client_org_id,
                    ClientDailyUsage.usage_date >= start_date,
                    ClientDailyUsage.usage_date <= end_date
                )
            ).order_by(ClientDailyUsage.usage_date.desc()).all()
        except Exception as e:
            log.error(f"Failed to get daily usage bulk: {e}")
            return []
    
    def get_month_totals_optimized(
        self,
        db: Session,
        client_org_id: str,
        month_start: DateType,
        month_end: DateType
    ) -> Dict[str, Any]:
        """
        Get month totals with a single optimized query
        
        Args:
            db: Database session
            client_org_id: Client organization ID
            month_start: First day of month
            month_end: Last day of month (or current date)
            
        Returns:
            Dictionary with aggregated month totals
        """
        try:
            # Single query with aggregation
            result = db.query(
                func.sum(ClientDailyUsage.total_tokens).label('total_tokens'),
                func.sum(ClientDailyUsage.total_requests).label('total_requests'),
                func.sum(ClientDailyUsage.raw_cost).label('raw_cost'),
                func.sum(ClientDailyUsage.markup_cost).label('markup_cost'),
                func.count(ClientDailyUsage.id).label('days_active')
            ).filter(
                and_(
                    ClientDailyUsage.client_org_id == client_org_id,
                    ClientDailyUsage.usage_date >= month_start,
                    ClientDailyUsage.usage_date <= month_end
                )
            ).first()
            
            if result:
                return {
                    'tokens': result.total_tokens or 0,
                    'requests': result.total_requests or 0,
                    'raw_cost': result.raw_cost or 0.0,
                    'cost': result.markup_cost or 0.0,
                    'days_active': result.days_active or 0
                }
            
            return {
                'tokens': 0,
                'requests': 0,
                'raw_cost': 0.0,
                'cost': 0.0,
                'days_active': 0
            }
            
        except Exception as e:
            log.error(f"Failed to get optimized month totals: {e}")
            return {
                'tokens': 0,
                'requests': 0,
                'raw_cost': 0.0,
                'cost': 0.0,
                'days_active': 0
            }
    
    def get_user_usage_bulk(
        self,
        db: Session,
        client_org_id: str,
        start_date: Optional[DateType] = None,
        end_date: Optional[DateType] = None
    ) -> List[Dict[str, Any]]:
        """
        Get aggregated usage by user with efficient query
        
        Args:
            db: Database session
            client_org_id: Client organization ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of user usage summaries
        """
        try:
            query = db.query(
                ClientUserDailyUsage.user_id,
                ClientUserDailyUsage.openrouter_user_id,
                func.sum(ClientUserDailyUsage.total_tokens).label('total_tokens'),
                func.sum(ClientUserDailyUsage.total_requests).label('total_requests'),
                func.sum(ClientUserDailyUsage.markup_cost).label('total_cost'),
                func.max(ClientUserDailyUsage.updated_at).label('last_active')
            ).filter(
                ClientUserDailyUsage.client_org_id == client_org_id
            )
            
            if start_date:
                query = query.filter(ClientUserDailyUsage.usage_date >= start_date)
            if end_date:
                query = query.filter(ClientUserDailyUsage.usage_date <= end_date)
            
            results = query.group_by(
                ClientUserDailyUsage.user_id,
                ClientUserDailyUsage.openrouter_user_id
            ).all()
            
            return [
                {
                    'user_id': r.user_id,
                    'openrouter_user_id': r.openrouter_user_id,
                    'tokens': r.total_tokens or 0,
                    'requests': r.total_requests or 0,
                    'cost': r.total_cost or 0.0,
                    'last_active': datetime.fromtimestamp(r.last_active) if r.last_active else None
                }
                for r in results
            ]
            
        except Exception as e:
            log.error(f"Failed to get user usage bulk: {e}")
            return []
    
    def get_model_usage_bulk(
        self,
        db: Session,
        client_org_id: str,
        start_date: Optional[DateType] = None,
        end_date: Optional[DateType] = None
    ) -> List[Dict[str, Any]]:
        """
        Get aggregated usage by model with efficient query
        
        Args:
            db: Database session
            client_org_id: Client organization ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of model usage summaries
        """
        try:
            query = db.query(
                ClientModelDailyUsage.model_name,
                ClientModelDailyUsage.provider,
                func.sum(ClientModelDailyUsage.total_tokens).label('total_tokens'),
                func.sum(ClientModelDailyUsage.total_requests).label('total_requests'),
                func.sum(ClientModelDailyUsage.markup_cost).label('total_cost'),
                func.sum(ClientModelDailyUsage.raw_cost).label('raw_cost')
            ).filter(
                ClientModelDailyUsage.client_org_id == client_org_id
            )
            
            if start_date:
                query = query.filter(ClientModelDailyUsage.usage_date >= start_date)
            if end_date:
                query = query.filter(ClientModelDailyUsage.usage_date <= end_date)
            
            results = query.group_by(
                ClientModelDailyUsage.model_name,
                ClientModelDailyUsage.provider
            ).all()
            
            return [
                {
                    'model_name': r.model_name,
                    'provider': r.provider,
                    'tokens': r.total_tokens or 0,
                    'requests': r.total_requests or 0,
                    'cost': r.total_cost or 0.0,
                    'raw_cost': r.raw_cost or 0.0,
                    'average_cost_per_request': (
                        (r.total_cost or 0) / r.total_requests 
                        if r.total_requests else 0
                    )
                }
                for r in results
            ]
            
        except Exception as e:
            log.error(f"Failed to get model usage bulk: {e}")
            return []