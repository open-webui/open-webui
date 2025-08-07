#!/usr/bin/env python3
"""
Fast Local K8s CronJob Simulator for CANChat Vector Cleanup
===========================================================

Simulates Kubernetes CronJob behavior locally with accelerated timing.
Calls the main k8s_vector_cleanup.py script at configurable intervals.

This allows rapid testing of cronjob behavior without waiting for real schedules.

Features:
- Configurable interval (seconds instead of minutes/hours)
- Calls the actual K8s cleanup script
- Real-time logging with job numbers
- Easy start/stop with Ctrl+C
- Dry-run support for safe testing

Usage:
  python fast_cronjob_simulator.py [--interval N] [--dry-run] [--max-runs N]

Examples:
  python fast_cronjob_simulator.py                    # Run every 10 seconds
  python fast_cronjob_simulator.py --interval 5       # Run every 5 seconds
  python fast_cronjob_simulator.py --dry-run          # Safe testing mode
  python fast_cronjob_simulator.py --max-runs 3       # Stop after 3 runs
"""

import argparse
import logging
import os
import subprocess
import sys
import time
import signal
from datetime import datetime
from pathlib import Path

# Configuration defaults
DEFAULT_INTERVAL_SECONDS = 10  # Default interval between jobs
DEFAULT_MAX_RUNS = 1  # change to None for unlimited runs
DEFAULT_DRY_RUN = True  # change to False for real runs
CLEANUP_SCRIPT = "k8s_vector_cleanup.py"


class CronJobSimulator:
    def __init__(
        self, interval_seconds: int, dry_run: bool = False, max_runs: int = None
    ):
        self.interval_seconds = interval_seconds
        self.dry_run = dry_run
        self.max_runs = max_runs
        self.current_run = 0
        self.running = True

        # Script configuration
        self.script_path = Path(__file__).parent / CLEANUP_SCRIPT

        # Environment configuration (use existing environment + required defaults)
        self.env_vars = os.environ.copy()

        # Set required environment variables for local testing
        backend_dir = Path(__file__).parent.parent

        if "DATABASE_URL" not in self.env_vars:
            self.env_vars["DATABASE_URL"] = f"sqlite:///{backend_dir}/data/webui.db"

        if "QDRANT_URI" not in self.env_vars:
            self.env_vars["QDRANT_URI"] = "http://localhost:6333"

        if "VECTOR_DB_WEB_SEARCH_EXPIRY_DAYS" not in self.env_vars:
            self.env_vars["VECTOR_DB_WEB_SEARCH_EXPIRY_DAYS"] = (
                "0"  # Clean ALL web searches immediately as opposed to the default 30 days
            )

        # Add backend directory to Python path so open_webui can be imported
        current_pythonpath = self.env_vars.get("PYTHONPATH", "")
        if current_pythonpath:
            self.env_vars["PYTHONPATH"] = f"{backend_dir}:{current_pythonpath}"
        else:
            self.env_vars["PYTHONPATH"] = str(backend_dir)

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - CRONJOB_SIM - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )
        self.logger = logging.getLogger(__name__)

        # Setup signal handling for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info("🛑 Shutdown signal received - stopping cronjob simulator...")
        self.running = False

    def _validate_script_exists(self):
        """Ensure the cleanup script exists."""
        if not self.script_path.exists():
            raise FileNotFoundError(f"Cleanup script not found: {self.script_path}")
        self.logger.info(f"✅ Found cleanup script: {self.script_path}")

    def _run_cleanup_job(self) -> bool:
        """
        Execute one cleanup job.

        Returns:
            bool: True if job succeeded, False otherwise
        """
        self.current_run += 1
        job_start_time = datetime.now()

        self.logger.info(
            f"🚀 Starting CronJob #{self.current_run} - {job_start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        try:
            # Build command
            cmd = ["python", str(self.script_path)]
            if self.dry_run:
                cmd.append("--dry-run")

            # Execute cleanup script
            self.logger.info(f"   Command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=self.script_path.parent,
                env=self.env_vars,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            # Log results
            if result.returncode == 0:
                self.logger.info("✅ Cleanup job completed successfully")
                if result.stdout.strip():
                    self.logger.info("📄 Script output:")
                    for line in result.stdout.strip().split("\n"):
                        self.logger.info(f"   {line}")
                return True
            else:
                self.logger.error(
                    f"❌ Cleanup job failed with exit code {result.returncode}"
                )
                if result.stderr.strip():
                    self.logger.error("📄 Error output:")
                    for line in result.stderr.strip().split("\n"):
                        self.logger.error(f"   {line}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("⏰ Cleanup job timed out after 5 minutes")
            return False
        except Exception as e:
            self.logger.error(f"💥 Cleanup job failed: {e}")
            return False
        finally:
            job_duration = (datetime.now() - job_start_time).total_seconds()
            self.logger.info(
                f"⏱️  Job #{self.current_run} completed in {job_duration:.2f}s"
            )

    def run(self):
        """Run the cronjob simulator."""
        try:
            self.logger.info("🔄 Starting Fast K8s CronJob Simulator")
            self.logger.info(f"   Script: {self.script_path.name}")
            self.logger.info(f"   Interval: {self.interval_seconds} seconds")
            self.logger.info(f"   Max runs: {self.max_runs or 'unlimited'}")
            self.logger.info(f"   Dry run: {self.dry_run}")
            self.logger.info("   Press Ctrl+C to stop")
            self.logger.info("=" * 60)

            # Validate script exists
            self._validate_script_exists()

            # Main simulation loop
            while self.running:
                if self.max_runs and self.current_run >= self.max_runs:
                    self.logger.info(f"🏁 Reached maximum runs ({self.max_runs})")
                    break

                # Run cleanup job
                success = self._run_cleanup_job()

                if not self.running:
                    break

                if self.current_run < (self.max_runs or float("inf")):
                    self.logger.info(
                        f"⏳ Waiting {self.interval_seconds} seconds until next run..."
                    )
                    self.logger.info("=" * 60)

                    # Sleep with interrupt checking
                    for _ in range(self.interval_seconds):
                        if not self.running:
                            break
                        time.sleep(1)

            self.logger.info("🎉 CronJob simulator finished")
            self.logger.info(f"   Total runs completed: {self.current_run}")

        except KeyboardInterrupt:
            self.logger.info("🛑 Interrupted by user")
        except Exception as e:
            self.logger.error(f"💥 Simulator error: {e}")
            sys.exit(1)


def main():
    """Main entry point for the cronjob simulator."""
    parser = argparse.ArgumentParser(
        description="Fast Local K8s CronJob Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fast_cronjob_simulator.py                    # Run every 10 seconds
  python fast_cronjob_simulator.py --interval 5       # Run every 5 seconds  
  python fast_cronjob_simulator.py --dry-run          # Safe testing mode
  python fast_cronjob_simulator.py --max-runs 3       # Stop after 3 runs
        """,
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help=f"Interval between jobs in seconds (default: {DEFAULT_INTERVAL_SECONDS})",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=DEFAULT_DRY_RUN,
        help=f"Pass --dry-run to the cleanup script for safe testing (default: {DEFAULT_DRY_RUN})",
    )

    parser.add_argument(
        "--max-runs",
        type=int,
        default=DEFAULT_MAX_RUNS,
        help=f"Maximum number of runs before stopping (default: {'unlimited' if DEFAULT_MAX_RUNS is None else DEFAULT_MAX_RUNS})",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.interval < 1:
        print("Error: Interval must be at least 1 second")
        sys.exit(1)

    if args.max_runs is not None and args.max_runs < 1:
        print("Error: Max runs must be at least 1")
        sys.exit(1)

    # Create and run simulator
    simulator = CronJobSimulator(
        interval_seconds=args.interval, dry_run=args.dry_run, max_runs=args.max_runs
    )

    simulator.run()


if __name__ == "__main__":
    main()
