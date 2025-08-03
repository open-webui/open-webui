#!/usr/bin/env python3
"""
Performance monitoring script for organization model access.
Tracks query performance, generates reports, and identifies bottlenecks.
"""

import sqlite3
import time
import statistics
import json
import threading
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import concurrent.futures


class PerformanceMonitor:
    """Monitor and analyze organization model access performance"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.results = {}
        self.lock = threading.Lock()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get optimized database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn
    
    def benchmark_query(self, query: str, params: tuple = (), iterations: int = 100) -> Dict[str, float]:
        """Benchmark a single query"""
        conn = self.get_connection()
        times = []
        
        # Warm up
        for _ in range(5):
            conn.execute(query, params).fetchall()
        
        # Actual benchmark
        for _ in range(iterations):
            start = time.perf_counter()
            conn.execute(query, params).fetchall()
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms
        
        conn.close()
        
        return {
            "min": min(times),
            "max": max(times),
            "avg": statistics.mean(times),
            "median": statistics.median(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0,
            "p95": statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times),
            "p99": statistics.quantiles(times, n=100)[98] if len(times) >= 100 else max(times)
        }
    
    def test_concurrent_access(self, num_threads: int = 50, requests_per_thread: int = 100) -> Dict[str, Any]:
        """Test performance under concurrent load"""
        
        def worker(thread_id: int):
            """Worker thread for concurrent testing"""
            conn = self.get_connection()
            thread_times = []
            errors = 0
            
            queries = [
                ("user_orgs", """
                    SELECT DISTINCT organization_id 
                    FROM organization_members 
                    WHERE user_id = ? AND is_active = 1
                """, (f"user_{thread_id}",)),
                ("org_models", """
                    SELECT DISTINCT model_id 
                    FROM organization_models 
                    WHERE organization_id = ? AND is_active = 1
                """, (f"org_{thread_id % 10}",)),
                ("model_count", """
                    SELECT COUNT(*) 
                    FROM organization_models 
                    WHERE organization_id = ? AND is_active = 1
                """, (f"org_{thread_id % 10}",))
            ]
            
            for i in range(requests_per_thread):
                query_name, query, params = queries[i % len(queries)]
                
                try:
                    start = time.perf_counter()
                    conn.execute(query, params).fetchall()
                    elapsed = (time.perf_counter() - start) * 1000
                    thread_times.append(elapsed)
                except Exception as e:
                    errors += 1
            
            conn.close()
            
            with self.lock:
                self.results[thread_id] = {
                    "times": thread_times,
                    "errors": errors
                }
        
        # Clear previous results
        self.results = {}
        
        # Run concurrent test
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            concurrent.futures.wait(futures)
        
        total_time = time.time() - start_time
        
        # Aggregate results
        all_times = []
        total_errors = 0
        
        for thread_results in self.results.values():
            all_times.extend(thread_results["times"])
            total_errors += thread_results["errors"]
        
        if not all_times:
            return {"error": "No successful queries"}
        
        return {
            "total_requests": num_threads * requests_per_thread,
            "total_time_seconds": round(total_time, 2),
            "requests_per_second": round((num_threads * requests_per_thread) / total_time, 2),
            "total_errors": total_errors,
            "error_rate": round((total_errors / (num_threads * requests_per_thread)) * 100, 2),
            "response_times": {
                "min": round(min(all_times), 3),
                "max": round(max(all_times), 3),
                "avg": round(statistics.mean(all_times), 3),
                "median": round(statistics.median(all_times), 3),
                "p95": round(statistics.quantiles(all_times, n=20)[18], 3) if len(all_times) >= 20 else round(max(all_times), 3),
                "p99": round(statistics.quantiles(all_times, n=100)[98], 3) if len(all_times) >= 100 else round(max(all_times), 3)
            }
        }
    
    def analyze_index_usage(self) -> Dict[str, Any]:
        """Analyze index usage for organization queries"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        index_analysis = {}
        
        queries_to_analyze = [
            ("user_organizations", """
                SELECT DISTINCT organization_id 
                FROM organization_members 
                WHERE user_id = 'test_user' AND is_active = 1
            """),
            ("organization_models", """
                SELECT DISTINCT model_id 
                FROM organization_models 
                WHERE organization_id = 'test_org' AND is_active = 1
            """),
            ("user_model_view", """
                SELECT DISTINCT model_id 
                FROM user_available_models 
                WHERE user_id = 'test_user'
            """)
        ]
        
        for query_name, query in queries_to_analyze:
            try:
                # Get query plan
                plan = cursor.execute(f"EXPLAIN QUERY PLAN {query}").fetchall()
                
                # Check if index is being used
                plan_text = " ".join([str(row) for row in plan])
                uses_index = "USING INDEX" in plan_text or "USING COVERING INDEX" in plan_text
                
                index_analysis[query_name] = {
                    "uses_index": uses_index,
                    "query_plan": [str(row) for row in plan],
                    "optimized": uses_index
                }
            except Exception as e:
                index_analysis[query_name] = {
                    "error": str(e)
                }
        
        conn.close()
        return index_analysis
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        
        print("🔍 Starting Performance Analysis...")
        
        # 1. Individual query benchmarks
        print("\n📊 Benchmarking individual queries...")
        query_benchmarks = {}
        
        queries = {
            "get_user_organizations": (
                "SELECT DISTINCT organization_id FROM organization_members WHERE user_id = ? AND is_active = 1",
                ("test_user",)
            ),
            "get_organization_models": (
                "SELECT DISTINCT model_id FROM organization_models WHERE organization_id = ? AND is_active = 1",
                ("test_org",)
            ),
            "count_organization_members": (
                "SELECT COUNT(*) FROM organization_members WHERE organization_id = ? AND is_active = 1",
                ("test_org",)
            ),
            "count_user_accessible_models": (
                "SELECT COUNT(DISTINCT om.model_id) FROM organization_members mem "
                "JOIN organization_models om ON mem.organization_id = om.organization_id "
                "WHERE mem.user_id = ? AND mem.is_active = 1 AND om.is_active = 1",
                ("test_user",)
            )
        }
        
        for query_name, (query, params) in queries.items():
            print(f"  - Benchmarking {query_name}...")
            query_benchmarks[query_name] = self.benchmark_query(query, params)
        
        # 2. Concurrent access test
        print("\n🔄 Testing concurrent access...")
        concurrent_results = self.test_concurrent_access(num_threads=50, requests_per_thread=100)
        
        # 3. Index usage analysis
        print("\n🔎 Analyzing index usage...")
        index_analysis = self.analyze_index_usage()
        
        # 4. Database statistics
        print("\n📈 Collecting database statistics...")
        conn = self.get_connection()
        
        db_stats = {}
        try:
            # Table sizes
            for table in ["organization_members", "organization_models"]:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                db_stats[f"{table}_count"] = count
            
            # Database file size
            db_stats["database_size_mb"] = conn.execute("SELECT page_count * page_size / 1024.0 / 1024.0 FROM pragma_page_count(), pragma_page_size()").fetchone()[0]
            
            # WAL mode check
            db_stats["journal_mode"] = conn.execute("PRAGMA journal_mode").fetchone()[0]
            
        except Exception as e:
            db_stats["error"] = str(e)
        
        conn.close()
        
        # Generate report
        report = {
            "timestamp": datetime.now().isoformat(),
            "database_path": self.db_path,
            "query_benchmarks": query_benchmarks,
            "concurrent_access_test": concurrent_results,
            "index_usage": index_analysis,
            "database_statistics": db_stats,
            "performance_summary": self._generate_summary(query_benchmarks, concurrent_results)
        }
        
        return report
    
    def _generate_summary(self, query_benchmarks: Dict, concurrent_results: Dict) -> Dict[str, Any]:
        """Generate performance summary with recommendations"""
        
        summary = {
            "overall_health": "healthy",
            "issues": [],
            "recommendations": []
        }
        
        # Check query performance
        slow_queries = []
        for query_name, metrics in query_benchmarks.items():
            if metrics["p95"] > 5.0:  # 5ms threshold
                slow_queries.append(query_name)
                summary["issues"].append(f"{query_name} P95 latency is {metrics['p95']:.2f}ms (threshold: 5ms)")
        
        if slow_queries:
            summary["overall_health"] = "degraded"
            summary["recommendations"].append("Consider optimizing slow queries or adding indexes")
        
        # Check concurrent performance
        if concurrent_results.get("error_rate", 0) > 1.0:
            summary["overall_health"] = "unhealthy"
            summary["issues"].append(f"High error rate under load: {concurrent_results['error_rate']}%")
            summary["recommendations"].append("Investigate database locking issues")
        
        if concurrent_results.get("response_times", {}).get("p95", 0) > 10.0:
            summary["overall_health"] = "degraded" if summary["overall_health"] == "healthy" else summary["overall_health"]
            summary["issues"].append("High latency under concurrent load")
            summary["recommendations"].append("Consider connection pooling or caching")
        
        # Performance grade
        if summary["overall_health"] == "healthy":
            if all(metrics["p95"] < 1.0 for metrics in query_benchmarks.values()):
                summary["performance_grade"] = "A+"
                summary["message"] = "Excellent performance - all queries sub-millisecond"
            else:
                summary["performance_grade"] = "A"
                summary["message"] = "Good performance - all queries within acceptable range"
        elif summary["overall_health"] == "degraded":
            summary["performance_grade"] = "B"
            summary["message"] = "Acceptable performance with some optimization opportunities"
        else:
            summary["performance_grade"] = "C"
            summary["message"] = "Performance issues detected - optimization required"
        
        return summary
    
    def continuous_monitoring(self, interval_seconds: int = 60, duration_minutes: int = 60):
        """Run continuous performance monitoring"""
        
        print(f"📊 Starting continuous monitoring for {duration_minutes} minutes...")
        print(f"   Interval: {interval_seconds} seconds")
        
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        results = []
        
        while datetime.now() < end_time:
            # Quick performance check
            conn = self.get_connection()
            
            check_time = datetime.now()
            metrics = {
                "timestamp": check_time.isoformat(),
                "queries": {}
            }
            
            # Test key queries
            test_queries = [
                ("user_orgs", "SELECT COUNT(*) FROM organization_members WHERE is_active = 1"),
                ("org_models", "SELECT COUNT(*) FROM organization_models WHERE is_active = 1"),
                ("active_users", "SELECT COUNT(DISTINCT user_id) FROM organization_members")
            ]
            
            for query_name, query in test_queries:
                start = time.perf_counter()
                try:
                    result = conn.execute(query).fetchone()[0]
                    elapsed = (time.perf_counter() - start) * 1000
                    metrics["queries"][query_name] = {
                        "time_ms": round(elapsed, 3),
                        "result": result,
                        "status": "ok"
                    }
                except Exception as e:
                    metrics["queries"][query_name] = {
                        "status": "error",
                        "error": str(e)
                    }
            
            conn.close()
            results.append(metrics)
            
            # Print summary
            avg_time = statistics.mean([q.get("time_ms", 0) for q in metrics["queries"].values() if "time_ms" in q])
            print(f"\r[{check_time.strftime('%H:%M:%S')}] Avg query time: {avg_time:.2f}ms", end="", flush=True)
            
            # Wait for next interval
            time.sleep(interval_seconds)
        
        print("\n\n✅ Monitoring complete!")
        
        # Save results
        output_file = f"performance_monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"📄 Results saved to: {output_file}")
        
        return results


def main():
    """Main monitoring function"""
    parser = argparse.ArgumentParser(description="Monitor organization model access performance")
    parser.add_argument("--db", default="/app/backend/data/webui.db", help="Database path")
    parser.add_argument("--mode", choices=["report", "continuous", "benchmark"], default="report", 
                       help="Monitoring mode")
    parser.add_argument("--duration", type=int, default=60, help="Duration for continuous monitoring (minutes)")
    parser.add_argument("--interval", type=int, default=60, help="Interval for continuous monitoring (seconds)")
    parser.add_argument("--threads", type=int, default=50, help="Number of concurrent threads for benchmark")
    
    args = parser.parse_args()
    
    monitor = PerformanceMonitor(args.db)
    
    if args.mode == "report":
        # Generate comprehensive report
        report = monitor.generate_performance_report()
        
        # Print summary
        print("\n" + "="*60)
        print("📊 PERFORMANCE REPORT SUMMARY")
        print("="*60)
        
        summary = report["performance_summary"]
        print(f"\n🏆 Performance Grade: {summary['performance_grade']}")
        print(f"📋 Overall Health: {summary['overall_health'].upper()}")
        print(f"💬 {summary['message']}")
        
        if summary["issues"]:
            print("\n⚠️  Issues Found:")
            for issue in summary["issues"]:
                print(f"   - {issue}")
        
        if summary["recommendations"]:
            print("\n💡 Recommendations:")
            for rec in summary["recommendations"]:
                print(f"   - {rec}")
        
        # Query performance summary
        print("\n📈 Query Performance (P95 latency):")
        for query_name, metrics in report["query_benchmarks"].items():
            status = "✅" if metrics["p95"] < 5.0 else "⚠️"
            print(f"   {status} {query_name}: {metrics['p95']:.2f}ms")
        
        # Concurrent access summary
        concurrent = report["concurrent_access_test"]
        print(f"\n🔄 Concurrent Access Test:")
        print(f"   - Requests/second: {concurrent['requests_per_second']}")
        print(f"   - Error rate: {concurrent['error_rate']}%")
        print(f"   - P95 latency: {concurrent['response_times']['p95']}ms")
        
        # Save full report
        report_file = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Full report saved to: {report_file}")
        
    elif args.mode == "continuous":
        # Run continuous monitoring
        monitor.continuous_monitoring(
            interval_seconds=args.interval,
            duration_minutes=args.duration
        )
        
    elif args.mode == "benchmark":
        # Run stress test
        print(f"🏋️ Running benchmark with {args.threads} concurrent threads...")
        results = monitor.test_concurrent_access(
            num_threads=args.threads,
            requests_per_thread=1000
        )
        
        print("\n📊 Benchmark Results:")
        print(f"   Total requests: {results['total_requests']}")
        print(f"   Total time: {results['total_time_seconds']}s")
        print(f"   Requests/second: {results['requests_per_second']}")
        print(f"   Error rate: {results['error_rate']}%")
        print(f"\n   Response times:")
        for metric, value in results['response_times'].items():
            print(f"     {metric}: {value}ms")


if __name__ == "__main__":
    main()