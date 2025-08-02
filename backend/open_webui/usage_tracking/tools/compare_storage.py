#!/usr/bin/env python3
"""
Command-line tool for comparing InfluxDB and SQLite data
Usage: python compare_storage.py [command] [options]
"""
import asyncio
import argparse
import sys
import os
from datetime import date, datetime, timedelta
import json

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))

from open_webui.utils.influxdb_sqlite_comparison import DataConsistencyValidator


async def compare_today():
    """Compare today's data between InfluxDB and SQLite"""
    print("Comparing today's data...")
    validator = DataConsistencyValidator()
    today = date.today()
    
    report = await validator.run_comprehensive_validation(today, today)
    
    if report["success"]:
        print(f"\n✅ Validation completed successfully")
        print(f"Discrepancies found: {report['summary']['total_discrepancies']}")
        
        if report['summary']['total_discrepancies'] > 0:
            print("\nDiscrepancy details:")
            for daily in report['daily_reports']:
                for disc in daily['discrepancies']:
                    print(f"  - {disc['client_name']} / {disc['model']}:")
                    print(f"    InfluxDB: {disc['influxdb']['tokens']} tokens, ${disc['influxdb']['cost_usd']:.4f}")
                    print(f"    SQLite:   {disc['sqlite']['tokens']} tokens, ${disc['sqlite']['cost_usd']:.4f}")
                    print(f"    Diff:     {disc['difference']['tokens']} tokens, ${disc['difference']['cost_usd']:.4f}")
    else:
        print(f"\n❌ Validation failed: {report.get('error', 'Unknown error')}")


async def compare_date_range(start_date: str, end_date: str):
    """Compare data for a specific date range"""
    validator = DataConsistencyValidator()
    
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    print(f"Comparing data from {start} to {end}...")
    
    report = await validator.run_comprehensive_validation(start, end)
    
    if report["success"]:
        print(f"\n✅ Validation completed successfully")
        print(f"Days checked: {report['summary']['days_checked']}")
        print(f"Total discrepancies: {report['summary']['total_discrepancies']}")
        
        print("\nRecommendations:")
        for rec in report['recommendations']:
            print(f"  - {rec}")
            
        # Show summary by client
        print("\nClient Summary:")
        for client_id, summary in report['client_summaries'].items():
            if abs(summary['difference']['cost_usd']) > 0.01:
                print(f"  {summary['client_name']}:")
                print(f"    Token difference: {summary['difference']['tokens']}")
                print(f"    Cost difference: ${summary['difference']['cost_usd']:.2f}")
    else:
        print(f"\n❌ Validation failed: {report.get('error', 'Unknown error')}")


async def generate_report(days: int, output_path: str):
    """Generate a detailed comparison report"""
    validator = DataConsistencyValidator()
    
    print(f"Generating report for last {days} days...")
    
    report_path = await validator.generate_discrepancy_report(output_path, days_back=days)
    
    print(f"\n✅ Report generated: {report_path}")
    
    # Show summary from the report
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)
    
    report = await validator.run_comprehensive_validation(start_date, end_date)
    
    if report["success"]:
        print(f"\nSummary:")
        print(f"  - Period: {start_date} to {end_date}")
        print(f"  - Total discrepancies: {report['summary']['total_discrepancies']}")
        print(f"  - Clients affected: {len(report['summary']['clients_with_discrepancies'])}")
        print(f"  - Models affected: {len(report['summary']['models_with_discrepancies'])}")


async def export_json(days: int, output_path: str):
    """Export comparison data as JSON"""
    validator = DataConsistencyValidator()
    
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)
    
    print(f"Exporting comparison data for {start_date} to {end_date}...")
    
    report = await validator.run_comprehensive_validation(start_date, end_date)
    
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n✅ JSON data exported to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Compare InfluxDB and SQLite data for consistency validation"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Today command
    subparsers.add_parser("today", help="Compare today's data")
    
    # Date range command
    range_parser = subparsers.add_parser("range", help="Compare a date range")
    range_parser.add_argument("start", help="Start date (YYYY-MM-DD)")
    range_parser.add_argument("end", help="End date (YYYY-MM-DD)")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate a detailed report")
    report_parser.add_argument("-d", "--days", type=int, default=7, help="Number of days to analyze (default: 7)")
    report_parser.add_argument("-o", "--output", default="comparison_report.md", help="Output file path")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export comparison data as JSON")
    export_parser.add_argument("-d", "--days", type=int, default=7, help="Number of days to analyze (default: 7)")
    export_parser.add_argument("-o", "--output", default="comparison_data.json", help="Output file path")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Run the appropriate command
    if args.command == "today":
        asyncio.run(compare_today())
    elif args.command == "range":
        asyncio.run(compare_date_range(args.start, args.end))
    elif args.command == "report":
        asyncio.run(generate_report(args.days, args.output))
    elif args.command == "export":
        asyncio.run(export_json(args.days, args.output))


if __name__ == "__main__":
    main()