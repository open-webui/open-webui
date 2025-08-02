"""
InfluxDB vs SQLite Comparison Tool
Validates data consistency between dual-write storage backends
"""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from decimal import Decimal

from open_webui.usage_tracking.services.influxdb_service import InfluxDBService
from open_webui.usage_tracking.models.database import ClientDailyUsageDB, ClientUserDailyUsageDB
from open_webui.models.organization_usage import ClientOrganizationDB
from open_webui.utils.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)


class DataConsistencyValidator:
    """Validates data consistency between InfluxDB and SQLite"""
    
    def __init__(self):
        self.influxdb_service = InfluxDBService()
        self.tolerance_usd = Decimal("0.01")  # 1 cent tolerance for floating point comparisons
        
    async def run_comprehensive_validation(
        self,
        start_date: date,
        end_date: date,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Run comprehensive validation between InfluxDB and SQLite
        
        Args:
            start_date: Start date for comparison
            end_date: End date for comparison (inclusive)
            db: Database session
            
        Returns:
            Detailed comparison report
        """
        if not self.influxdb_service.enabled:
            return {
                "success": False,
                "error": "InfluxDB not enabled",
                "message": "Cannot run comparison without InfluxDB enabled"
            }
        
        if not db:
            db = next(get_db())
            close_db = True
        else:
            close_db = False
        
        try:
            logger.info(f"Starting data validation from {start_date} to {end_date}")
            
            report = {
                "success": True,
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "summary": {
                    "days_checked": 0,
                    "total_discrepancies": 0,
                    "clients_with_discrepancies": set(),
                    "models_with_discrepancies": set()
                },
                "daily_reports": [],
                "client_summaries": {},
                "recommendations": []
            }
            
            # Process each day in the range
            current_date = start_date
            while current_date <= end_date:
                daily_report = await self._validate_single_day(db, current_date)
                report["daily_reports"].append(daily_report)
                report["summary"]["days_checked"] += 1
                
                # Update summary statistics
                if daily_report["discrepancies"]:
                    report["summary"]["total_discrepancies"] += len(daily_report["discrepancies"])
                    for disc in daily_report["discrepancies"]:
                        report["summary"]["clients_with_discrepancies"].add(disc["client_org_id"])
                        report["summary"]["models_with_discrepancies"].add(disc["model"])
                
                current_date += timedelta(days=1)
            
            # Generate client summaries
            report["client_summaries"] = await self._generate_client_summaries(
                db, start_date, end_date
            )
            
            # Convert sets to lists for JSON serialization
            report["summary"]["clients_with_discrepancies"] = list(
                report["summary"]["clients_with_discrepancies"]
            )
            report["summary"]["models_with_discrepancies"] = list(
                report["summary"]["models_with_discrepancies"]
            )
            
            # Generate recommendations
            report["recommendations"] = self._generate_recommendations(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if close_db:
                db.close()
    
    async def _validate_single_day(
        self,
        db: Session,
        check_date: date
    ) -> Dict[str, Any]:
        """Validate data for a single day"""
        
        # Get all active clients
        clients = db.query(ClientOrganizationDB).filter_by(is_active=True).all()
        
        daily_report = {
            "date": check_date.isoformat(),
            "clients_checked": len(clients),
            "discrepancies": [],
            "totals": {
                "influxdb": {"tokens": 0, "cost_usd": 0.0},
                "sqlite": {"tokens": 0, "cost_usd": 0.0}
            }
        }
        
        # Define time range for InfluxDB query
        start_time = datetime.combine(check_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_time = start_time + timedelta(days=1)
        
        for client in clients:
            # Get InfluxDB data
            influx_data = await self.influxdb_service.get_data_for_batch(
                client.id,
                start_time,
                end_time
            )
            
            # Get SQLite data
            sqlite_data = db.query(ClientDailyUsageDB).filter_by(
                client_org_id=client.id,
                usage_date=check_date
            ).all()
            
            # Compare aggregated data by model
            influx_by_model = self._aggregate_influx_data(influx_data)
            sqlite_by_model = self._aggregate_sqlite_data(sqlite_data)
            
            # Find discrepancies
            all_models = set(influx_by_model.keys()) | set(sqlite_by_model.keys())
            
            for model in all_models:
                influx_stats = influx_by_model.get(model, {"tokens": 0, "cost_usd": 0.0})
                sqlite_stats = sqlite_by_model.get(model, {"tokens": 0, "cost_usd": Decimal("0.0")})
                
                tokens_diff = abs(influx_stats["tokens"] - sqlite_stats["tokens"])
                cost_diff = abs(Decimal(str(influx_stats["cost_usd"])) - sqlite_stats["cost_usd"])
                
                if tokens_diff > 0 or cost_diff > self.tolerance_usd:
                    daily_report["discrepancies"].append({
                        "client_org_id": client.id,
                        "client_name": client.name,
                        "model": model,
                        "influxdb": {
                            "tokens": influx_stats["tokens"],
                            "cost_usd": float(influx_stats["cost_usd"])
                        },
                        "sqlite": {
                            "tokens": sqlite_stats["tokens"],
                            "cost_usd": float(sqlite_stats["cost_usd"])
                        },
                        "difference": {
                            "tokens": influx_stats["tokens"] - sqlite_stats["tokens"],
                            "cost_usd": float(Decimal(str(influx_stats["cost_usd"])) - sqlite_stats["cost_usd"])
                        }
                    })
                
                # Update totals
                daily_report["totals"]["influxdb"]["tokens"] += influx_stats["tokens"]
                daily_report["totals"]["influxdb"]["cost_usd"] += influx_stats["cost_usd"]
                daily_report["totals"]["sqlite"]["tokens"] += sqlite_stats["tokens"]
                daily_report["totals"]["sqlite"]["cost_usd"] += float(sqlite_stats["cost_usd"])
        
        return daily_report
    
    def _aggregate_influx_data(self, data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Aggregate InfluxDB data by model"""
        aggregated = {}
        
        for record in data:
            model = record["model"]
            if model not in aggregated:
                aggregated[model] = {"tokens": 0, "cost_usd": 0.0}
            
            aggregated[model]["tokens"] += record["total_tokens"]
            aggregated[model]["cost_usd"] += record["cost_usd"]
        
        return aggregated
    
    def _aggregate_sqlite_data(self, data: List[ClientDailyUsageDB]) -> Dict[str, Dict[str, Any]]:
        """Aggregate SQLite data by model"""
        aggregated = {}
        
        for record in data:
            model = record.model
            if model not in aggregated:
                aggregated[model] = {"tokens": 0, "cost_usd": Decimal("0.0")}
            
            aggregated[model]["tokens"] += record.total_tokens
            aggregated[model]["cost_usd"] += record.total_cost
        
        return aggregated
    
    async def _generate_client_summaries(
        self,
        db: Session,
        start_date: date,
        end_date: date
    ) -> Dict[str, Dict[str, Any]]:
        """Generate summary statistics for each client"""
        summaries = {}
        
        clients = db.query(ClientOrganizationDB).filter_by(is_active=True).all()
        
        for client in clients:
            # SQLite totals
            sqlite_totals = db.query(
                func.sum(ClientDailyUsageDB.total_tokens).label("tokens"),
                func.sum(ClientDailyUsageDB.total_cost).label("cost")
            ).filter(
                ClientDailyUsageDB.client_org_id == client.id,
                ClientDailyUsageDB.usage_date >= start_date,
                ClientDailyUsageDB.usage_date <= end_date
            ).first()
            
            # InfluxDB totals
            influx_total_tokens = 0
            influx_total_cost = 0.0
            
            current_date = start_date
            while current_date <= end_date:
                start_time = datetime.combine(current_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                end_time = start_time + timedelta(days=1)
                
                influx_data = await self.influxdb_service.get_data_for_batch(
                    client.id,
                    start_time,
                    end_time
                )
                
                for record in influx_data:
                    influx_total_tokens += record["total_tokens"]
                    influx_total_cost += record["cost_usd"]
                
                current_date += timedelta(days=1)
            
            summaries[client.id] = {
                "client_name": client.name,
                "sqlite": {
                    "total_tokens": sqlite_totals.tokens or 0,
                    "total_cost_usd": float(sqlite_totals.cost or 0)
                },
                "influxdb": {
                    "total_tokens": influx_total_tokens,
                    "total_cost_usd": influx_total_cost
                },
                "difference": {
                    "tokens": influx_total_tokens - (sqlite_totals.tokens or 0),
                    "cost_usd": influx_total_cost - float(sqlite_totals.cost or 0)
                }
            }
        
        return summaries
    
    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        if report["summary"]["total_discrepancies"] == 0:
            recommendations.append(
                "✅ No discrepancies found. Data is consistent between InfluxDB and SQLite."
            )
            recommendations.append(
                "Consider disabling dual-write mode to improve performance."
            )
        else:
            discrepancy_rate = (
                report["summary"]["total_discrepancies"] / 
                (report["summary"]["days_checked"] * len(report["client_summaries"]))
            )
            
            if discrepancy_rate > 0.1:  # More than 10% discrepancy rate
                recommendations.append(
                    "⚠️ High discrepancy rate detected. Investigate webhook processing pipeline."
                )
                recommendations.append(
                    "Keep dual-write mode enabled until issues are resolved."
                )
            else:
                recommendations.append(
                    "Minor discrepancies found. These may be due to timing differences."
                )
                recommendations.append(
                    "Monitor for a few more days before disabling dual-write mode."
                )
            
            # Client-specific recommendations
            if len(report["summary"]["clients_with_discrepancies"]) == 1:
                client_id = report["summary"]["clients_with_discrepancies"][0]
                recommendations.append(
                    f"Discrepancies isolated to single client ({client_id}). "
                    "Check client-specific configuration."
                )
            
            # Model-specific recommendations
            if len(report["summary"]["models_with_discrepancies"]) == 1:
                model = report["summary"]["models_with_discrepancies"][0]
                recommendations.append(
                    f"Discrepancies isolated to single model ({model}). "
                    "Check model-specific webhook handling."
                )
        
        return recommendations
    
    async def generate_discrepancy_report(
        self,
        output_path: str,
        days_back: int = 7
    ) -> str:
        """
        Generate a detailed discrepancy report and save to file
        
        Args:
            output_path: Path to save the report
            days_back: Number of days to analyze
            
        Returns:
            Path to the generated report
        """
        end_date = date.today() - timedelta(days=1)  # Yesterday
        start_date = end_date - timedelta(days=days_back - 1)
        
        report = await self.run_comprehensive_validation(start_date, end_date)
        
        # Format report as markdown
        markdown_content = f"""# InfluxDB vs SQLite Data Validation Report

## Summary
- **Period**: {report['period']['start']} to {report['period']['end']}
- **Days Checked**: {report['summary']['days_checked']}
- **Total Discrepancies**: {report['summary']['total_discrepancies']}
- **Clients with Discrepancies**: {len(report['summary']['clients_with_discrepancies'])}
- **Models with Discrepancies**: {len(report['summary']['models_with_discrepancies'])}

## Recommendations
"""
        
        for rec in report.get('recommendations', []):
            markdown_content += f"- {rec}\n"
        
        markdown_content += "\n## Daily Discrepancies\n"
        
        for daily in report['daily_reports']:
            if daily['discrepancies']:
                markdown_content += f"\n### {daily['date']}\n"
                markdown_content += f"Found {len(daily['discrepancies'])} discrepancies:\n\n"
                
                for disc in daily['discrepancies']:
                    markdown_content += f"- **{disc['client_name']}** - {disc['model']}:\n"
                    markdown_content += f"  - InfluxDB: {disc['influxdb']['tokens']} tokens, ${disc['influxdb']['cost_usd']:.4f}\n"
                    markdown_content += f"  - SQLite: {disc['sqlite']['tokens']} tokens, ${disc['sqlite']['cost_usd']:.4f}\n"
                    markdown_content += f"  - Difference: {disc['difference']['tokens']} tokens, ${disc['difference']['cost_usd']:.4f}\n\n"
        
        markdown_content += "\n## Client Summaries\n"
        
        for client_id, summary in report['client_summaries'].items():
            if abs(summary['difference']['cost_usd']) > 0.01:
                markdown_content += f"\n### {summary['client_name']} ({client_id})\n"
                markdown_content += f"- InfluxDB Total: {summary['influxdb']['total_tokens']} tokens, ${summary['influxdb']['total_cost_usd']:.2f}\n"
                markdown_content += f"- SQLite Total: {summary['sqlite']['total_tokens']} tokens, ${summary['sqlite']['total_cost_usd']:.2f}\n"
                markdown_content += f"- Difference: {summary['difference']['tokens']} tokens, ${summary['difference']['cost_usd']:.2f}\n"
        
        # Save report
        with open(output_path, 'w') as f:
            f.write(markdown_content)
        
        logger.info(f"Validation report saved to {output_path}")
        return output_path


# Convenience functions for command-line usage
async def validate_today():
    """Validate today's data"""
    validator = DataConsistencyValidator()
    today = date.today()
    report = await validator.run_comprehensive_validation(today, today)
    return report


async def validate_last_week():
    """Validate last 7 days of data"""
    validator = DataConsistencyValidator()
    await validator.generate_discrepancy_report(
        "influxdb_sqlite_validation_report.md",
        days_back=7
    )


if __name__ == "__main__":
    # Run validation for last week
    asyncio.run(validate_last_week())