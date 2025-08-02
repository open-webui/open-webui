#!/usr/bin/env python3
"""
Test Runner for E2E Usage Processing Tests
Orchestrates the complete end-to-end testing of the usage processing cycle

Usage:
    python3 run_e2e_tests.py                    # Run all E2E tests
    python3 run_e2e_tests.py --fast             # Run fast tests only
    python3 run_e2e_tests.py --verbose          # Verbose output
    python3 run_e2e_tests.py --cleanup-only     # Just cleanup test data
"""

import asyncio
import subprocess
import sys
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class E2ETestRunner:
    """Orchestrates E2E test execution with proper setup and cleanup"""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.backend_dir = self.test_dir.parent
        self.project_root = self.backend_dir.parent
        
        # Test configuration
        self.test_files = [
            "test_usage_processing_e2e.py",
        ]
        
        self.fast_tests = [
            "test_usage_processing_e2e.py::TestUsageProcessingE2E::test_webhook_signature_validation",
            "test_usage_processing_e2e.py::TestUsageProcessingE2E::test_duplicate_webhook_handling",
        ]
        
    async def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met for running E2E tests"""
        logger.info("🔍 Checking prerequisites...")
        
        prerequisites = {
            "Python version": self._check_python_version(),
            "Required packages": self._check_packages(),
            "Backend directory": self._check_backend_structure(),
            "Database access": await self._check_database_access(),
            "Test files": self._check_test_files()
        }
        
        all_good = True
        for check, result in prerequisites.items():
            status = "✅" if result else "❌"
            logger.info(f"  {status} {check}")
            if not result:
                all_good = False
        
        if not all_good:
            logger.error("❌ Prerequisites not met. Please fix the issues above.")
            return False
        
        logger.info("✅ All prerequisites met")
        return True
    
    def _check_python_version(self) -> bool:
        """Check if Python version is 3.12+"""
        version = sys.version_info
        return version.major == 3 and version.minor >= 12
    
    def _check_packages(self) -> bool:
        """Check if required packages are available"""
        required_packages = [
            "pytest", "pytest-asyncio", "httpx", "freezegun"
        ]
        
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                logger.error(f"Missing package: {package}")
                return False
        
        return True
    
    def _check_backend_structure(self) -> bool:
        """Check if backend directory structure is correct"""
        required_paths = [
            self.backend_dir / "open_webui",
            self.backend_dir / "open_webui" / "usage_tracking",
            self.backend_dir / "open_webui" / "utils"
        ]
        
        for path in required_paths:
            if not path.exists():
                logger.error(f"Missing directory: {path}")
                return False
        
        return True
    
    async def _check_database_access(self) -> bool:
        """Check if database access is working"""
        try:
            # Add backend to path for imports
            sys.path.insert(0, str(self.backend_dir))
            
            from open_webui.utils.database import get_db
            
            # Try to get a database connection
            db = next(get_db())
            db.execute("SELECT 1")
            db.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Database access failed: {e}")
            return False
    
    def _check_test_files(self) -> bool:
        """Check if test files exist"""
        for test_file in self.test_files:
            test_path = self.test_dir / test_file
            if not test_path.exists():
                logger.error(f"Missing test file: {test_path}")
                return False
        
        return True
    
    async def setup_test_environment(self):
        """Set up the test environment"""
        logger.info("🔧 Setting up test environment...")
        
        # Set environment variables
        os.environ["ENVIRONMENT"] = "test"
        os.environ["PYTHONPATH"] = str(self.backend_dir)
        
        # Ensure test directories exist
        for subdir in ["mocks", "utils"]:
            (self.test_dir / subdir).mkdir(exist_ok=True)
        
        logger.info("✅ Test environment ready")
    
    async def cleanup_test_data(self):
        """Clean up test data from previous runs"""
        logger.info("🧹 Cleaning up test data...")
        
        try:
            # Remove test database files
            for db_file in self.test_dir.glob("test_*.db*"):
                db_file.unlink()
                logger.info(f"Removed {db_file}")
            
            # Clean up any temporary files
            for temp_file in self.test_dir.glob("temp_*"):
                if temp_file.is_file():
                    temp_file.unlink()
                elif temp_file.is_dir():
                    import shutil
                    shutil.rmtree(temp_file)
            
            logger.info("✅ Test data cleanup completed")
            
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")
    
    def run_pytest(self, test_args: list) -> int:
        """Run pytest with specified arguments"""
        cmd = [
            sys.executable, "-m", "pytest",
            "--tb=short",
            "--color=yes",
            "-v"
        ] + test_args
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        # Change to test directory
        original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        try:
            result = subprocess.run(cmd, capture_output=False)
            return result.returncode
        finally:
            os.chdir(original_cwd)
    
    async def run_all_tests(self, verbose: bool = False) -> bool:
        """Run all E2E tests"""
        logger.info("🚀 Running all E2E tests...")
        
        test_args = []
        if verbose:
            test_args.append("-vv")
        
        test_args.extend(self.test_files)
        
        return_code = self.run_pytest(test_args)
        
        if return_code == 0:
            logger.info("✅ All E2E tests passed!")
            return True
        else:
            logger.error(f"❌ E2E tests failed with return code {return_code}")
            return False
    
    async def run_fast_tests(self, verbose: bool = False) -> bool:
        """Run only fast E2E tests"""
        logger.info("⚡ Running fast E2E tests...")
        
        test_args = []
        if verbose:
            test_args.append("-vv")
        
        test_args.extend(self.fast_tests)
        
        return_code = self.run_pytest(test_args)
        
        if return_code == 0:
            logger.info("✅ Fast E2E tests passed!")
            return True
        else:
            logger.error(f"❌ Fast E2E tests failed with return code {return_code}")
            return False
    
    async def run_specific_test(self, test_name: str, verbose: bool = False) -> bool:
        """Run a specific test"""
        logger.info(f"🎯 Running specific test: {test_name}")
        
        test_args = []
        if verbose:
            test_args.append("-vv")
        
        test_args.append(test_name)
        
        return_code = self.run_pytest(test_args)
        
        if return_code == 0:
            logger.info(f"✅ Test {test_name} passed!")
            return True
        else:
            logger.error(f"❌ Test {test_name} failed with return code {return_code}")
            return False
    
    def generate_test_report(self, success: bool):
        """Generate a test report summary"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""
{'='*60}
E2E Test Report - {timestamp}
{'='*60}

Overall Result: {'✅ PASSED' if success else '❌ FAILED'}

Test Configuration:
- Environment: test
- Backend Directory: {self.backend_dir}
- Test Directory: {self.test_dir}

Test Files Executed:
{chr(10).join(f'  - {test_file}' for test_file in self.test_files)}

{'='*60}
"""
        
        print(report)
        
        # Save report to file
        report_file = self.test_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Test report saved to: {report_file}")


async def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description="E2E Usage Processing Test Runner")
    parser.add_argument("--fast", action="store_true", help="Run fast tests only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--cleanup-only", action="store_true", help="Just cleanup test data")
    parser.add_argument("--test", type=str, help="Run specific test")
    parser.add_argument("--no-prereq-check", action="store_true", help="Skip prerequisite checks")
    
    args = parser.parse_args()
    
    runner = E2ETestRunner()
    
    # Handle cleanup-only mode
    if args.cleanup_only:
        await runner.cleanup_test_data()
        return 0
    
    try:
        # Check prerequisites unless skipped
        if not args.no_prereq_check:
            if not await runner.check_prerequisites():
                return 1
        
        # Set up test environment
        await runner.setup_test_environment()
        
        # Clean up from previous runs
        await runner.cleanup_test_data()
        
        # Run tests based on arguments
        if args.test:
            success = await runner.run_specific_test(args.test, args.verbose)
        elif args.fast:
            success = await runner.run_fast_tests(args.verbose)
        else:
            success = await runner.run_all_tests(args.verbose)
        
        # Generate report
        runner.generate_test_report(success)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("❌ Tests interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"❌ Test runner failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Final cleanup
        try:
            await runner.cleanup_test_data()
        except Exception as e:
            logger.warning(f"Final cleanup failed: {e}")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)