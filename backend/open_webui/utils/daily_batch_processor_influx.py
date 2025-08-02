"""
Daily Batch Processor for InfluxDB
Processes usage data from InfluxDB Cloud at 13:00 CET daily
Aggregates data by client, model, and user with PLN conversion
"""

import os
import asyncio
import logging
import httpx
from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, List, Optional
from decimal import Decimal

from open_webui.usage_tracking.services.influxdb_service import InfluxDBService
from open_webui.usage_tracking.models.database import (
    ClientDailyUsageDB, 
    ClientUserDailyUsageDB,
    DailyExchangeRateDB
)
from open_webui.utils.database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class DailyBatchProcessorInflux:
    """
    Daily batch processor that reads from InfluxDB and writes to SQLite
    Designed to run at 13:00 CET to use same-day NBP exchange rates
    """
    
    def __init__(self):
        self.influxdb_service = InfluxDBService()
        self.nbp_service_url = os.getenv("NBP_SERVICE_URL", "http://localhost:8001")
        self.markup_multiplier = float(os.getenv("USAGE_MARKUP_MULTIPLIER", "1.3"))
        self.batch_timezone = timezone(timedelta(hours=1))  # CET
        
    async def process_daily_batch(
        self, 
        processing_date: Optional[date] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for daily batch processing
        
        Args:
            processing_date: Date to process (default: yesterday)
            db: Database session (optional, will create if not provided)
            
        Returns:
            Batch processing result with statistics
        """
        if not self.influxdb_service.enabled:
            logger.warning("InfluxDB is not enabled, skipping batch processing")
            return {
                "success": False,
                "error": "InfluxDB not enabled",
                "message": "Batch processing requires InfluxDB to be enabled"
            }
        
        # Use yesterday as default processing date
        if not processing_date:
            processing_date = date.today() - timedelta(days=1)
        
        # Create database session if not provided
        if not db:
            db = next(get_db())
            close_db = True
        else:
            close_db = False
        
        try:
            logger.info(f"Starting InfluxDB batch processing for {processing_date}")
            
            # Step 1: Get exchange rate from NBP service
            exchange_rate = await self._get_exchange_rate(processing_date)
            logger.info(f"Exchange rate for {processing_date}: 1 USD = {exchange_rate} PLN")
            
            # Save exchange rate to database
            self._save_exchange_rate(db, processing_date, exchange_rate)
            
            # Step 2: Get all client organizations
            client_orgs = self._get_active_clients(db)
            logger.info(f"Processing {len(client_orgs)} client organizations")
            
            # Step 3: Process each client organization
            results = {
                "success": True,
                "processing_date": processing_date.isoformat(),
                "exchange_rate": float(exchange_rate),
                "clients_processed": 0,
                "total_records": 0,
                "total_cost_usd": 0.0,
                "total_cost_pln": 0.0,
                "errors": []
            }
            
            for client_org in client_orgs:
                try:
                    client_result = await self._process_client_organization(
                        db, client_org, processing_date, exchange_rate
                    )
                    
                    results["clients_processed"] += 1
                    results["total_records"] += client_result["records_processed"]
                    results["total_cost_usd"] += client_result["total_cost_usd"]
                    results["total_cost_pln"] += client_result["total_cost_pln"]
                    
                except Exception as e:
                    logger.error(f"Error processing client {client_org.id}: {e}")
                    results["errors"].append({
                        "client_org_id": client_org.id,
                        "error": str(e)
                    })
            
            # Commit all changes
            db.commit()
            
            logger.info(
                f"Batch processing completed: {results['clients_processed']} clients, "
                f"{results['total_records']} records, "
                f"${results['total_cost_usd']:.2f} USD / {results['total_cost_pln']:.2f} PLN"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            db.rollback()
            return {
                "success": False,
                "error": str(e),
                "processing_date": processing_date.isoformat()
            }
        finally:
            if close_db:
                db.close()
    
    async def _get_exchange_rate(self, date: date) -> Decimal:
        """
        Get USD/PLN exchange rate from NBP service
        
        Args:
            date: Date for which to get the rate
            
        Returns:
            Exchange rate as Decimal
        """
        try:
            # Format date for NBP API (YYYY-MM-DD)
            date_str = date.strftime("%Y-%m-%d")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.nbp_service_url}/api/usd-pln-rate",
                    params={"date": date_str},
                    timeout=10.0
                )
                response.raise_for_status()
                
                data = response.json()
                return Decimal(str(data["rate"]))
                
        except Exception as e:
            logger.error(f"Failed to get exchange rate from NBP service: {e}")
            # Fallback to a default rate if NBP service fails
            logger.warning("Using fallback exchange rate of 4.0 PLN/USD")
            return Decimal("4.0")
    
    def _save_exchange_rate(self, db: Session, date: date, rate: Decimal):
        """Save exchange rate to database"""
        try:
            # Check if rate already exists
            existing = db.query(DailyExchangeRateDB).filter_by(
                date=date,
                currency_from="USD",
                currency_to="PLN"
            ).first()
            
            if existing:
                existing.rate = rate
                existing.updated_at = datetime.utcnow()
            else:
                exchange_rate = DailyExchangeRateDB(
                    date=date,
                    currency_from="USD",
                    currency_to="PLN",
                    rate=rate,
                    source="NBP"
                )
                db.add(exchange_rate)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to save exchange rate: {e}")
            db.rollback()
    
    def _get_active_clients(self, db: Session) -> List[Any]:
        """Get all active client organizations"""
        from open_webui.models.organization_usage import ClientOrganizationDB
        
        return db.query(ClientOrganizationDB).filter_by(is_active=True).all()
    
    async def _process_client_organization(
        self,
        db: Session,
        client_org: Any,
        processing_date: date,
        exchange_rate: Decimal
    ) -> Dict[str, Any]:
        """
        Process usage data for a single client organization
        
        Returns:
            Processing statistics for the client
        """
        logger.info(f"Processing client: {client_org.name} ({client_org.id})")
        
        # Define time range for the processing date (in UTC)
        start_time = datetime.combine(processing_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_time = start_time + timedelta(days=1)
        
        # Query InfluxDB for aggregated usage data
        usage_data = await self.influxdb_service.get_data_for_batch(
            client_org.id,
            start_time,
            end_time
        )
        
        if not usage_data:
            logger.info(f"No usage data found for client {client_org.id} on {processing_date}")
            return {
                "records_processed": 0,
                "total_cost_usd": 0.0,
                "total_cost_pln": 0.0
            }
        
        # Aggregate by model and user
        model_totals = {}
        user_totals = {}
        
        for record in usage_data:
            model = record["model"]
            user = record.get("external_user", "unknown")
            tokens = record["total_tokens"]
            cost_usd = record["cost_usd"]
            
            # Apply markup
            cost_usd_with_markup = cost_usd * self.markup_multiplier
            cost_pln = cost_usd_with_markup * exchange_rate
            
            # Aggregate by model
            if model not in model_totals:
                model_totals[model] = {
                    "tokens": 0,
                    "cost_usd": 0.0,
                    "cost_pln": 0.0
                }
            
            model_totals[model]["tokens"] += tokens
            model_totals[model]["cost_usd"] += cost_usd_with_markup
            model_totals[model]["cost_pln"] += cost_pln
            
            # Aggregate by user
            if user not in user_totals:
                user_totals[user] = {
                    "models": {},
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                    "total_cost_pln": 0.0
                }
            
            if model not in user_totals[user]["models"]:
                user_totals[user]["models"][model] = {
                    "tokens": 0,
                    "cost_usd": 0.0,
                    "cost_pln": 0.0
                }
            
            user_totals[user]["models"][model]["tokens"] += tokens
            user_totals[user]["models"][model]["cost_usd"] += cost_usd_with_markup
            user_totals[user]["models"][model]["cost_pln"] += cost_pln
            user_totals[user]["total_tokens"] += tokens
            user_totals[user]["total_cost_usd"] += cost_usd_with_markup
            user_totals[user]["total_cost_pln"] += cost_pln
        
        # Save aggregated data to SQLite
        total_cost_usd = 0.0
        total_cost_pln = 0.0
        
        # Save client daily usage
        for model, totals in model_totals.items():
            self._save_client_daily_usage(
                db,
                client_org.id,
                processing_date,
                model,
                totals["tokens"],
                Decimal(str(totals["cost_usd"])),
                Decimal(str(totals["cost_pln"]))
            )
            
            total_cost_usd += totals["cost_usd"]
            total_cost_pln += totals["cost_pln"]
        
        # Save user daily usage
        for user_email, user_data in user_totals.items():
            for model, model_data in user_data["models"].items():
                self._save_user_daily_usage(
                    db,
                    client_org.id,
                    user_email,
                    processing_date,
                    model,
                    model_data["tokens"],
                    Decimal(str(model_data["cost_usd"])),
                    Decimal(str(model_data["cost_pln"]))
                )
        
        db.commit()
        
        return {
            "records_processed": len(usage_data),
            "total_cost_usd": total_cost_usd,
            "total_cost_pln": float(total_cost_pln)
        }
    
    def _save_client_daily_usage(
        self,
        db: Session,
        client_org_id: str,
        usage_date: date,
        model: str,
        tokens: int,
        cost_usd: Decimal,
        cost_pln: Decimal
    ):
        """Save or update client daily usage record"""
        try:
            # Check if record exists
            existing = db.query(ClientDailyUsageDB).filter_by(
                client_org_id=client_org_id,
                usage_date=usage_date,
                model=model
            ).first()
            
            if existing:
                # Update existing record
                existing.total_tokens = tokens
                existing.total_cost = cost_usd
                existing.total_cost_pln = cost_pln
                existing.updated_at = datetime.utcnow()
                existing.source = "influxdb_batch"
            else:
                # Create new record
                usage = ClientDailyUsageDB(
                    client_org_id=client_org_id,
                    usage_date=usage_date,
                    model=model,
                    total_tokens=tokens,
                    total_cost=cost_usd,
                    total_cost_pln=cost_pln,
                    source="influxdb_batch"
                )
                db.add(usage)
                
        except Exception as e:
            logger.error(f"Failed to save client daily usage: {e}")
            raise
    
    def _save_user_daily_usage(
        self,
        db: Session,
        client_org_id: str,
        user_email: str,
        usage_date: date,
        model: str,
        tokens: int,
        cost_usd: Decimal,
        cost_pln: Decimal
    ):
        """Save or update user daily usage record"""
        try:
            # Check if record exists
            existing = db.query(ClientUserDailyUsageDB).filter_by(
                client_org_id=client_org_id,
                user_email=user_email,
                usage_date=usage_date,
                model=model
            ).first()
            
            if existing:
                # Update existing record
                existing.total_tokens = tokens
                existing.total_cost = cost_usd
                existing.total_cost_pln = cost_pln
                existing.updated_at = datetime.utcnow()
                existing.source = "influxdb_batch"
            else:
                # Create new record
                usage = ClientUserDailyUsageDB(
                    client_org_id=client_org_id,
                    user_email=user_email,
                    usage_date=usage_date,
                    model=model,
                    total_tokens=tokens,
                    total_cost=cost_usd,
                    total_cost_pln=cost_pln,
                    source="influxdb_batch"
                )
                db.add(usage)
                
        except Exception as e:
            logger.error(f"Failed to save user daily usage: {e}")
            raise
    
    async def validate_against_sqlite(
        self,
        processing_date: date,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Compare InfluxDB results against SQLite data for validation
        Useful during dual-write mode to ensure data consistency
        """
        if not db:
            db = next(get_db())
            close_db = True
        else:
            close_db = False
        
        try:
            # Get InfluxDB totals
            influx_totals = {}
            clients = self._get_active_clients(db)
            
            for client in clients:
                start_time = datetime.combine(processing_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                end_time = start_time + timedelta(days=1)
                
                usage_data = await self.influxdb_service.get_data_for_batch(
                    client.id,
                    start_time,
                    end_time
                )
                
                client_total = sum(record["cost_usd"] for record in usage_data)
                influx_totals[client.id] = client_total * self.markup_multiplier
            
            # Get SQLite totals
            sqlite_totals = {}
            sqlite_records = db.query(ClientDailyUsageDB).filter_by(
                usage_date=processing_date,
                source="webhook"  # Only compare webhook-sourced data
            ).all()
            
            for record in sqlite_records:
                if record.client_org_id not in sqlite_totals:
                    sqlite_totals[record.client_org_id] = 0.0
                sqlite_totals[record.client_org_id] += float(record.total_cost)
            
            # Compare results
            discrepancies = []
            for client_id in set(influx_totals.keys()) | set(sqlite_totals.keys()):
                influx_val = influx_totals.get(client_id, 0.0)
                sqlite_val = sqlite_totals.get(client_id, 0.0)
                
                if abs(influx_val - sqlite_val) > 0.01:  # Allow 1 cent tolerance
                    discrepancies.append({
                        "client_org_id": client_id,
                        "influxdb_total": influx_val,
                        "sqlite_total": sqlite_val,
                        "difference": influx_val - sqlite_val
                    })
            
            return {
                "success": True,
                "processing_date": processing_date.isoformat(),
                "clients_compared": len(set(influx_totals.keys()) | set(sqlite_totals.keys())),
                "discrepancies": discrepancies,
                "discrepancy_count": len(discrepancies)
            }
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if close_db:
                db.close()


# Module-level function for compatibility
async def run_influxdb_batch(processing_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Entry point for InfluxDB daily batch processing
    Should be scheduled for 13:00 CET daily
    """
    processor = DailyBatchProcessorInflux()
    return await processor.process_daily_batch(processing_date)