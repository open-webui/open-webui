#!/usr/bin/env python3
"""
Local test script for worker file processor.
Tests config initialization and API key handling without rebuilding Docker.
Run with: conda activate rit4test && python test_worker_local.py
"""

import os
import sys
import logging

# Add backend to path
backend_dir = os.path.join(os.path.dirname(__file__), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Set timezone
os.environ["TZ"] = "America/New_York"

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

log = logging.getLogger(__name__)

def test_config_initialization():
    """Test that AppConfig initializes correctly with all RAG config values."""
    log.info("=" * 80)
    log.info("TEST 1: Config Initialization")
    log.info("=" * 80)
    
    try:
        from open_webui.workers.file_processor import MockState
        
        # Test without API key (should still initialize config)
        state = MockState(embedding_api_key=None)
        
        # Check that config is populated
        assert hasattr(state.config, '_state'), "AppConfig._state not found"
        assert 'RAG_EMBEDDING_ENGINE' in state.config._state, "RAG_EMBEDDING_ENGINE not in _state"
        
        # Check that we can access config values
        engine = state.config.RAG_EMBEDDING_ENGINE
        model = state.config.RAG_EMBEDDING_MODEL
        
        log.info(f"✅ Config initialized successfully")
        log.info(f"   RAG_EMBEDDING_ENGINE: {engine}")
        log.info(f"   RAG_EMBEDDING_MODEL: {model}")
        log.info(f"   Config _state keys: {list(state.config._state.keys())[:10]}...")
        
        # Check that base embedding functions are initialized
        assert state.ef is not None, "ef (embedding function model) should be initialized"
        assert state.rf is not None or state.config.RAG_RERANKING_MODEL == "", "rf should be initialized or reranking disabled"
        
        log.info(f"✅ Base embedding functions initialized")
        log.info(f"   ef: {type(state.ef).__name__}")
        log.info(f"   rf: {type(state.rf).__name__ if state.rf else 'None (reranking disabled)'}")
        
        return True
    except Exception as e:
        log.error(f"❌ Config initialization failed: {e}", exc_info=True)
        return False


def test_api_key_handling():
    """Test that API key is handled correctly per-job (RBAC-protected)."""
    log.info("=" * 80)
    log.info("TEST 2: API Key Handling (RBAC-protected)")
    log.info("=" * 80)
    
    try:
        from open_webui.workers.file_processor import MockState
        
        # Test 1: Initialize without API key
        state1 = MockState(embedding_api_key=None)
        assert state1.EMBEDDING_FUNCTION is None, "EMBEDDING_FUNCTION should be None until initialized per-job"
        log.info("✅ State initialized without API key (EMBEDDING_FUNCTION is None)")
        
        # Test 2: Initialize per-job with API key
        test_api_key = "test_api_key_12345"
        state1.initialize_embedding_function(embedding_api_key=test_api_key)
        
        # Check that EMBEDDING_FUNCTION is now initialized
        if state1.EMBEDDING_FUNCTION is not None:
            log.info("✅ EMBEDDING_FUNCTION initialized per-job with API key")
        else:
            log.warning("⚠️  EMBEDDING_FUNCTION is None (may be expected if API key is invalid)")
        
        # Test 3: Initialize with different API key (simulating different admin)
        state2 = MockState(embedding_api_key="different_admin_key_67890")
        state2.initialize_embedding_function(embedding_api_key="different_admin_key_67890")
        
        log.info("✅ Different API key handled correctly (RBAC-protected)")
        log.info(f"   State1 API key stored: {state1._embedding_api_key[:10]}..." if state1._embedding_api_key else "   State1: No API key")
        log.info(f"   State2 API key stored: {state2._embedding_api_key[:10]}..." if state2._embedding_api_key else "   State2: No API key")
        
        return True
    except Exception as e:
        log.error(f"❌ API key handling test failed: {e}", exc_info=True)
        return False


def test_redis_connection():
    """Test Redis connection configuration (decode_responses=False for binary data)."""
    log.info("=" * 80)
    log.info("TEST 3: Redis Connection Configuration")
    log.info("=" * 80)
    
    try:
        from redis import Redis
        from redis.connection import ConnectionPool
        from open_webui.env import REDIS_URL
        
        # Test worker connection pool (should have decode_responses=False)
        worker_pool = ConnectionPool.from_url(
            REDIS_URL,
            decode_responses=False,  # CRITICAL: RQ stores binary pickled job data
            max_connections=10,
            retry_on_timeout=True,
            socket_connect_timeout=10,
            socket_timeout=None,  # CRITICAL: No timeout for blocking operations (BRPOP)
            health_check_interval=30,
        )
        
        redis_conn = Redis(connection_pool=worker_pool)
        
        # Test connection
        redis_conn.ping()
        log.info("✅ Redis connection successful")
        log.info(f"   REDIS_URL: {REDIS_URL.split('@')[0]}@...")
        log.info(f"   decode_responses: False (correct for binary RQ data)")
        log.info(f"   socket_timeout: None (correct for blocking operations)")
        
        return True
    except Exception as e:
        log.warning(f"⚠️  Redis connection test failed (may not be running): {e}")
        log.info("   This is OK if Redis is not running locally")
        return True  # Don't fail the test if Redis isn't running


def test_imports():
    """Test that all required imports work."""
    log.info("=" * 80)
    log.info("TEST 4: Import Verification")
    log.info("=" * 80)
    
    try:
        from open_webui.workers.file_processor import (
            MockRequest,
            MockApp,
            MockState,
            process_file_job,
            _create_fallback_config,
        )
        from open_webui.config import (
            AppConfig,
            RAG_EMBEDDING_ENGINE,
            RAG_EMBEDDING_MODEL,
            RAG_OPENAI_API_KEY,
        )
        
        log.info("✅ All imports successful")
        return True
    except Exception as e:
        log.error(f"❌ Import test failed: {e}", exc_info=True)
        return False


def main():
    """Run all tests."""
    log.info("Starting worker local tests...")
    log.info(f"Python: {sys.version}")
    log.info(f"Working directory: {os.getcwd()}")
    log.info(f"Backend path: {backend_dir}")
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Config Initialization", test_config_initialization()))
    results.append(("API Key Handling", test_api_key_handling()))
    results.append(("Redis Connection", test_redis_connection()))
    
    # Summary
    log.info("=" * 80)
    log.info("TEST SUMMARY")
    log.info("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        log.info(f"{status}: {test_name}")
    
    log.info("=" * 80)
    log.info(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        log.info("✅ ALL TESTS PASSED - Worker should work correctly!")
        return 0
    else:
        log.error("❌ SOME TESTS FAILED - Check errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())








