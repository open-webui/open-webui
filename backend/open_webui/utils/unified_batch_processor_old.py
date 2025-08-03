"""
Unified Batch Processor - Phase 2: InfluxDB-First Architecture
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
from open_webui.usage_tracking.models.database import (
    ClientDailyUsageDB, 
    ClientUserDailyUsageDB,
    ClientModelDailyUsageDB,
    DailyExchangeRateDB
)
from open_webui.utils.database import get_db
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
        
        Args:
            processing_date: Date to process (default: yesterday)
            db: Database session (optional)
            
        Returns:
            Unified batch processing result
        """
        batch_start = time.time()
        
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
            logger.info(f"🚀 Starting unified batch processing for {processing_date}")
            logger.info(f"📊 InfluxDB-First enabled: {self.influxdb_first_enabled}")
            
            if self.influxdb_first_enabled and influxdb_first_service.enabled:
                # Phase 2: InfluxDB-First processing
                result = await self._process_influxdb_first_batch(db, processing_date)
            else:
                # Fallback: Legacy processing (if needed for backward compatibility)
                logger.warning("InfluxDB-First disabled - using legacy processing mode")
                result = await self._process_legacy_batch(db, processing_date)
            
            batch_duration = time.time() - batch_start
            result["total_duration_seconds"] = batch_duration
            result["batch_end_time"] = datetime.now().isoformat()
            
            # Record batch run for tracking
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
            
        finally:
            if close_db:
                db.close()
        
        return result
    
    async def _process_influxdb_first_batch(
        self, 
        db: Session, 
        processing_date: date
    ) -> Dict[str, Any]:
        """
        Process batch using InfluxDB-First architecture
        
        Flow:
        1. Update reference data (NBP rates)
        2. Read raw usage from InfluxDB
        3. Aggregate into SQLite summaries
        4. Apply markup calculations
        5. Validate data consistency
        """
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
        
        # Commit all changes
        db.commit()
        
        return results
    
    async def _process_client_influxdb_first(
        self,
        db: Session,
        client_org: Any,
        processing_date: date,
        exchange_rate: Decimal
    ) -> Dict[str, Any]:
        """
        Process single client using InfluxDB → SQLite flow
        
        Optimized Flux Queries:
        - Group by client_org_id, model, external_user
        - Sum tokens, cost_usd for daily aggregation
        - Single query per client for efficiency
        """
        logger.debug(f"🔄 Processing client: {client_org.name} ({client_org.id})")
        
        # Define time range for processing date (UTC)
        start_time = datetime.combine(processing_date, datetime.min.time()).replace(tzinfo=None)
        end_time = start_time + timedelta(days=1)
        
        # Get aggregated usage data from InfluxDB
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
            
            # Apply markup
            markup_cost_usd = raw_cost_usd * self.markup_multiplier
            markup_cost_pln = markup_cost_usd * float(exchange_rate)
            
            # Aggregate by model for ClientDailyUsage
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
            
            # Aggregate by user+model for ClientUserDailyUsage
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
        
        # Save ClientDailyUsage records
        for model, summary in model_summaries.items():
            corrections = self._save_client_daily_usage(
                db, client_org.id, processing_date, model, summary
            )
            sqlite_summaries_created += 1
            data_corrections += corrections
        
        # Save ClientUserDailyUsage records
        for (user_email, model), summary in user_model_summaries.items():
            corrections = self._save_client_user_daily_usage(
                db, client_org.id, user_email, processing_date, model, summary
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
        model: str,
        summary: Dict[str, Any]
    ) -> int:
        """Save or update ClientDailyUsage record"""\n        corrections = 0\n        \n        try:\n            # Check if record exists\n            existing = db.query(ClientDailyUsageDB).filter_by(\n                client_org_id=client_org_id,\n                usage_date=usage_date,\n                model=model\n            ).first()\n            \n            if existing:\n                # Update existing record\n                old_cost = float(existing.total_cost)\n                new_cost = summary[\"markup_cost_usd\"]\n                \n                existing.total_tokens = summary[\"tokens\"]\n                existing.total_cost = Decimal(str(new_cost))\n                existing.total_cost_pln = Decimal(str(summary[\"markup_cost_pln\"]))\n                existing.updated_at = datetime.utcnow()\n                existing.source = \"influxdb_first\"\n                \n                # Check if correction was made\n                if abs(old_cost - new_cost) > 0.001:\n                    corrections = 1\n                    logger.debug(f\"💰 Corrected ClientDailyUsage for {model}: ${old_cost:.6f} → ${new_cost:.6f}\")\n            else:\n                # Create new record\n                usage = ClientDailyUsageDB(\n                    client_org_id=client_org_id,\n                    usage_date=usage_date,\n                    model=model,\n                    total_tokens=summary[\"tokens\"],\n                    total_cost=Decimal(str(summary[\"markup_cost_usd\"])),\n                    total_cost_pln=Decimal(str(summary[\"markup_cost_pln\"])),\n                    source=\"influxdb_first\"\n                )\n                db.add(usage)\n                \n        except Exception as e:\n            logger.error(f\"Failed to save ClientDailyUsage: {e}\")\n            raise\n        \n        return corrections\n    \n    async def _save_client_user_daily_usage(\n        self,\n        db: Session,\n        client_org_id: str,\n        user_email: str,\n        usage_date: date,\n        model: str,\n        summary: Dict[str, Any]\n    ) -> int:\n        \"\"\"Save or update ClientUserDailyUsage record\"\"\"\n        corrections = 0\n        \n        try:\n            # Check if record exists\n            existing = db.query(ClientUserDailyUsageDB).filter_by(\n                client_org_id=client_org_id,\n                user_email=user_email,\n                usage_date=usage_date,\n                model=model\n            ).first()\n            \n            if existing:\n                # Update existing record\n                old_cost = float(existing.total_cost)\n                new_cost = summary[\"markup_cost_usd\"]\n                \n                existing.total_tokens = summary[\"tokens\"]\n                existing.total_cost = Decimal(str(new_cost))\n                existing.total_cost_pln = Decimal(str(summary[\"markup_cost_pln\"]))\n                existing.updated_at = datetime.utcnow()\n                existing.source = \"influxdb_first\"\n                \n                # Check if correction was made\n                if abs(old_cost - new_cost) > 0.001:\n                    corrections = 1\n                    logger.debug(f\"💰 Corrected ClientUserDailyUsage for {user_email}/{model}: ${old_cost:.6f} → ${new_cost:.6f}\")\n            else:\n                # Create new record\n                usage = ClientUserDailyUsageDB(\n                    client_org_id=client_org_id,\n                    user_email=user_email,\n                    usage_date=usage_date,\n                    model=model,\n                    total_tokens=summary[\"tokens\"],\n                    total_cost=Decimal(str(summary[\"markup_cost_usd\"])),\n                    total_cost_pln=Decimal(str(summary[\"markup_cost_pln\"])),\n                    source=\"influxdb_first\"\n                )\n                db.add(usage)\n                \n        except Exception as e:\n            logger.error(f\"Failed to save ClientUserDailyUsage: {e}\")\n            raise\n        \n        return corrections\n    \n    async def _process_legacy_batch(\n        self, \n        db: Session, \n        processing_date: date\n    ) -> Dict[str, Any]:\n        \"\"\"Fallback to legacy SQLite-based processing\"\"\"\n        logger.warning(\"🔄 Using legacy SQLite-based batch processing\")\n        \n        # Import legacy processor on-demand\n        try:\n            from open_webui.utils.daily_batch_processor import run_daily_batch as legacy_batch\n            result = await legacy_batch()\n            result[\"data_source\"] = \"legacy_sqlite\"\n            return result\n        except ImportError as e:\n            logger.error(f\"Failed to import legacy batch processor: {e}\")\n            raise\n    \n    async def _fetch_exchange_rate(self, date: date) -> Decimal:\n        \"\"\"Fetch USD/PLN exchange rate from NBP service\"\"\"\n        try:\n            import httpx\n            \n            date_str = date.strftime(\"%Y-%m-%d\")\n            \n            async with httpx.AsyncClient() as client:\n                response = await client.get(\n                    f\"{self.nbp_service_url}/api/usd-pln-rate\",\n                    params={\"date\": date_str},\n                    timeout=10.0\n                )\n                response.raise_for_status()\n                \n                data = response.json()\n                return Decimal(str(data[\"rate\"]))\n                \n        except Exception as e:\n            logger.error(f\"Failed to get exchange rate from NBP service: {e}\")\n            # Fallback rate\n            logger.warning(\"Using fallback exchange rate of 4.0 PLN/USD\")\n            return Decimal(\"4.0\")\n    \n    async def _save_exchange_rate(self, db: Session, date: date, rate: Decimal):\n        \"\"\"Save exchange rate to database\"\"\"\n        try:\n            # Check if rate already exists\n            existing = db.query(DailyExchangeRateDB).filter_by(\n                date=date,\n                currency_from=\"USD\",\n                currency_to=\"PLN\"\n            ).first()\n            \n            if existing:\n                existing.rate = rate\n                existing.updated_at = datetime.utcnow()\n            else:\n                exchange_rate = DailyExchangeRateDB(\n                    date=date,\n                    currency_from=\"USD\",\n                    currency_to=\"PLN\",\n                    rate=rate,\n                    source=\"NBP\"\n                )\n                db.add(exchange_rate)\n            \n            db.commit()\n            \n        except Exception as e:\n            logger.error(f\"Failed to save exchange rate: {e}\")\n            db.rollback()\n    \n    async def _get_active_clients(self, db: Session) -> List[Any]:\n        \"\"\"Get all active client organizations\"\"\"\n        from open_webui.models.organization_usage import ClientOrganizationDB\n        \n        return db.query(ClientOrganizationDB).filter_by(is_active=True).all()\n    \n    async def _record_batch_run(\n        self, \n        db: Session, \n        processing_date: date, \n        result: Dict[str, Any]\n    ):\n        \"\"\"Record batch run for tracking and monitoring\"\"\"\n        try:\n            # For now, log the batch run details\n            # In Phase 3, this will save to influxdb_batch_runs table\n            batch_summary = {\n                \"processing_date\": processing_date.isoformat(),\n                \"success\": result.get(\"success\", False),\n                \"clients_processed\": result.get(\"clients_processed\", 0),\n                \"influxdb_records_processed\": result.get(\"influxdb_records_processed\", 0),\n                \"sqlite_summaries_created\": result.get(\"sqlite_summaries_created\", 0),\n                \"data_corrections\": result.get(\"data_corrections\", 0),\n                \"duration_seconds\": result.get(\"total_duration_seconds\", 0),\n                \"data_source\": result.get(\"data_source\", \"unknown\")\n            }\n            \n            logger.info(f\"📋 Batch run summary: {batch_summary}\")\n            \n        except Exception as e:\n            logger.error(f\"Failed to record batch run: {e}\")\n    \n    async def health_check(self) -> Dict[str, Any]:\n        \"\"\"Health check for unified batch processor\"\"\"\n        try:\n            health_status = {\n                \"status\": \"healthy\",\n                \"influxdb_first_enabled\": self.influxdb_first_enabled,\n                \"data_source\": \"influxdb_first\" if self.influxdb_first_enabled else \"legacy_sqlite\",\n                \"services\": {}\n            }\n            \n            # Check InfluxDB service health\n            if self.influxdb_first_enabled:\n                influxdb_health = await influxdb_first_service.health_check()\n                health_status[\"services\"][\"influxdb\"] = influxdb_health\n            \n            # Check NBP service\n            try:\n                test_rate = await self._fetch_exchange_rate(date.today())\n                health_status[\"services\"][\"nbp\"] = {\n                    \"status\": \"operational\",\n                    \"test_rate\": str(test_rate)\n                }\n            except Exception as e:\n                health_status[\"services\"][\"nbp\"] = {\n                    \"status\": \"error\",\n                    \"error\": str(e)\n                }\n            \n            return health_status\n            \n        except Exception as e:\n            return {\n                \"status\": \"unhealthy\",\n                \"error\": str(e),\n                \"influxdb_first_enabled\": self.influxdb_first_enabled\n            }\n\n\n# Module-level functions for backward compatibility\nunified_batch_processor = UnifiedBatchProcessor()\n\n\nasync def run_unified_daily_batch(processing_date: Optional[date] = None) -> Dict[str, Any]:\n    \"\"\"\n    Entry point for unified daily batch processing\n    \n    This function provides backward compatibility while implementing\n    the new InfluxDB-First architecture.\n    \n    Args:\n        processing_date: Date to process (default: yesterday)\n        \n    Returns:\n        Unified batch processing result\n    \"\"\"\n    return await unified_batch_processor.run_daily_batch(processing_date)\n\n\nasync def health_check_unified_batch() -> Dict[str, Any]:\n    \"\"\"Health check for unified batch processor\"\"\"\n    return await unified_batch_processor.health_check()\n"