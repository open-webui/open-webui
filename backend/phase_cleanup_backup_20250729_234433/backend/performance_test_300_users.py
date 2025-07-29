#!/usr/bin/env python3
"""
Performance test simulating 300+ concurrent users accessing models.
Tests the production readiness of the organization model access system.
"""

import sqlite3
import time
import threading
import random
import statistics
import json
import argparse
import os
from datetime import datetime
from typing import Dict, List, Any, Tuple
import concurrent.futures
from dataclasses import dataclass
import queue


@dataclass
class PerformanceMetrics:
    """Performance test metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_time: float = 0
    response_times: List[float] = None
    errors: List[Tuple[str, str]] = None
    
    def __post_init__(self):
        if self.response_times is None:
            self.response_times = []
        if self.errors is None:
            self.errors = []
    
    def add_response(self, response_time: float):
        """Add successful response time"""
        self.response_times.append(response_time)
        self.successful_requests += 1
        self.total_requests += 1
    
    def add_error(self, error_type: str, error_msg: str):
        """Add error"""
        self.errors.append((error_type, error_msg))
        self.failed_requests += 1
        self.total_requests += 1
    
    def calculate_statistics(self) -> Dict[str, Any]:
        """Calculate performance statistics"""
        if not self.response_times:
            return {"error": "No successful requests"}
        
        sorted_times = sorted(self.response_times)
        
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": round((self.successful_requests / self.total_requests) * 100, 2),
            "total_time_seconds": round(self.total_time, 2),
            "requests_per_second": round(self.total_requests / self.total_time, 2),
            "response_times_ms": {
                "min": round(min(sorted_times), 3),
                "max": round(max(sorted_times), 3),
                "mean": round(statistics.mean(sorted_times), 3),
                "median": round(statistics.median(sorted_times), 3),
                "p50": round(sorted_times[int(len(sorted_times) * 0.50)], 3),
                "p90": round(sorted_times[int(len(sorted_times) * 0.90)], 3),
                "p95": round(sorted_times[int(len(sorted_times) * 0.95)], 3),
                "p99": round(sorted_times[int(len(sorted_times) * 0.99)], 3),
                "stdev": round(statistics.stdev(sorted_times), 3) if len(sorted_times) > 1 else 0
            },
            "error_summary": self._summarize_errors()
        }
    
    def _summarize_errors(self) -> Dict[str, int]:
        """Summarize errors by type"""
        error_counts = {}
        for error_type, _ in self.errors:
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        return error_counts


class LoadGenerator:
    """Generate realistic load for performance testing"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.metrics = PerformanceMetrics()
        self.result_queue = queue.Queue()
        self.user_sessions = {}
        
    def setup_test_data(self, num_users: int = 300, num_orgs: int = 20, num_models: int = 50):
        """Set up realistic test data"""
        print(f"📊 Setting up test data: {num_users} users, {num_orgs} organizations, {num_models} models...")
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        cursor = conn.cursor()
        
        try:
            # Clear existing data
            for table in ["organization_members", "organization_models", "model", "user"]:
                cursor.execute(f"DELETE FROM {table}")
            
            # Create users
            print("  Creating users...")
            users = []
            for i in range(num_users):
                user_id = f"user_{i:04d}"
                email = f"user{i}@company{i % num_orgs}.com"
                users.append((user_id, email, f"User {i}", "user", int(time.time())))
            
            cursor.executemany("""
                INSERT INTO user (id, email, name, role, last_active_at)
                VALUES (?, ?, ?, ?, ?)
            """, users)
            
            # Create models
            print("  Creating models...")
            models = []
            model_names = ["GPT-4", "Claude-3", "Gemini-Pro", "Llama-70B", "Mistral-Large"]
            for i in range(num_models):
                model_id = f"model_{i:03d}"
                model_name = f"{model_names[i % len(model_names)]}-{i}"
                models.append((model_id, "system", None, model_name, "{}", "{}", None, 1, 
                             int(time.time()), int(time.time())))
            
            cursor.executemany("""
                INSERT INTO model (id, user_id, base_model_id, name, params, meta, 
                                 access_control, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, models)
            
            # Create organizations and assign users
            print("  Creating organization memberships...")
            memberships = []
            org_user_map = {}
            
            for org_idx in range(num_orgs):
                org_id = f"org_{org_idx:03d}"
                org_user_map[org_id] = []
                
                # Each organization gets users from specific ranges
                start_user = (org_idx * num_users) // num_orgs
                end_user = ((org_idx + 1) * num_users) // num_orgs
                
                for user_idx in range(start_user, end_user):
                    user_id = f"user_{user_idx:04d}"
                    member_id = f"om_{user_id}_{org_id}"
                    role = "admin" if user_idx % 20 == 0 else "member"
                    memberships.append((member_id, org_id, user_id, role, 1, int(time.time())))
                    org_user_map[org_id].append(user_id)
                
                # Add some users to multiple organizations (10% overlap)
                if org_idx > 0 and random.random() < 0.1:
                    overlap_count = random.randint(1, 5)
                    for _ in range(overlap_count):
                        user_idx = random.randint(0, num_users - 1)
                        user_id = f"user_{user_idx:04d}"
                        member_id = f"om_{user_id}_{org_id}_overlap"
                        if member_id not in [m[0] for m in memberships]:
                            memberships.append((member_id, org_id, user_id, "member", 1, int(time.time())))
            
            cursor.executemany("""
                INSERT INTO organization_members (id, organization_id, user_id, role, is_active, joined_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, memberships)
            
            # Assign models to organizations
            print("  Assigning models to organizations...")
            assignments = []
            
            for org_idx in range(num_orgs):
                org_id = f"org_{org_idx:03d}"
                
                # Each organization gets 10-30 models
                model_count = random.randint(10, 30)
                selected_models = random.sample(range(num_models), model_count)
                
                for model_idx in selected_models:
                    model_id = f"model_{model_idx:03d}"
                    org_model_id = f"orgmod_{org_id}_{model_id}"
                    is_active = 1 if random.random() > 0.05 else 0  # 5% inactive
                    assignments.append((org_model_id, org_id, model_id, is_active, 
                                      int(time.time()), int(time.time())))
            
            cursor.executemany("""
                INSERT INTO organization_models (id, organization_id, model_id, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, assignments)
            
            conn.commit()
            
            # Verify setup
            user_count = cursor.execute("SELECT COUNT(*) FROM user").fetchone()[0]
            member_count = cursor.execute("SELECT COUNT(*) FROM organization_members").fetchone()[0]
            model_count = cursor.execute("SELECT COUNT(*) FROM model").fetchone()[0]
            assignment_count = cursor.execute("SELECT COUNT(*) FROM organization_models").fetchone()[0]
            
            print(f"✅ Test data created:")
            print(f"   Users: {user_count}")
            print(f"   Organization memberships: {member_count}")
            print(f"   Models: {model_count}")
            print(f"   Model assignments: {assignment_count}")
            
            # Store user list for testing
            self.test_users = [f"user_{i:04d}" for i in range(num_users)]
            
        except Exception as e:
            print(f"❌ Error setting up test data: {e}")
            raise
        finally:
            conn.close()
    
    def simulate_user_session(self, user_id: str, session_id: int, duration_seconds: int = 60):
        """Simulate a single user session with realistic behavior"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        
        session_start = time.time()
        session_metrics = {
            "user_id": user_id,
            "session_id": session_id,
            "requests": 0,
            "errors": 0,
            "response_times": []
        }
        
        try:
            while time.time() - session_start < duration_seconds:
                # Simulate different types of requests
                request_type = random.choice([
                    "get_models",      # 60% - Most common
                    "get_models",
                    "get_models",
                    "check_access",    # 20% - Permission checks
                    "count_models",    # 20% - Dashboard queries
                ])
                
                start_time = time.perf_counter()
                
                try:
                    if request_type == "get_models":
                        # Simulate get_models_by_user_id query pattern
                        cursor = conn.cursor()
                        
                        # Get user organizations
                        user_orgs = cursor.execute("""
                            SELECT DISTINCT organization_id 
                            FROM organization_members 
                            WHERE user_id = ? AND is_active = 1
                        """, (user_id,)).fetchall()
                        
                        if user_orgs:
                            org_ids = [org[0] for org in user_orgs]
                            
                            # Get models for organizations
                            placeholders = ','.join(['?' for _ in org_ids])
                            models = cursor.execute(f"""
                                SELECT DISTINCT m.id, m.name 
                                FROM organization_models om
                                JOIN model m ON om.model_id = m.id
                                WHERE om.organization_id IN ({placeholders}) 
                                AND om.is_active = 1
                            """, org_ids).fetchall()
                    
                    elif request_type == "check_access":
                        # Check specific model access
                        cursor = conn.cursor()
                        model_id = f"model_{random.randint(0, 49):03d}"
                        
                        access = cursor.execute("""
                            SELECT COUNT(*) 
                            FROM organization_members om
                            JOIN organization_models orgm ON om.organization_id = orgm.organization_id
                            WHERE om.user_id = ? 
                            AND orgm.model_id = ?
                            AND om.is_active = 1 
                            AND orgm.is_active = 1
                        """, (user_id, model_id)).fetchone()[0]
                    
                    elif request_type == "count_models":
                        # Count accessible models
                        cursor = conn.cursor()
                        count = cursor.execute("""
                            SELECT COUNT(DISTINCT orgm.model_id)
                            FROM organization_members om
                            JOIN organization_models orgm ON om.organization_id = orgm.organization_id
                            WHERE om.user_id = ? 
                            AND om.is_active = 1 
                            AND orgm.is_active = 1
                        """, (user_id,)).fetchone()[0]
                    
                    # Calculate response time
                    response_time = (time.perf_counter() - start_time) * 1000
                    session_metrics["requests"] += 1
                    session_metrics["response_times"].append(response_time)
                    
                    # Report to main metrics
                    self.result_queue.put(("success", response_time))
                    
                except Exception as e:
                    session_metrics["errors"] += 1
                    self.result_queue.put(("error", (type(e).__name__, str(e))))
                
                # Simulate think time between requests
                think_time = random.uniform(0.5, 2.0)
                time.sleep(think_time)
        
        except Exception as e:
            self.result_queue.put(("error", ("SessionError", str(e))))
        finally:
            conn.close()
            
        # Store session metrics
        self.user_sessions[session_id] = session_metrics
    
    def run_load_test(self, num_concurrent_users: int = 300, test_duration: int = 60):
        """Run the load test with specified number of concurrent users"""
        print(f"\n🚀 Starting load test with {num_concurrent_users} concurrent users for {test_duration} seconds...")
        
        # Start metrics collector thread
        collector_thread = threading.Thread(target=self._collect_metrics)
        collector_thread.daemon = True
        collector_thread.start()
        
        # Start time
        start_time = time.time()
        
        # Launch user sessions
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent_users) as executor:
            futures = []
            
            for i in range(num_concurrent_users):
                user_id = random.choice(self.test_users)
                future = executor.submit(self.simulate_user_session, user_id, i, test_duration)
                futures.append(future)
                
                # Stagger start times slightly
                time.sleep(0.01)
            
            # Wait for all sessions to complete
            print(f"⏳ Running test... (0/{test_duration}s)", end="", flush=True)
            
            for i in range(test_duration):
                time.sleep(1)
                print(f"\r⏳ Running test... ({i+1}/{test_duration}s)", end="", flush=True)
            
            print("\n📊 Waiting for sessions to complete...")
            concurrent.futures.wait(futures)
        
        # Calculate total time
        self.metrics.total_time = time.time() - start_time
        
        # Signal collector to stop
        self.result_queue.put(("stop", None))
        collector_thread.join()
        
        print("✅ Load test completed!")
    
    def _collect_metrics(self):
        """Collect metrics from result queue"""
        while True:
            try:
                result_type, data = self.result_queue.get(timeout=1)
                
                if result_type == "stop":
                    break
                elif result_type == "success":
                    self.metrics.add_response(data)
                elif result_type == "error":
                    error_type, error_msg = data
                    self.metrics.add_error(error_type, error_msg)
            except queue.Empty:
                continue
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        stats = self.metrics.calculate_statistics()
        
        # Add session analysis
        session_stats = self._analyze_sessions()
        
        report = {
            "test_configuration": {
                "concurrent_users": len(self.user_sessions),
                "test_duration_seconds": int(self.metrics.total_time),
                "total_unique_users": len(set(s["user_id"] for s in self.user_sessions.values()))
            },
            "performance_metrics": stats,
            "session_analysis": session_stats,
            "timestamp": datetime.now().isoformat()
        }
        
        # Performance grading
        report["performance_grade"] = self._calculate_performance_grade(stats)
        
        return report
    
    def _analyze_sessions(self) -> Dict[str, Any]:
        """Analyze individual session performance"""
        if not self.user_sessions:
            return {}
        
        session_requests = [s["requests"] for s in self.user_sessions.values()]
        session_errors = [s["errors"] for s in self.user_sessions.values()]
        
        return {
            "total_sessions": len(self.user_sessions),
            "requests_per_session": {
                "min": min(session_requests) if session_requests else 0,
                "max": max(session_requests) if session_requests else 0,
                "avg": round(statistics.mean(session_requests), 2) if session_requests else 0
            },
            "errors_per_session": {
                "min": min(session_errors) if session_errors else 0,
                "max": max(session_errors) if session_errors else 0,
                "avg": round(statistics.mean(session_errors), 2) if session_errors else 0
            }
        }
    
    def _calculate_performance_grade(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance grade based on metrics"""
        grade_info = {
            "grade": "A+",
            "summary": "Excellent performance",
            "details": []
        }
        
        # Check response times
        p95 = stats["response_times_ms"]["p95"]
        if p95 < 10:
            grade_info["details"].append("✅ P95 latency < 10ms (excellent)")
        elif p95 < 50:
            grade_info["grade"] = "A"
            grade_info["details"].append("✅ P95 latency < 50ms (good)")
        elif p95 < 100:
            grade_info["grade"] = "B"
            grade_info["summary"] = "Good performance with room for improvement"
            grade_info["details"].append("⚠️  P95 latency < 100ms (acceptable)")
        else:
            grade_info["grade"] = "C"
            grade_info["summary"] = "Performance needs optimization"
            grade_info["details"].append("❌ P95 latency > 100ms (needs improvement)")
        
        # Check success rate
        success_rate = stats.get("success_rate", 0)
        if success_rate >= 99.9:
            grade_info["details"].append("✅ Success rate >= 99.9% (excellent)")
        elif success_rate >= 99:
            if grade_info["grade"] == "A+":
                grade_info["grade"] = "A"
            grade_info["details"].append("✅ Success rate >= 99% (good)")
        elif success_rate >= 95:
            if grade_info["grade"] in ["A+", "A"]:
                grade_info["grade"] = "B"
            grade_info["details"].append("⚠️  Success rate >= 95% (acceptable)")
        else:
            grade_info["grade"] = "D"
            grade_info["summary"] = "Significant reliability issues"
            grade_info["details"].append("❌ Success rate < 95% (poor)")
        
        # Check throughput
        rps = stats.get("requests_per_second", 0)
        if rps >= 1000:
            grade_info["details"].append("✅ Throughput >= 1000 req/s (excellent)")
        elif rps >= 500:
            grade_info["details"].append("✅ Throughput >= 500 req/s (good)")
        elif rps >= 100:
            grade_info["details"].append("⚠️  Throughput >= 100 req/s (acceptable)")
        else:
            if grade_info["grade"] in ["A+", "A"]:
                grade_info["grade"] = "B"
            grade_info["details"].append("❌ Throughput < 100 req/s (needs improvement)")
        
        return grade_info


def print_report(report: Dict[str, Any]):
    """Print formatted performance report"""
    print("\n" + "="*80)
    print("📊 PERFORMANCE TEST REPORT")
    print("="*80)
    
    # Test configuration
    config = report["test_configuration"]
    print(f"\n🔧 Test Configuration:")
    print(f"   Concurrent Users: {config['concurrent_users']}")
    print(f"   Test Duration: {config['test_duration_seconds']}s")
    print(f"   Unique Users: {config['total_unique_users']}")
    
    # Performance metrics
    metrics = report["performance_metrics"]
    print(f"\n📈 Performance Metrics:")
    print(f"   Total Requests: {metrics['total_requests']:,}")
    print(f"   Successful: {metrics['successful_requests']:,}")
    print(f"   Failed: {metrics['failed_requests']:,}")
    print(f"   Success Rate: {metrics['success_rate']}%")
    print(f"   Throughput: {metrics['requests_per_second']:,.1f} req/s")
    
    # Response times
    rt = metrics["response_times_ms"]
    print(f"\n⏱️  Response Times (ms):")
    print(f"   Min: {rt['min']}")
    print(f"   P50: {rt['p50']}")
    print(f"   P90: {rt['p90']}")
    print(f"   P95: {rt['p95']}")
    print(f"   P99: {rt['p99']}")
    print(f"   Max: {rt['max']}")
    
    # Errors
    if metrics.get("error_summary"):
        print(f"\n❌ Errors:")
        for error_type, count in metrics["error_summary"].items():
            print(f"   {error_type}: {count}")
    
    # Performance grade
    grade = report["performance_grade"]
    print(f"\n🏆 Performance Grade: {grade['grade']}")
    print(f"   {grade['summary']}")
    for detail in grade["details"]:
        print(f"   {detail}")
    
    print("\n" + "="*80)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Performance test for organization model access")
    parser.add_argument("--db", default="/app/backend/data/webui.db", help="Database path")
    parser.add_argument("--users", type=int, default=300, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--setup-only", action="store_true", help="Only set up test data")
    parser.add_argument("--output", help="Output file for JSON report")
    
    args = parser.parse_args()
    
    # Initialize load generator
    generator = LoadGenerator(args.db)
    
    # Set up test data
    generator.setup_test_data(num_users=max(args.users, 300))
    
    if args.setup_only:
        print("✅ Test data setup complete")
        return 0
    
    # Run load test
    generator.run_load_test(
        num_concurrent_users=args.users,
        test_duration=args.duration
    )
    
    # Generate report
    report = generator.generate_report()
    
    # Print report
    print_report(report)
    
    # Save JSON report if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Full report saved to: {args.output}")
    
    # Return exit code based on grade
    grade = report["performance_grade"]["grade"]
    if grade in ["A+", "A", "B"]:
        return 0
    else:
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())