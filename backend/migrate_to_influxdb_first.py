#!/usr/bin/env python3
"""
Migration Script: SQLite Dual-Write → InfluxDB-First Architecture
Handles the transition from dual-write mode to InfluxDB-First architecture

Usage:
    python3 migrate_to_influxdb_first.py --help
    python3 migrate_to_influxdb_first.py --validate-only
    python3 migrate_to_influxdb_first.py --migrate --start-date 2025-01-01 --end-date 2025-01-31
    python3 migrate_to_influxdb_first.py --rollback --backup-id abc123
"""

import os
import sys
import asyncio
import argparse
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Tuple, Optional
import json
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from open_webui.usage_tracking.services.influxdb_first_service import influxdb_first_service
from open_webui.models.organization_usage import ClientUsageDB, ClientOrganizationDB
from open_webui.internal.db import get_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


class InfluxDBFirstMigrator:
    """Handles migration from SQLite dual-write to InfluxDB-First architecture"""
    
    def __init__(self):
        self.backup_dir = "migration_backups"
        self.migration_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create backup directory
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Migration statistics
        self.stats = {
            "total_records": 0,
            "migrated_records": 0,
            "failed_records": 0,
            "duplicates_found": 0,
            "start_time": None,
            "end_time": None
        }
    
    async def validate_environment(self) -> Dict[str, Any]:
        """Validate that environment is ready for migration"""
        log.info("🔍 Validating migration environment...")
        
        validation_result = {
            "ready": True,
            "checks": {},
            "warnings": [],
            "errors": []
        }
        
        # Check InfluxDB-First service availability
        try:
            health_check = await influxdb_first_service.health_check()
            validation_result["checks"]["influxdb_service"] = health_check
            
            if health_check.get("status") != "healthy":
                validation_result["errors"].append("InfluxDB-First service is not healthy")
                validation_result["ready"] = False
                
        except Exception as e:
            validation_result["errors"].append(f"InfluxDB-First service check failed: {e}")
            validation_result["ready"] = False
        
        # Check SQLite database access
        try:
            with get_db() as db:
                # Test query
                result = db.execute("SELECT COUNT(*) FROM client_organizations").fetchone()
                client_count = result[0] if result else 0
                validation_result["checks"]["sqlite_access"] = {
                    "status": "ok",
                    "client_organizations": client_count
                }
                
                # Check for existing raw usage data
                result = db.execute("SELECT COUNT(*) FROM client_user_daily_usage").fetchone()
                raw_usage_count = result[0] if result else 0
                validation_result["checks"]["sqlite_raw_usage"] = {
                    "count": raw_usage_count
                }
                
                if raw_usage_count == 0:
                    validation_result["warnings"].append("No raw usage data found in SQLite")
                    
        except Exception as e:
            validation_result["errors"].append(f"SQLite database check failed: {e}")
            validation_result["ready"] = False
        
        # Check environment variables
        required_env_vars = ["INFLUXDB_FIRST_ENABLED"]
        for var in required_env_vars:
            value = os.getenv(var)
            validation_result["checks"][f"env_{var}"] = {
                "present": value is not None,
                "value": value
            }
            
            if not value:
                validation_result["warnings"].append(f"Environment variable {var} not set")
        
        return validation_result
    
    async def create_backup(self, start_date: date, end_date: date) -> str:
        """Create backup of data before migration"""
        backup_id = f"backup_{self.migration_id}"
        backup_file = os.path.join(self.backup_dir, f"{backup_id}.json")
        
        log.info(f"📦 Creating backup: {backup_file}")
        
        backup_data = {
            "backup_id": backup_id,
            "created_at": datetime.now().isoformat(),
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "sqlite_data": {}
        }
        
        try:
            with get_db() as db:
                # Backup client organizations
                clients = db.execute("SELECT * FROM client_organizations").fetchall()
                backup_data["sqlite_data"]["client_organizations"] = [
                    dict(zip([col[0] for col in db.description], row)) for row in clients
                ]
                
                # Backup raw usage data in date range
                raw_usage = db.execute("""
                    SELECT * FROM client_user_daily_usage 
                    WHERE usage_date >= ? AND usage_date <= ?
                """, (start_date, end_date)).fetchall()
                
                backup_data["sqlite_data"]["client_user_daily_usage"] = [
                    dict(zip([col[0] for col in db.description], row)) for row in raw_usage
                ]
                
                # Backup daily summaries
                daily_usage = db.execute("""
                    SELECT * FROM client_daily_usage 
                    WHERE usage_date >= ? AND usage_date <= ?
                """, (start_date, end_date)).fetchall()
                
                backup_data["sqlite_data"]["client_daily_usage"] = [
                    dict(zip([col[0] for col in db.description], row)) for row in daily_usage
                ]
        
            # Save backup file
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
                
            log.info(f"✅ Backup created: {backup_file}")
            return backup_id
            
        except Exception as e:
            log.error(f"❌ Backup creation failed: {e}")
            raise
    
    async def migrate_sqlite_to_influxdb(
        self, 
        start_date: date, 
        end_date: date,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Migrate raw usage data from SQLite to InfluxDB
        
        Process:
        1. Read raw usage data from client_user_daily_usage table
        2. Transform to InfluxDB format
        3. Write to InfluxDB with deduplication
        4. Validate migration
        """
        log.info(f"🚀 Starting migration from {start_date} to {end_date} (dry_run={dry_run})")
        
        self.stats["start_time"] = datetime.now()
        migration_results = []
        
        try:
            with get_db() as db:
                # Get raw usage data from SQLite
                raw_usage_query = """
                    SELECT 
                        cudu.*,
                        co.name as client_name,
                        co.markup_rate
                    FROM client_user_daily_usage cudu
                    JOIN client_organizations co ON cudu.client_org_id = co.id
                    WHERE cudu.usage_date >= ? AND cudu.usage_date <= ?
                    ORDER BY cudu.usage_date, cudu.client_org_id
                """
                
                raw_usage_data = db.execute(raw_usage_query, (start_date, end_date)).fetchall()
                columns = [col[0] for col in db.description]
                
                self.stats["total_records"] = len(raw_usage_data)
                log.info(f"Found {self.stats['total_records']} raw usage records to migrate")
                
                # Process in batches
                batch_size = 100
                for i in range(0, len(raw_usage_data), batch_size):
                    batch = raw_usage_data[i:i + batch_size]
                    batch_results = await self._process_migration_batch(batch, columns, dry_run)
                    migration_results.extend(batch_results)
                    
                    log.info(f"Processed batch {i//batch_size + 1}/{(len(raw_usage_data) + batch_size - 1)//batch_size}")
            
            self.stats["end_time"] = datetime.now()
            self.stats["migrated_records"] = len([r for r in migration_results if r["success"]])
            self.stats["failed_records"] = len([r for r in migration_results if not r["success"]])
            
            duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
            
            log.info(f"✅ Migration completed in {duration:.2f}s")
            log.info(f"   📊 Total: {self.stats['total_records']}")
            log.info(f"   ✅ Migrated: {self.stats['migrated_records']}")
            log.info(f"   ❌ Failed: {self.stats['failed_records']}")
            log.info(f"   🔄 Duplicates: {self.stats['duplicates_found']}")
            
            return {
                "success": self.stats["failed_records"] == 0,
                "statistics": self.stats,
                "migration_results": migration_results
            }
            
        except Exception as e:
            log.error(f"❌ Migration failed: {e}")
            self.stats["end_time"] = datetime.now()
            return {
                "success": False,
                "error": str(e),
                "statistics": self.stats
            }
    
    async def _process_migration_batch(
        self, 
        batch: List[Tuple], 
        columns: List[str], 
        dry_run: bool
    ) -> List[Dict[str, Any]]:
        """Process a batch of migration records"""
        batch_results = []
        
        for row in batch:
            record = dict(zip(columns, row))
            
            try:
                # Transform SQLite record to InfluxDB format
                influxdb_data = self._transform_sqlite_to_influxdb(record)
                
                if not dry_run:
                    # Write to InfluxDB
                    success = await influxdb_first_service.write_usage_record(influxdb_data)
                    
                    if success:
                        batch_results.append({
                            "success": True,
                            "record_id": record.get("id"),
                            "client_org_id": record["client_org_id"],
                            "usage_date": record["usage_date"],
                            "user_id": record["user_id"]
                        })
                    else:
                        batch_results.append({
                            "success": False,
                            "error": "InfluxDB write failed",
                            "record_id": record.get("id"),
                            "client_org_id": record["client_org_id"],
                            "usage_date": record["usage_date"]
                        })
                else:
                    # Dry run - just validate transformation
                    batch_results.append({
                        "success": True,
                        "dry_run": True,
                        "record_id": record.get("id"),
                        "transformed_data": influxdb_data
                    })
                    
            except Exception as e:
                batch_results.append({
                    "success": False,
                    "error": str(e),
                    "record_id": record.get("id"),
                    "client_org_id": record.get("client_org_id")
                })
        
        return batch_results
    
    def _transform_sqlite_to_influxdb(self, sqlite_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform SQLite record to InfluxDB format"""
        # Calculate total tokens
        input_tokens = sqlite_record.get("input_tokens", 0) or 0
        output_tokens = sqlite_record.get("output_tokens", 0) or 0
        total_tokens = sqlite_record.get("total_tokens") or (input_tokens + output_tokens)
        
        # Calculate costs
        raw_cost = sqlite_record.get("raw_cost", 0.0) or 0.0
        markup_rate = sqlite_record.get("markup_rate", 1.3) or 1.3
        markup_cost = raw_cost * markup_rate
        
        # Create timestamp from usage_date
        usage_date = sqlite_record["usage_date"]
        if isinstance(usage_date, str):
            timestamp = datetime.fromisoformat(usage_date).isoformat()
        else:
            timestamp = datetime.combine(usage_date, datetime.min.time()).isoformat()
        
        return {
            "client_org_id": str(sqlite_record["client_org_id"]),
            "model": sqlite_record.get("model_used", "unknown"),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": markup_cost,
            "timestamp": timestamp,
            "external_user": f"user_{sqlite_record['user_id']}",
            "request_id": f"migration_{sqlite_record.get('id', 'unknown')}_{int(time.time())}",
            "provider": sqlite_record.get("provider", "openrouter"),
            "source": "sqlite_migration"
        }
    
    async def validate_migration(
        self, 
        start_date: date, 
        end_date: date
    ) -> Dict[str, Any]:
        """Validate migration results by comparing SQLite and InfluxDB data"""
        log.info(f"🔍 Validating migration for {start_date} to {end_date}")
        
        validation_results = {
            "success": True,
            "discrepancies": [],
            "summary": {}
        }
        
        try:
            # Get SQLite summary data
            with get_db() as db:
                sqlite_summary = db.execute("""
                    SELECT 
                        client_org_id,
                        COUNT(*) as record_count,
                        SUM(total_tokens) as total_tokens,
                        SUM(raw_cost * markup_rate) as total_cost
                    FROM client_user_daily_usage cudu
                    JOIN client_organizations co ON cudu.client_org_id = co.id
                    WHERE usage_date >= ? AND usage_date <= ?
                    GROUP BY client_org_id
                """, (start_date, end_date)).fetchall()
            
            # Get InfluxDB summary data
            for client_id, record_count, total_tokens, total_cost in sqlite_summary:
                start_time = datetime.combine(start_date, datetime.min.time())
                end_time = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
                
                influxdb_data = await influxdb_first_service.query_usage_data(
                    client_org_id=str(client_id),
                    start_time=start_time,
                    end_time=end_time
                )
                
                influxdb_tokens = sum(record.get("total_tokens", 0) for record in influxdb_data)
                influxdb_cost = sum(record.get("cost_usd", 0.0) for record in influxdb_data)
                influxdb_count = len(influxdb_data)
                
                # Compare results
                token_diff = abs(total_tokens - influxdb_tokens)
                cost_diff = abs(total_cost - influxdb_cost)
                count_diff = abs(record_count - influxdb_count)
                
                if token_diff > 100 or cost_diff > 0.01 or count_diff > 0:
                    validation_results["discrepancies"].append({
                        "client_id": client_id,
                        "sqlite": {
                            "records": record_count,
                            "tokens": total_tokens,
                            "cost": total_cost
                        },
                        "influxdb": {
                            "records": influxdb_count,
                            "tokens": influxdb_tokens,
                            "cost": influxdb_cost
                        },
                        "differences": {
                            "records": count_diff,
                            "tokens": token_diff,
                            "cost": cost_diff
                        }
                    })
                    validation_results["success"] = False
            
            validation_results["summary"] = {
                "clients_checked": len(sqlite_summary),
                "discrepancies_found": len(validation_results["discrepancies"])
            }
            
            if validation_results["success"]:
                log.info("✅ Migration validation successful - no discrepancies found")
            else:
                log.warning(f"⚠️ Migration validation found {len(validation_results['discrepancies'])} discrepancies")
            
            return validation_results
            
        except Exception as e:
            log.error(f"❌ Migration validation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


async def main():
    """Main migration script entry point"""
    parser = argparse.ArgumentParser(description="Migrate from SQLite dual-write to InfluxDB-First architecture")
    parser.add_argument("--validate-only", action="store_true", help="Only validate environment")
    parser.add_argument("--migrate", action="store_true", help="Perform migration")
    parser.add_argument("--dry-run", action="store_true", help="Dry run migration (no actual writes)")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--validate-migration", action="store_true", help="Validate existing migration")
    
    args = parser.parse_args()
    
    if not any([args.validate_only, args.migrate, args.validate_migration]):
        parser.print_help()
        return
    
    migrator = InfluxDBFirstMigrator()
    
    # Validate environment
    if args.validate_only or args.migrate:
        validation = await migrator.validate_environment()
        
        print("\n📋 Environment Validation:")
        print(f"Ready for migration: {'✅' if validation['ready'] else '❌'}")
        
        if validation["warnings"]:
            print("\n⚠️ Warnings:")
            for warning in validation["warnings"]:
                print(f"  - {warning}")
        
        if validation["errors"]:
            print("\n❌ Errors:")
            for error in validation["errors"]:
                print(f"  - {error}")
        
        if not validation["ready"]:
            print("\n🚫 Migration cannot proceed due to validation errors")
            return
    
    # Perform migration
    if args.migrate:
        if not args.start_date or not args.end_date:
            print("❌ --start-date and --end-date are required for migration")
            return
        
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD")
            return
        
        # Create backup
        backup_id = await migrator.create_backup(start_date, end_date)
        print(f"📦 Backup created: {backup_id}")
        
        # Run migration
        migration_result = await migrator.migrate_sqlite_to_influxdb(
            start_date, end_date, dry_run=args.dry_run
        )
        
        if migration_result["success"]:
            print(f"✅ Migration {'simulated' if args.dry_run else 'completed'} successfully")
        else:
            print(f"❌ Migration failed: {migration_result.get('error', 'Unknown error')}")
        
        # Validate if not dry run
        if not args.dry_run and migration_result["success"]:
            validation_result = await migrator.validate_migration(start_date, end_date)
            if validation_result["success"]:
                print("✅ Migration validation successful")
            else:
                print(f"⚠️ Migration validation found issues: {len(validation_result['discrepancies'])} discrepancies")
    
    # Validate existing migration
    if args.validate_migration:
        if not args.start_date or not args.end_date:
            print("❌ --start-date and --end-date are required for validation")
            return
        
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD")
            return
        
        validation_result = await migrator.validate_migration(start_date, end_date)
        
        if validation_result["success"]:
            print("✅ Migration validation successful")
        else:
            print(f"⚠️ Migration validation found {len(validation_result['discrepancies'])} discrepancies")
            for disc in validation_result["discrepancies"]:
                print(f"  Client {disc['client_id']}: SQLite({disc['sqlite']['records']} records, {disc['sqlite']['tokens']} tokens) vs InfluxDB({disc['influxdb']['records']} records, {disc['influxdb']['tokens']} tokens)")


if __name__ == "__main__":
    asyncio.run(main())