"""
Unified Batch Processor - Phase 2: InfluxDB-First Architecture (Clean Version)
Merges legacy SQLite batch processing with InfluxDB-First approach
"""

import asyncio
import time
import os
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal

from open_webui.usage_tracking.services.influxdb_first_service import influxdb_first_service
from open_webui.models.organization_usage.database import (
    ClientDailyUsage, 
    ClientUserDailyUsage,
    DailyExchangeRate
)
from open_webui.internal.db import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class UnifiedBatchProcessor:
    """
    Unified Batch Processor implementing InfluxDB-First Architecture
    
    Data Flow:
    1. InfluxDB (raw usage data) → SQLite (daily summaries)
    2. Preserves all existing functionality
    3. Removes SQLite raw data processing
    4. Maintains 100% business logic compatibility
    """
    
    def __init__(self):
        self.influxdb_first_enabled = os.getenv("INFLUXDB_FIRST_ENABLED", "true").lower() == "true"
        self.nbp_service_url = os.getenv("NBP_SERVICE_URL", "http://localhost:8001")
        self.markup_multiplier = float(os.getenv("USAGE_MARKUP_MULTIPLIER", "1.3"))
        self.batch_timezone = "Europe/Warsaw"  # CET/CEST
        
    async def run_daily_batch(
        self, 
        processing_date: Optional[date] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Unified daily batch processing entry point
        
        Architecture Decision:
        - If INFLUXDB_FIRST_ENABLED=true: Use InfluxDB → SQLite flow
        - If INFLUXDB_FIRST_ENABLED=false: Fallback to legacy SQLite processing
        """
        batch_start = time.time()
        
        if not processing_date:
            processing_date = date.today() - timedelta(days=1)
        
        if not db:
            # Use get_db as a context manager
            with get_db() as db_session:
                db = db_session
                try:
                    logger.info(f"🚀 Starting unified batch processing for {processing_date}")
                    logger.info(f"📊 InfluxDB-First enabled: {self.influxdb_first_enabled}")
                    
                    if self.influxdb_first_enabled and influxdb_first_service.enabled:
                        result = await self._process_influxdb_first_batch(db, processing_date)
                    else:
                        logger.warning("InfluxDB-First disabled - using legacy processing mode")
                        result = await self._process_legacy_batch(db, processing_date)
                    
                    batch_duration = time.time() - batch_start
                    result["total_duration_seconds"] = batch_duration
                    result["batch_end_time"] = datetime.now().isoformat()
                    
                    await self._record_batch_run(db, processing_date, result)
                    
                    logger.info(
                        f"✅ Unified batch processing completed in {batch_duration:.2f}s: "
                        f"{result.get('clients_processed', 0)} clients, "
                        f"{result.get('influxdb_records_processed', 0)} InfluxDB records, "
                        f"{result.get('sqlite_summaries_created', 0)} summaries created"
                    )
                    
                except Exception as e:
                    batch_duration = time.time() - batch_start
                    logger.error(f"❌ Unified batch processing failed after {batch_duration:.2f}s: {e}")
                    
                    result = {
                        "success": False,
                        "processing_date": processing_date.isoformat(),
                        "error": str(e),
                        "data_source": "influxdb_first" if self.influxdb_first_enabled else "legacy_sqlite",
                        "total_duration_seconds": batch_duration
                    }
        else:
            # External db provided
            try:
                logger.info(f"🚀 Starting unified batch processing for {processing_date}")
                logger.info(f"📊 InfluxDB-First enabled: {self.influxdb_first_enabled}")
                
                if self.influxdb_first_enabled and influxdb_first_service.enabled:
                    result = await self._process_influxdb_first_batch(db, processing_date)
                else:
                    logger.warning("InfluxDB-First disabled - using legacy processing mode")
                    result = await self._process_legacy_batch(db, processing_date)
                
                batch_duration = time.time() - batch_start
                result["total_duration_seconds"] = batch_duration
                result["batch_end_time"] = datetime.now().isoformat()
                
                await self._record_batch_run(db, processing_date, result)
                
                logger.info(
                    f"✅ Unified batch processing completed in {batch_duration:.2f}s: "
                    f"{result.get('clients_processed', 0)} clients, "
                    f"{result.get('influxdb_records_processed', 0)} InfluxDB records, "
                    f"{result.get('sqlite_summaries_created', 0)} summaries created"
                )
                
            except Exception as e:
                batch_duration = time.time() - batch_start
                logger.error(f"❌ Unified batch processing failed after {batch_duration:.2f}s: {e}")
                
                result = {
                    "success": False,
                    "processing_date": processing_date.isoformat(),
                    "error": str(e),
                    "data_source": "influxdb_first" if self.influxdb_first_enabled else "legacy_sqlite",
                    "total_duration_seconds": batch_duration
                }
        
        return result
    
    async def _process_influxdb_first_batch(
        self, 
        db: Session, 
        processing_date: date
    ) -> Dict[str, Any]:
        """Process batch using InfluxDB-First architecture"""
        logger.info("📈 Processing InfluxDB-First batch")
        
        # Step 1: Update NBP exchange rate
        exchange_rate = await self._fetch_exchange_rate(processing_date)
        await self._save_exchange_rate(db, processing_date, exchange_rate)
        
        # Step 2: Get active clients
        client_orgs = await self._get_active_clients(db)
        logger.info(f"📋 Processing {len(client_orgs)} client organizations")
        
        # Step 3: Process each client using InfluxDB data
        results = {
            "success": True,
            "processing_date": processing_date.isoformat(),
            "data_source": "influxdb_first",
            "exchange_rate": float(exchange_rate),
            "clients_processed": 0,
            "influxdb_records_processed": 0,
            "sqlite_summaries_created": 0,
            "data_corrections": 0,
            "errors": []
        }
        
        for client_org in client_orgs:
            try:
                client_result = await self._process_client_influxdb_first(
                    db, client_org, processing_date, exchange_rate
                )
                
                results["clients_processed"] += 1
                results["influxdb_records_processed"] += client_result["influxdb_records_processed"]
                results["sqlite_summaries_created"] += client_result["sqlite_summaries_created"]
                results["data_corrections"] += client_result["data_corrections"]
                
            except Exception as e:
                logger.error(f"Error processing client {client_org.id}: {e}")
                results["errors"].append({
                    "client_org_id": client_org.id,
                    "error": str(e)
                })
        
        db.commit()
        return results
    
    async def _process_client_influxdb_first(
        self,
        db: Session,
        client_org: Any,
        processing_date: date,
        exchange_rate: Decimal
    ) -> Dict[str, Any]:
        """Process single client using InfluxDB → SQLite flow"""
        logger.debug(f"🔄 Processing client: {client_org.name} ({client_org.id})")
        
        # Create UTC-aware datetime objects for InfluxDB queries
        from datetime import timezone
        start_time = datetime.combine(processing_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_time = start_time + timedelta(days=1)
        
        try:
            usage_data = await influxdb_first_service.get_daily_usage_aggregated(
                client_org_id=client_org.id,
                start_time=start_time,
                end_time=end_time
            )
        except Exception as e:
            logger.error(f"Failed to fetch InfluxDB data for client {client_org.id}: {e}")
            return {
                "influxdb_records_processed": 0,
                "sqlite_summaries_created": 0,
                "data_corrections": 0
            }
        
        if not usage_data:
            logger.debug(f"No usage data found for client {client_org.id} on {processing_date}")
            return {
                "influxdb_records_processed": 0,
                "sqlite_summaries_created": 0,
                "data_corrections": 0
            }
        
        # Aggregate data for SQLite summaries
        model_summaries = {}
        user_model_summaries = {}
        influxdb_records_count = len(usage_data)
        
        for record in usage_data:
            model = record.get("model", "unknown")
            user_email = record.get("external_user", "unknown")
            tokens = int(record.get("total_tokens", 0))
            raw_cost_usd = float(record.get("cost_usd", 0.0))
            
            markup_cost_usd = raw_cost_usd * self.markup_multiplier
            markup_cost_pln = markup_cost_usd * float(exchange_rate)
            
            # Aggregate by model
            if model not in model_summaries:
                model_summaries[model] = {
                    "tokens": 0,
                    "raw_cost_usd": 0.0,
                    "markup_cost_usd": 0.0,
                    "markup_cost_pln": 0.0
                }
            
            model_summaries[model]["tokens"] += tokens
            model_summaries[model]["raw_cost_usd"] += raw_cost_usd
            model_summaries[model]["markup_cost_usd"] += markup_cost_usd
            model_summaries[model]["markup_cost_pln"] += markup_cost_pln
            
            # Aggregate by user+model
            user_model_key = (user_email, model)
            if user_model_key not in user_model_summaries:
                user_model_summaries[user_model_key] = {
                    "tokens": 0,
                    "raw_cost_usd": 0.0,
                    "markup_cost_usd": 0.0,
                    "markup_cost_pln": 0.0
                }
            
            user_model_summaries[user_model_key]["tokens"] += tokens
            user_model_summaries[user_model_key]["raw_cost_usd"] += raw_cost_usd
            user_model_summaries[user_model_key]["markup_cost_usd"] += markup_cost_usd
            user_model_summaries[user_model_key]["markup_cost_pln"] += markup_cost_pln
        
        # Save to SQLite summary tables
        sqlite_summaries_created = 0
        data_corrections = 0
        
        # Calculate overall daily summary for ClientDailyUsage
        total_daily_tokens = sum(s["tokens"] for s in model_summaries.values())
        total_daily_raw_cost = sum(s["raw_cost_usd"] for s in model_summaries.values())
        total_daily_markup_cost = sum(s["markup_cost_usd"] for s in model_summaries.values())
        total_daily_markup_cost_pln = sum(s["markup_cost_pln"] for s in model_summaries.values())
        
        # Find primary model (most used by tokens)
        primary_model = max(model_summaries.keys(), key=lambda m: model_summaries[m]["tokens"]) if model_summaries else None
        
        # Save overall daily usage
        corrections = self._save_client_daily_usage(
            db, client_org.id, processing_date, {
                "tokens": total_daily_tokens,
                "raw_cost_usd": total_daily_raw_cost,
                "markup_cost_usd": total_daily_markup_cost,
                "markup_cost_pln": total_daily_markup_cost_pln,
                "primary_model": primary_model,
                "unique_users": len(set(user for user, _ in user_model_summaries.keys()))
            }
        )
        sqlite_summaries_created += 1
        data_corrections += corrections
        
        # Save per-model usage in ClientModelDailyUsage
        for model, summary in model_summaries.items():
            corrections = self._save_client_model_daily_usage(
                db, client_org.id, processing_date, model, summary
            )
            sqlite_summaries_created += 1
            data_corrections += corrections
        
        # Aggregate user summaries (across all models)
        user_summaries = {}
        for (user_email, model), summary in user_model_summaries.items():
            if user_email not in user_summaries:
                user_summaries[user_email] = {
                    "tokens": 0,
                    "raw_cost_usd": 0.0,
                    "markup_cost_usd": 0.0,
                    "markup_cost_pln": 0.0
                }
            user_summaries[user_email]["tokens"] += summary["tokens"]
            user_summaries[user_email]["raw_cost_usd"] += summary["raw_cost_usd"]
            user_summaries[user_email]["markup_cost_usd"] += summary["markup_cost_usd"]
            user_summaries[user_email]["markup_cost_pln"] += summary["markup_cost_pln"]
        
        # Save ClientUserDailyUsage records
        for user_email, summary in user_summaries.items():
            corrections = self._save_client_user_daily_usage(
                db, client_org.id, user_email, processing_date, summary
            )
            sqlite_summaries_created += 1
            data_corrections += corrections
        
        return {
            "influxdb_records_processed": influxdb_records_count,
            "sqlite_summaries_created": sqlite_summaries_created,
            "data_corrections": data_corrections
        }
    
    def _save_client_daily_usage(
        self,
        db: Session,
        client_org_id: str,
        usage_date: date,
        summary: Dict[str, Any]
    ) -> int:
        """Save or update ClientDailyUsage record"""
        corrections = 0
        
        try:
            import uuid
            existing = db.query(ClientDailyUsage).filter_by(
                client_org_id=client_org_id,
                usage_date=usage_date
            ).first()
            
            if existing:
                old_cost = float(existing.markup_cost)
                new_cost = summary["markup_cost_usd"]
                
                existing.total_tokens = summary["tokens"]
                existing.raw_cost = summary["raw_cost_usd"]
                existing.markup_cost = summary["markup_cost_usd"]
                existing.primary_model = summary.get("primary_model")
                existing.unique_users = summary.get("unique_users", 1)
                existing.updated_at = int(datetime.utcnow().timestamp())
                
                if abs(old_cost - new_cost) > 0.001:
                    corrections = 1
                    logger.debug(f"💰 Corrected ClientDailyUsage: ${old_cost:.6f} → ${new_cost:.6f}")
            else:
                usage = ClientDailyUsage(
                    id=str(uuid.uuid4()),
                    client_org_id=client_org_id,
                    usage_date=usage_date,
                    total_tokens=summary["tokens"],
                    raw_cost=summary["raw_cost_usd"],
                    markup_cost=summary["markup_cost_usd"],
                    primary_model=summary.get("primary_model"),
                    unique_users=summary.get("unique_users", 1),
                    created_at=int(datetime.utcnow().timestamp()),
                    updated_at=int(datetime.utcnow().timestamp())
                )
                db.add(usage)
                
        except Exception as e:
            logger.error(f"Failed to save ClientDailyUsage: {e}")
            raise
        
        return corrections
    
    def _save_client_model_daily_usage(
        self,
        db: Session,
        client_org_id: str,
        usage_date: date,
        model: str,
        summary: Dict[str, Any]
    ) -> int:
        """Save or update ClientModelDailyUsage record"""
        corrections = 0
        
        try:
            import uuid
            from open_webui.models.organization_usage.database import ClientModelDailyUsage
            
            existing = db.query(ClientModelDailyUsage).filter_by(
                client_org_id=client_org_id,
                usage_date=usage_date,
                model_name=model
            ).first()
            
            if existing:
                old_cost = float(existing.markup_cost)
                new_cost = summary["markup_cost_usd"]
                
                existing.total_tokens = summary["tokens"]
                existing.raw_cost = summary["raw_cost_usd"]
                existing.markup_cost = summary["markup_cost_usd"]
                existing.updated_at = int(datetime.utcnow().timestamp())
                
                if abs(old_cost - new_cost) > 0.001:
                    corrections = 1
                    logger.debug(f"💰 Corrected ClientModelDailyUsage for {model}: ${old_cost:.6f} → ${new_cost:.6f}")
            else:
                # Extract provider from model name (e.g., "openai/gpt-4" -> "openai")
                provider = model.split("/")[0] if "/" in model else "unknown"
                
                usage = ClientModelDailyUsage(
                    id=str(uuid.uuid4()),
                    client_org_id=client_org_id,
                    usage_date=usage_date,
                    model_name=model,
                    total_tokens=summary["tokens"],
                    raw_cost=summary["raw_cost_usd"],
                    markup_cost=summary["markup_cost_usd"],
                    provider=provider,
                    created_at=int(datetime.utcnow().timestamp()),
                    updated_at=int(datetime.utcnow().timestamp())
                )
                db.add(usage)
                
        except Exception as e:
            logger.error(f"Failed to save ClientModelDailyUsage: {e}")
            raise
        
        return corrections
    
    def _save_client_user_daily_usage(
        self,
        db: Session,
        client_org_id: str,
        user_email: str,
        usage_date: date,
        summary: Dict[str, Any]
    ) -> int:
        """Save or update ClientUserDailyUsage record"""
        corrections = 0
        
        try:
            import uuid
            existing = db.query(ClientUserDailyUsage).filter_by(
                client_org_id=client_org_id,
                openrouter_user_id=user_email,  # external_user from InfluxDB maps to openrouter_user_id
                usage_date=usage_date
            ).first()
            
            if existing:
                old_cost = float(existing.markup_cost)
                new_cost = summary["markup_cost_usd"]
                
                existing.total_tokens = summary["tokens"]
                existing.raw_cost = summary["raw_cost_usd"]
                existing.markup_cost = summary["markup_cost_usd"]
                existing.updated_at = int(datetime.utcnow().timestamp())
                
                if abs(old_cost - new_cost) > 0.001:
                    corrections = 1
                    logger.debug(f"💰 Corrected ClientUserDailyUsage for {user_email}: ${old_cost:.6f} → ${new_cost:.6f}")
            else:
                usage = ClientUserDailyUsage(
                    id=str(uuid.uuid4()),
                    client_org_id=client_org_id,
                    user_id="unknown",  # We don't have the Open WebUI user ID in InfluxDB data
                    openrouter_user_id=user_email,
                    usage_date=usage_date,
                    total_tokens=summary["tokens"],
                    raw_cost=summary["raw_cost_usd"],
                    markup_cost=summary["markup_cost_usd"],
                    created_at=int(datetime.utcnow().timestamp()),
                    updated_at=int(datetime.utcnow().timestamp())
                )
                db.add(usage)
                
        except Exception as e:
            logger.error(f"Failed to save ClientUserDailyUsage: {e}")
            raise
        
        return corrections
    
    async def _process_legacy_batch(
        self, 
        db: Session, 
        processing_date: date
    ) -> Dict[str, Any]:
        """Fallback to legacy SQLite-based processing"""
        logger.warning("🔄 Using legacy SQLite-based batch processing")
        
        try:
            from open_webui.utils.daily_batch_processor import run_daily_batch as legacy_batch
            result = await legacy_batch()
            result["data_source"] = "legacy_sqlite"
            return result
        except ImportError as e:
            logger.error(f"Failed to import legacy batch processor: {e}")
            raise
    
    async def _fetch_exchange_rate(self, date: date) -> Decimal:
        """Fetch USD/PLN exchange rate from NBP service"""
        try:
            import httpx
            
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
            logger.warning("Using fallback exchange rate of 4.0 PLN/USD")
            return Decimal("4.0")
    
    async def _save_exchange_rate(self, db: Session, date: date, rate: Decimal):
        """Save exchange rate to database"""
        try:
            import uuid
            existing = db.query(DailyExchangeRate).filter_by(
                date=date,
                currency_from="USD",
                currency_to="PLN"
            ).first()
            
            if existing:
                existing.rate = float(rate)
                existing.updated_at = int(datetime.utcnow().timestamp())
            else:
                exchange_rate = DailyExchangeRate(
                    id=str(uuid.uuid4()),
                    date=date,
                    currency_from="USD",
                    currency_to="PLN",
                    rate=float(rate),
                    source="NBP",
                    created_at=int(datetime.utcnow().timestamp()),
                    updated_at=int(datetime.utcnow().timestamp())
                )
                db.add(exchange_rate)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to save exchange rate: {e}")
            db.rollback()
    
    async def _get_active_clients(self, db: Session) -> List[Any]:
        """Get all active client organizations"""
        from open_webui.models.organization_usage.database import ClientOrganization
        
        return db.query(ClientOrganization).filter_by(is_active=True).all()
    
    async def _record_batch_run(
        self, 
        db: Session, 
        processing_date: date, 
        result: Dict[str, Any]
    ):
        """Record batch run for tracking and monitoring"""
        try:
            batch_summary = {
                "processing_date": processing_date.isoformat(),
                "success": result.get("success", False),
                "clients_processed": result.get("clients_processed", 0),
                "influxdb_records_processed": result.get("influxdb_records_processed", 0),
                "sqlite_summaries_created": result.get("sqlite_summaries_created", 0),
                "data_corrections": result.get("data_corrections", 0),
                "duration_seconds": result.get("total_duration_seconds", 0),
                "data_source": result.get("data_source", "unknown")
            }
            
            logger.info(f"📋 Batch run summary: {batch_summary}")
            
        except Exception as e:
            logger.error(f"Failed to record batch run: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for unified batch processor"""
        try:
            health_status = {
                "status": "healthy",
                "influxdb_first_enabled": self.influxdb_first_enabled,
                "data_source": "influxdb_first" if self.influxdb_first_enabled else "legacy_sqlite",
                "services": {}
            }
            
            if self.influxdb_first_enabled:
                influxdb_health = await influxdb_first_service.health_check()
                health_status["services"]["influxdb"] = influxdb_health
            
            try:
                test_rate = await self._fetch_exchange_rate(date.today())
                health_status["services"]["nbp"] = {
                    "status": "operational",
                    "test_rate": str(test_rate)
                }
            except Exception as e:
                health_status["services"]["nbp"] = {
                    "status": "error",
                    "error": str(e)
                }
            
            return health_status
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "influxdb_first_enabled": self.influxdb_first_enabled
            }


# Module-level functions for backward compatibility
unified_batch_processor = UnifiedBatchProcessor()


async def run_unified_daily_batch(processing_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Entry point for unified daily batch processing
    
    This function provides backward compatibility while implementing
    the new InfluxDB-First architecture.
    """
    return await unified_batch_processor.run_daily_batch(processing_date)


async def health_check_unified_batch() -> Dict[str, Any]:
    """Health check for unified batch processor"""
    return await unified_batch_processor.health_check()


if __name__ == "__main__":
    import sys
    from datetime import date, timedelta
    
    # Parse command line arguments
    run_now = "--run-now" in sys.argv
    
    # Optional: parse date argument
    processing_date = None
    for i, arg in enumerate(sys.argv):
        if arg == "--date" and i + 1 < len(sys.argv):
            try:
                processing_date = datetime.strptime(sys.argv[i + 1], "%Y-%m-%d").date()
            except ValueError:
                print(f"Error: Invalid date format. Use YYYY-MM-DD")
                sys.exit(1)
    
    if run_now:
        # If no date specified, default to yesterday
        if processing_date is None:
            processing_date = date.today() - timedelta(days=1)
            
        print(f"🚀 Manual batch processing started...")
        print(f"📅 Processing date: {processing_date}")
        
        try:
            # Run the batch process
            result = asyncio.run(run_unified_daily_batch(processing_date))
            
            if result.get('success', False):
                print(f"✅ Batch processing completed successfully!")
                print(f"   - Clients processed: {result.get('clients_processed', 0)}")
                print(f"   - InfluxDB records: {result.get('influxdb_records_processed', 0)}")
                print(f"   - SQLite summaries: {result.get('sqlite_summaries_created', 0)}")
                print(f"   - Duration: {result.get('total_duration_seconds', 0):.2f}s")
                print(f"   - Data source: {result.get('data_source', 'unknown')}")
            else:
                print(f"❌ Batch processing failed: {result.get('error', 'Unknown error')}")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Critical error during batch processing: {e}")
            sys.exit(1)
    else:
        print("Usage: python -m open_webui.utils.unified_batch_processor --run-now [--date YYYY-MM-DD]")
        print("")
        print("Options:")
        print("  --run-now    Execute the batch process immediately (required)")
        print("  --date       Process specific date in YYYY-MM-DD format (optional, default: yesterday)")
        print("")
        print("Examples:")
        print("  python -m open_webui.utils.unified_batch_processor --run-now")
        print("  python -m open_webui.utils.unified_batch_processor --run-now --date 2025-08-01")
        sys.exit(0)