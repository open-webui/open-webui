#!/usr/bin/env python3
"""
Database Monitoring Script for Client Organization System
Monitors database health, performance, and growth patterns
"""
import sys
import os
import asyncio
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
import logging

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("Warning: psycopg2 not installed. Database-specific queries will not work.")
    psycopg2 = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseMonitor:
    """Database monitoring and alerting system"""
    
    def __init__(self, db_config: Optional[Dict] = None):
        self.db_config = db_config or {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'mai_db'),
            'user': os.getenv('DB_USER', 'mai_user'),
            'password': os.getenv('DB_PASSWORD', '')
        }
        
        # Alert thresholds
        self.thresholds = {
            'db_size_gb': float(os.getenv('ALERT_DB_SIZE_GB', '5.0')),
            'daily_records_spike': float(os.getenv('ALERT_RECORDS_SPIKE', '1.5')),
            'query_time_seconds': float(os.getenv('ALERT_QUERY_TIME', '5.0')),
            'disk_space_percent': float(os.getenv('ALERT_DISK_SPACE', '10.0')),
            'connection_percent': float(os.getenv('ALERT_CONNECTIONS', '80.0'))
        }
    
    def get_db_connection(self):
        """Get database connection"""
        if not psycopg2:
            raise ImportError("psycopg2 not available")
        
        return psycopg2.connect(**self.db_config)
    
    def check_database_size(self) -> Dict[str, Any]:
        """Check database size and growth"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Total database size
                    cur.execute("""
                        SELECT pg_size_pretty(pg_database_size(%s)) as size_pretty,
                               pg_database_size(%s) as size_bytes
                    """, (self.db_config['database'], self.db_config['database']))
                    
                    db_size = cur.fetchone()
                    
                    # Table sizes
                    cur.execute("""
                        SELECT 
                            schemaname,
                            tablename,
                            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size_pretty,
                            pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                        FROM pg_tables 
                        WHERE schemaname = 'public'
                        ORDER BY size_bytes DESC
                    """)
                    
                    table_sizes = cur.fetchall()
                    
                    size_gb = db_size['size_bytes'] / (1024**3)
                    alert = size_gb > self.thresholds['db_size_gb']
                    
                    return {
                        'status': 'warning' if alert else 'ok',
                        'database_size': db_size['size_pretty'],
                        'database_size_gb': round(size_gb, 2),
                        'threshold_gb': self.thresholds['db_size_gb'],
                        'alert': alert,
                        'table_sizes': [dict(row) for row in table_sizes[:5]]  # Top 5 tables
                    }
                    
        except Exception as e:
            logger.error(f"Database size check failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def check_record_growth(self) -> Dict[str, Any]:
        """Check daily record growth patterns"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Daily usage record counts for last 30 days
                    cur.execute("""
                        SELECT 
                            usage_date,
                            COUNT(*) as daily_records
                        FROM client_usage 
                        WHERE usage_date >= CURRENT_DATE - INTERVAL '30 days'
                        GROUP BY usage_date
                        ORDER BY usage_date DESC
                        LIMIT 30
                    """)
                    
                    daily_counts = cur.fetchall()
                    
                    if not daily_counts:
                        return {'status': 'ok', 'message': 'No recent usage data'}
                    
                    # Calculate average and detect spikes
                    recent_counts = [row['daily_records'] for row in daily_counts[:7]]
                    avg_recent = sum(recent_counts) / len(recent_counts)
                    
                    older_counts = [row['daily_records'] for row in daily_counts[7:]]
                    avg_older = sum(older_counts) / len(older_counts) if older_counts else avg_recent
                    
                    spike_ratio = avg_recent / avg_older if avg_older > 0 else 1.0
                    alert = spike_ratio > self.thresholds['daily_records_spike']
                    
                    return {
                        'status': 'warning' if alert else 'ok',
                        'avg_daily_recent': round(avg_recent),
                        'avg_daily_older': round(avg_older),
                        'spike_ratio': round(spike_ratio, 2),
                        'threshold_ratio': self.thresholds['daily_records_spike'],
                        'alert': alert,
                        'daily_data': [dict(row) for row in daily_counts[:7]]
                    }
                    
        except Exception as e:
            logger.error(f"Record growth check failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def check_query_performance(self) -> Dict[str, Any]:
        """Check slow queries and performance"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Check if pg_stat_statements is available
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                        ) as has_pg_stat_statements
                    """)
                    
                    has_extension = cur.fetchone()['has_pg_stat_statements']
                    
                    if not has_extension:
                        return {
                            'status': 'info', 
                            'message': 'pg_stat_statements extension not available'
                        }
                    
                    # Get slow queries
                    cur.execute("""
                        SELECT 
                            substring(query, 1, 100) as query_sample,
                            calls,
                            total_exec_time,
                            mean_exec_time,
                            rows
                        FROM pg_stat_statements 
                        WHERE mean_exec_time > %s * 1000  -- Convert to milliseconds
                        ORDER BY mean_exec_time DESC 
                        LIMIT 10
                    """, (self.thresholds['query_time_seconds'],))
                    
                    slow_queries = cur.fetchall()
                    
                    alert = len(slow_queries) > 0
                    
                    return {
                        'status': 'warning' if alert else 'ok',
                        'slow_query_count': len(slow_queries),
                        'threshold_seconds': self.thresholds['query_time_seconds'],
                        'alert': alert,
                        'slow_queries': [dict(row) for row in slow_queries]
                    }
                    
        except Exception as e:
            logger.error(f"Query performance check failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def check_client_usage_stats(self) -> Dict[str, Any]:
        """Check client usage statistics"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Active clients
                    cur.execute("SELECT COUNT(*) as active_clients FROM client_organizations WHERE is_active = 1")
                    active_clients = cur.fetchone()['active_clients']
                    
                    # Total users mapped
                    cur.execute("SELECT COUNT(*) as total_users FROM user_client_mapping WHERE is_active = 1")
                    total_users = cur.fetchone()['total_users']
                    
                    # Usage today
                    cur.execute("""
                        SELECT 
                            COUNT(*) as requests_today,
                            SUM(total_tokens) as tokens_today,
                            SUM(markup_cost) as cost_today
                        FROM client_usage 
                        WHERE usage_date = CURRENT_DATE
                    """)
                    
                    today_stats = cur.fetchone()
                    
                    # Top clients by usage (last 7 days)
                    cur.execute("""
                        SELECT 
                            co.name as client_name,
                            COUNT(*) as requests,
                            SUM(cu.markup_cost) as total_cost
                        FROM client_usage cu
                        JOIN client_organizations co ON cu.client_org_id = co.id
                        WHERE cu.usage_date >= CURRENT_DATE - INTERVAL '7 days'
                        GROUP BY co.name
                        ORDER BY total_cost DESC
                        LIMIT 5
                    """)
                    
                    top_clients = cur.fetchall()
                    
                    return {
                        'status': 'ok',
                        'active_clients': active_clients,
                        'total_users': total_users,
                        'today_stats': {
                            'requests': today_stats['requests_today'] or 0,
                            'tokens': today_stats['tokens_today'] or 0,
                            'cost': float(today_stats['cost_today'] or 0)
                        },
                        'top_clients_7days': [dict(row) for row in top_clients]
                    }
                    
        except Exception as e:
            logger.error(f"Client usage stats check failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        logger.info("🔍 Generating database health report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'database_size': self.check_database_size(),
            'record_growth': self.check_record_growth(),
            'query_performance': self.check_query_performance(),
            'client_stats': self.check_client_usage_stats(),
            'overall_status': 'ok'
        }
        
        # Determine overall status
        alerts = []
        for check_name, check_result in report.items():
            if isinstance(check_result, dict):
                if check_result.get('status') == 'error':
                    report['overall_status'] = 'error'
                    alerts.append(f"{check_name}: {check_result.get('error', 'Unknown error')}")
                elif check_result.get('alert'):
                    if report['overall_status'] != 'error':
                        report['overall_status'] = 'warning'
                    alerts.append(f"{check_name}: Alert triggered")
        
        report['alerts'] = alerts
        report['alert_count'] = len(alerts)
        
        return report
    
    def send_alert(self, alert_type: str, message: str, details: Dict = None):
        """Send alert notification"""
        alert_data = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'message': message,
            'details': details or {}
        }
        
        # Log alert
        logger.warning(f"🚨 ALERT [{alert_type}]: {message}")
        
        # Here you would integrate with your alerting system
        # Examples: Slack, email, PagerDuty, etc.
        
        # Example Slack notification:
        # slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        # if slack_webhook:
        #     requests.post(slack_webhook, json={
        #         'text': f"MAI Database Alert: {message}",
        #         'attachments': [{'text': json.dumps(details, indent=2)}]
        #     })

def main():
    """Main monitoring script"""
    print("📊 MAI Database Monitor")
    print("=" * 50)
    
    # Initialize monitor
    monitor = DatabaseMonitor()
    
    try:
        # Generate health report
        report = monitor.generate_health_report()
        
        # Print summary
        print(f"\n🏥 Overall Status: {report['overall_status'].upper()}")
        print(f"📅 Report Time: {report['timestamp']}")
        
        if report['alert_count'] > 0:
            print(f"\n🚨 Alerts ({report['alert_count']}):")
            for alert in report['alerts']:
                print(f"  • {alert}")
        
        # Print detailed results
        print(f"\n📊 Database Size:")
        db_size = report['database_size']
        print(f"  Size: {db_size.get('database_size', 'Unknown')}")
        print(f"  Status: {db_size.get('status', 'Unknown')}")
        
        print(f"\n📈 Record Growth:")
        growth = report['record_growth']  
        print(f"  Recent avg: {growth.get('avg_daily_recent', 'Unknown')} records/day")
        print(f"  Status: {growth.get('status', 'Unknown')}")
        
        print(f"\n⚡ Query Performance:")
        perf = report['query_performance']
        print(f"  Slow queries: {perf.get('slow_query_count', 'Unknown')}")
        print(f"  Status: {perf.get('status', 'Unknown')}")
        
        print(f"\n👥 Client Statistics:")
        stats = report['client_stats']
        print(f"  Active clients: {stats.get('active_clients', 'Unknown')}")
        print(f"  Total users: {stats.get('total_users', 'Unknown')}")
        
        if stats.get('today_stats'):
            today = stats['today_stats']
            print(f"  Today: {today['requests']} requests, ${today['cost']:.2f}")
        
        # Save report to file
        report_file = f"/tmp/mai_health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Full report saved: {report_file}")
        
        # Send alerts if needed
        if report['overall_status'] in ['warning', 'error']:
            monitor.send_alert(
                report['overall_status'].upper(),
                f"Database health check: {report['alert_count']} alerts detected",
                {'alerts': report['alerts']}
            )
        
    except Exception as e:
        logger.error(f"Monitoring failed: {e}")
        monitor.send_alert('ERROR', f"Database monitoring failed: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())