"""
Basic validation tests to ensure E2E test infrastructure is working
Run these tests first to validate the test environment setup
"""

import pytest
import sys
import os
from pathlib import Path


class TestValidation:
    """Basic validation tests for E2E test infrastructure"""
    
    def test_python_version(self):
        """Test that Python version is 3.12+"""
        version = sys.version_info
        assert version.major == 3, f"Python 3 required, got {version.major}"
        assert version.minor >= 12, f"Python 3.12+ required, got {version.major}.{version.minor}"
    
    def test_backend_imports(self):
        """Test that backend modules can be imported"""
        # Add backend to path
        test_dir = Path(__file__).parent
        backend_dir = test_dir.parent
        sys.path.insert(0, str(backend_dir))
        
        # Test basic imports
        try:
            import open_webui
            assert True, "open_webui module imported successfully"
        except ImportError as e:
            pytest.fail(f"Failed to import open_webui: {e}")
        
        try:
            from open_webui.usage_tracking.services.webhook_service import WebhookService
            assert True, "WebhookService imported successfully"
        except ImportError as e:
            pytest.fail(f"Failed to import WebhookService: {e}")
    
    def test_test_utilities_import(self):
        """Test that test utilities can be imported"""
        test_dir = Path(__file__).parent
        utils_dir = test_dir / "utils"
        mocks_dir = test_dir / "mocks"
        
        sys.path.insert(0, str(utils_dir))
        sys.path.insert(0, str(mocks_dir))
        
        try:
            from test_helpers import WebhookTestGenerator, DatabaseVerifier
            assert True, "Test helpers imported successfully"
        except ImportError as e:
            pytest.fail(f"Failed to import test helpers: {e}")
        
        try:
            from nbp_mock import NBPMockService
            assert True, "NBP mock imported successfully"
        except ImportError as e:
            pytest.fail(f"Failed to import NBP mock: {e}")
    
    def test_required_packages(self):
        """Test that required packages are available"""
        required_packages = [
            "pytest",
            "asyncio", 
            "httpx",
            "datetime",
            "decimal",
            "logging"
        ]
        
        for package in required_packages:
            try:
                __import__(package)
                assert True, f"Package {package} available"
            except ImportError:
                pytest.fail(f"Required package missing: {package}")
    
    def test_database_connection(self):
        """Test that database connection works"""
        # Add backend to path
        test_dir = Path(__file__).parent
        backend_dir = test_dir.parent
        sys.path.insert(0, str(backend_dir))
        
        try:
            from open_webui.utils.database import get_db
            
            # Try to get a database connection
            db = next(get_db())
            result = db.execute("SELECT 1").fetchone()
            db.close()
            
            assert result[0] == 1, "Database query successful"
            assert True, "Database connection working"
            
        except Exception as e:
            pytest.fail(f"Database connection failed: {e}")
    
    @pytest.mark.asyncio
    async def test_webhook_generator(self):
        """Test webhook payload generation"""
        test_dir = Path(__file__).parent
        utils_dir = test_dir / "utils"
        sys.path.insert(0, str(utils_dir))
        
        from test_helpers import WebhookTestGenerator
        
        generator = WebhookTestGenerator()
        
        # Test single payload generation
        payload = generator.generate_usage_payload(
            tokens=1000,
            cost=0.01
        )
        
        assert payload["tokens_used"] == 1000
        assert payload["cost"] == 0.01
        assert "api_key" in payload
        assert "model" in payload
        assert "timestamp" in payload
        
        # Test batch generation
        payloads = generator.generate_batch_for_total(
            total_tokens=5000,
            total_cost=0.05,
            num_requests=3
        )
        
        assert len(payloads) == 3
        total_tokens = sum(p["tokens_used"] for p in payloads)
        total_cost = sum(p["cost"] for p in payloads)
        
        assert total_tokens == 5000
        assert abs(total_cost - 0.05) < 0.001
    
    @pytest.mark.asyncio 
    async def test_nbp_mock_service(self):
        """Test NBP mock service functionality"""
        test_dir = Path(__file__).parent
        mocks_dir = test_dir / "mocks"
        sys.path.insert(0, str(mocks_dir))
        
        from nbp_mock import NBPMockService
        from datetime import date
        from decimal import Decimal
        
        mock_service = NBPMockService()
        
        # Test mock configuration
        mock_service.enable_mock()
        mock_service.set_mock_rate("2025-08-01", Decimal("4.50"))
        
        # Test rate retrieval
        rate_data = await mock_service.get_usd_pln_rate(date(2025, 8, 1))
        
        assert rate_data["rate"] == 4.50
        assert rate_data["effective_date"] == "2025-08-01"
        assert rate_data["rate_source"] == "mock"
        
        mock_service.disable_mock()
    
    def test_file_structure(self):
        """Test that all required files exist"""
        test_dir = Path(__file__).parent
        
        required_files = [
            "test_usage_processing_e2e.py",
            "utils/test_helpers.py", 
            "mocks/nbp_mock.py",
            "conftest.py",
            "pytest.ini",
            "run_e2e_tests.py",
            "README.md"
        ]
        
        for file_path in required_files:
            full_path = test_dir / file_path
            assert full_path.exists(), f"Required file missing: {file_path}"
    
    def test_environment_setup(self):
        """Test environment variable setup"""
        # These should be set by conftest.py
        expected_env_vars = [
            ("ENVIRONMENT", "test"),
        ]
        
        for var_name, expected_value in expected_env_vars:
            actual_value = os.environ.get(var_name)
            if actual_value:
                assert actual_value == expected_value, f"{var_name} should be {expected_value}, got {actual_value}"


if __name__ == "__main__":
    # Run validation tests directly
    import asyncio
    
    async def run_validation():
        print("🧪 Running E2E test infrastructure validation...")
        
        validator = TestValidation()
        
        tests = [
            ("Python version", validator.test_python_version),
            ("Backend imports", validator.test_backend_imports),
            ("Test utilities import", validator.test_test_utilities_import),
            ("Required packages", validator.test_required_packages),
            ("Database connection", validator.test_database_connection),
            ("File structure", validator.test_file_structure),
            ("Environment setup", validator.test_environment_setup),
            ("Webhook generator", validator.test_webhook_generator),
            ("NBP mock service", validator.test_nbp_mock_service),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                if asyncio.iscoroutinefunction(test_func):
                    await test_func()
                else:
                    test_func()
                print(f"✅ {test_name}")
                passed += 1
            except Exception as e:
                print(f"❌ {test_name}: {e}")
                failed += 1
        
        print(f"\n📊 Validation Results: {passed} passed, {failed} failed")
        
        if failed == 0:
            print("🎉 All validation tests passed! E2E test infrastructure is ready.")
            return True
        else:
            print("⚠️  Some validation tests failed. Please fix the issues above.")
            return False
    
    # asyncio.run(run_validation())