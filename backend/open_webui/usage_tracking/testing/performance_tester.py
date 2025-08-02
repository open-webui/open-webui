"""
Performance Testing Script for SQLite vs InfluxDB
Measures and compares webhook processing performance
"""

import asyncio
import time
import statistics
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional
import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import sys

# Add parent directories to path
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent))

from webhook_data_generator import WebhookDataGenerator
from webhook_sender import WebhookSender


class PerformanceTester:
    """Performance testing for webhook processing"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        webhook_secret: str = "test-webhook-secret"
    ):
        self.base_url = base_url
        self.webhook_secret = webhook_secret
        self.generator = WebhookDataGenerator(webhook_secret)
        self.sender = WebhookSender(base_url, webhook_secret)
        self.results = {
            "sqlite_only": [],
            "influxdb_only": [],
            "dual_write": []
        }
    
    async def measure_single_request(
        self,
        payload: Dict[str, Any],
        mode: str
    ) -> Tuple[float, bool]:
        """
        Measure response time for a single request
        
        Args:
            payload: Webhook payload
            mode: Storage mode (sqlite_only, influxdb_only, dual_write)
            
        Returns:
            Tuple of (response_time_ms, success)
        """
        # Set headers to indicate storage mode for testing
        headers = {
            "X-Test-Storage-Mode": mode,
            "X-OpenRouter-Signature": self.sender.generate_signature(payload),
            "Content-Type": "application/json"
        }
        
        start_time = time.perf_counter()
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/webhooks/openrouter",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
            end_time = time.perf_counter()
            response_time_ms = (end_time - start_time) * 1000
            
            success = response.status_code == 200
            return response_time_ms, success
            
        except Exception as e:
            end_time = time.perf_counter()
            response_time_ms = (end_time - start_time) * 1000
            print(f"Request failed: {e}")
            return response_time_ms, False
    
    async def run_performance_test(
        self,
        test_size: int = 100,
        concurrent_requests: int = 10,
        modes: List[str] = None
    ) -> Dict[str, Any]:
        """
        Run comprehensive performance test
        
        Args:
            test_size: Number of requests per mode
            concurrent_requests: Max concurrent requests
            modes: Storage modes to test
            
        Returns:
            Test results with statistics
        """
        if modes is None:
            modes = ["sqlite_only", "influxdb_only", "dual_write"]
        
        print(f"\n🚀 Starting performance test")
        print(f"Test size: {test_size} requests per mode")
        print(f"Concurrent requests: {concurrent_requests}")
        print(f"Modes: {', '.join(modes)}")
        print("-" * 60)
        
        results = {}
        
        for mode in modes:
            print(f"\n📊 Testing {mode} mode...")
            
            # Generate test payloads
            payloads = self.generator.generate_batch(count=test_size)
            
            # Run tests with concurrency limit
            mode_results = []
            semaphore = asyncio.Semaphore(concurrent_requests)
            
            async def test_with_semaphore(payload):
                async with semaphore:
                    return await self.measure_single_request(payload, mode)
            
            # Start timing
            start_time = time.time()
            
            # Create all tasks
            tasks = [test_with_semaphore(payload) for payload in payloads]
            
            # Execute with progress tracking
            completed = 0
            for task in asyncio.as_completed(tasks):
                response_time, success = await task
                mode_results.append({
                    "response_time_ms": response_time,
                    "success": success
                })
                
                completed += 1
                if completed % 20 == 0:
                    print(f"  Progress: {completed}/{test_size}")
            
            total_time = time.time() - start_time
            
            # Calculate statistics
            response_times = [r["response_time_ms"] for r in mode_results if r["success"]]
            success_count = sum(1 for r in mode_results if r["success"])
            
            if response_times:
                stats = {
                    "mode": mode,
                    "total_requests": test_size,
                    "successful_requests": success_count,
                    "success_rate": (success_count / test_size) * 100,
                    "total_time_seconds": total_time,
                    "requests_per_second": test_size / total_time,
                    "response_times": {
                        "min": min(response_times),
                        "max": max(response_times),
                        "mean": statistics.mean(response_times),
                        "median": statistics.median(response_times),
                        "p95": np.percentile(response_times, 95),
                        "p99": np.percentile(response_times, 99),
                        "stdev": statistics.stdev(response_times) if len(response_times) > 1 else 0
                    }
                }
            else:
                stats = {
                    "mode": mode,
                    "total_requests": test_size,
                    "successful_requests": 0,
                    "success_rate": 0,
                    "error": "No successful requests"
                }
            
            results[mode] = stats
            self.results[mode] = response_times
            
            # Print summary
            print(f"\n  ✅ {mode} Results:")
            print(f"  Success rate: {stats['success_rate']:.1f}%")
            if response_times:
                print(f"  Response times (ms):")
                print(f"    - Mean: {stats['response_times']['mean']:.2f}")
                print(f"    - Median: {stats['response_times']['median']:.2f}")
                print(f"    - P95: {stats['response_times']['p95']:.2f}")
                print(f"    - P99: {stats['response_times']['p99']:.2f}")
                print(f"  Throughput: {stats['requests_per_second']:.1f} req/s")
        
        return results
    
    def generate_comparison_report(
        self,
        results: Dict[str, Any],
        output_file: str = "performance_report.json"
    ):
        """Generate detailed comparison report"""
        
        report = {
            "test_timestamp": datetime.now(timezone.utc).isoformat(),
            "test_configuration": {
                "base_url": self.base_url,
                "modes_tested": list(results.keys())
            },
            "results": results,
            "comparison": {}
        }
        
        # Calculate comparisons if we have multiple modes
        if len(results) > 1 and all("response_times" in r for r in results.values()):
            baseline = "sqlite_only" if "sqlite_only" in results else list(results.keys())[0]
            baseline_mean = results[baseline]["response_times"]["mean"]
            
            for mode, stats in results.items():
                if mode != baseline and "response_times" in stats:
                    mode_mean = stats["response_times"]["mean"]
                    improvement = ((baseline_mean - mode_mean) / baseline_mean) * 100
                    report["comparison"][f"{mode}_vs_{baseline}"] = {
                        "improvement_percent": improvement,
                        "speedup_factor": baseline_mean / mode_mean,
                        "absolute_difference_ms": baseline_mean - mode_mean
                    }
        
        # Save report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Report saved to {output_file}")
        
        return report
    
    def plot_results(
        self,
        results: Dict[str, Any],
        output_file: str = "performance_comparison.png"
    ):
        """Create visualization of performance results"""
        
        # Skip if matplotlib not available
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("⚠️  matplotlib not available, skipping plots")
            return
        
        modes = []
        means = []
        p95s = []
        p99s = []
        
        for mode, stats in results.items():
            if "response_times" in stats:
                modes.append(mode.replace("_", " ").title())
                means.append(stats["response_times"]["mean"])
                p95s.append(stats["response_times"]["p95"])
                p99s.append(stats["response_times"]["p99"])
        
        if not modes:
            print("⚠️  No data to plot")
            return
        
        # Create bar chart
        x = np.arange(len(modes))
        width = 0.25
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
        
        # Response time comparison
        rects1 = ax1.bar(x - width, means, width, label='Mean')
        rects2 = ax1.bar(x, p95s, width, label='P95')
        rects3 = ax1.bar(x + width, p99s, width, label='P99')
        
        ax1.set_ylabel('Response Time (ms)')
        ax1.set_xlabel('Storage Mode')
        ax1.set_title('Webhook Processing Response Times')
        ax1.set_xticks(x)
        ax1.set_xticklabels(modes)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Add value labels on bars
        def autolabel(ax, rects):
            for rect in rects:
                height = rect.get_height()
                ax.annotate(f'{height:.1f}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom')
        
        autolabel(ax1, rects1)
        autolabel(ax1, rects2)
        autolabel(ax1, rects3)
        
        # Box plot for distribution
        if self.results:
            data_to_plot = []
            labels_to_plot = []
            
            for mode in ["sqlite_only", "influxdb_only", "dual_write"]:
                if mode in self.results and self.results[mode]:
                    data_to_plot.append(self.results[mode])
                    labels_to_plot.append(mode.replace("_", " ").title())
            
            if data_to_plot:
                ax2.boxplot(data_to_plot, labels=labels_to_plot)
                ax2.set_ylabel('Response Time (ms)')
                ax2.set_xlabel('Storage Mode')
                ax2.set_title('Response Time Distribution')
                ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"\n📊 Plot saved to {output_file}")
    
    async def run_stress_test(
        self,
        duration_seconds: int = 60,
        requests_per_second: int = 10
    ) -> Dict[str, Any]:
        """
        Run stress test to find breaking point
        
        Args:
            duration_seconds: Test duration
            requests_per_second: Target request rate
            
        Returns:
            Stress test results
        """
        print(f"\n🔥 Starting stress test")
        print(f"Duration: {duration_seconds}s")
        print(f"Target rate: {requests_per_second} req/s")
        print("-" * 60)
        
        results = {
            "start_time": datetime.now(timezone.utc).isoformat(),
            "target_rps": requests_per_second,
            "duration_seconds": duration_seconds,
            "checkpoints": []
        }
        
        start_time = time.time()
        sent_count = 0
        success_count = 0
        response_times = []
        
        # Calculate interval between requests
        interval = 1.0 / requests_per_second
        
        import httpx
        async with httpx.AsyncClient() as client:
            while (time.time() - start_time) < duration_seconds:
                # Generate and send webhook
                payload = self.generator.generate_webhook_payload()
                
                # Measure response time
                request_start = time.perf_counter()
                try:
                    response = await client.post(
                        f"{self.base_url}/api/webhooks/openrouter",
                        json=payload,
                        headers={
                            "X-OpenRouter-Signature": self.sender.generate_signature(payload),
                            "Content-Type": "application/json"
                        },
                        timeout=5.0
                    )
                    
                    request_end = time.perf_counter()
                    response_time_ms = (request_end - request_start) * 1000
                    
                    sent_count += 1
                    if response.status_code == 200:
                        success_count += 1
                        response_times.append(response_time_ms)
                    
                except Exception as e:
                    sent_count += 1
                    print(f"Request failed: {e}")
                
                # Checkpoint every 10 seconds
                elapsed = time.time() - start_time
                if int(elapsed) % 10 == 0 and int(elapsed) not in [c["elapsed_seconds"] for c in results["checkpoints"]]:
                    checkpoint = {
                        "elapsed_seconds": int(elapsed),
                        "sent": sent_count,
                        "success": success_count,
                        "success_rate": (success_count / sent_count * 100) if sent_count > 0 else 0,
                        "actual_rps": sent_count / elapsed,
                        "avg_response_ms": statistics.mean(response_times[-100:]) if response_times else 0
                    }
                    results["checkpoints"].append(checkpoint)
                    print(f"  [{elapsed:.0f}s] Sent: {sent_count}, Success: {success_rate:.1f}%, RPS: {actual_rps:.1f}")
                
                # Rate limiting
                await asyncio.sleep(interval)
        
        # Final results
        total_duration = time.time() - start_time
        results["final_stats"] = {
            "total_sent": sent_count,
            "total_success": success_count,
            "success_rate": (success_count / sent_count * 100) if sent_count > 0 else 0,
            "actual_rps": sent_count / total_duration,
            "avg_response_ms": statistics.mean(response_times) if response_times else 0,
            "p95_response_ms": np.percentile(response_times, 95) if response_times else 0,
            "p99_response_ms": np.percentile(response_times, 99) if response_times else 0
        }
        
        print(f"\n✅ Stress test complete")
        print(f"Total requests: {sent_count}")
        print(f"Success rate: {results['final_stats']['success_rate']:.1f}%")
        print(f"Actual RPS: {results['final_stats']['actual_rps']:.1f}")
        
        return results


async def main():
    """Run performance tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Performance testing for mAI webhooks")
    parser.add_argument("--url", default="http://localhost:8080", help="mAI base URL")
    parser.add_argument("--test", choices=["compare", "stress", "both"], default="compare")
    parser.add_argument("--size", type=int, default=100, help="Test size for comparison")
    parser.add_argument("--concurrent", type=int, default=10, help="Concurrent requests")
    parser.add_argument("--duration", type=int, default=60, help="Stress test duration")
    parser.add_argument("--rps", type=int, default=10, help="Requests per second for stress test")
    
    args = parser.parse_args()
    
    tester = PerformanceTester(base_url=args.url)
    
    if args.test in ["compare", "both"]:
        # Run comparison test
        results = await tester.run_performance_test(
            test_size=args.size,
            concurrent_requests=args.concurrent
        )
        
        # Generate report and plots
        tester.generate_comparison_report(results)
        tester.plot_results(results)
    
    if args.test in ["stress", "both"]:
        # Run stress test
        stress_results = await tester.run_stress_test(
            duration_seconds=args.duration,
            requests_per_second=args.rps
        )
        
        # Save stress test results
        with open("stress_test_results.json", 'w') as f:
            json.dump(stress_results, f, indent=2)
        print("\n📄 Stress test results saved to stress_test_results.json")


if __name__ == "__main__":
    asyncio.run(main())