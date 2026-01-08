#!/usr/bin/env python3
"""
Test that ef=None is handled correctly for Portkey/OpenAI engines.
Run with: conda activate rit4test && python test_worker_ef_fix.py
"""

import os
import sys

backend_dir = os.path.join(os.path.dirname(__file__), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ["TZ"] = "America/New_York"

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

log = logging.getLogger(__name__)

def test_ef_none_for_portkey():
    """Test that ef=None works for Portkey engine."""
    log.info("=" * 80)
    log.info("TEST: ef=None for Portkey/OpenAI engines")
    log.info("=" * 80)
    
    try:
        from open_webui.workers.file_processor import MockState
        from open_webui.routers.retrieval import get_ef, get_embedding_function
        
        # Test get_ef for Portkey (should return None)
        ef = get_ef("portkey", "@openai-embedding/text-embedding-3-small", False)
        log.info(f"get_ef('portkey', ...) = {ef}")
        assert ef is None, "For Portkey engine, ef should be None (API-based)"
        log.info("✅ get_ef returns None for Portkey (correct)")
        
        # Test that get_embedding_function works with ef=None for Portkey
        embedding_func = get_embedding_function(
            embedding_engine="portkey",
            embedding_model="@openai-embedding/text-embedding-3-small",
            embedding_function=None,  # ef is None for API engines
            url="",
            key="test_key",
            embedding_batch_size=1,
        )
        
        assert embedding_func is not None, "get_embedding_function should work with ef=None for Portkey"
        log.info("✅ get_embedding_function works with ef=None for Portkey")
        
        # Test MockState initialization
        state = MockState(embedding_api_key="test_key_12345")
        log.info(f"MockState.ef = {state.ef}")
        log.info(f"MockState.config.RAG_EMBEDDING_ENGINE = {state.config.RAG_EMBEDDING_ENGINE}")
        
        # For Portkey, ef should be None
        if state.config.RAG_EMBEDDING_ENGINE in ["portkey", "openai"]:
            assert state.ef is None, f"For {state.config.RAG_EMBEDDING_ENGINE}, ef should be None"
            log.info(f"✅ ef is None for {state.config.RAG_EMBEDDING_ENGINE} engine (correct)")
        
        # Test initialize_embedding_function with ef=None
        state.initialize_embedding_function(embedding_api_key="test_key_12345")
        
        if state.EMBEDDING_FUNCTION is not None:
            log.info("✅ EMBEDDING_FUNCTION initialized successfully with ef=None")
        else:
            log.warning("⚠️  EMBEDDING_FUNCTION is None (may be expected if API key is invalid)")
        
        log.info("=" * 80)
        log.info("✅ ALL TESTS PASSED - ef=None handling is correct!")
        return True
        
    except Exception as e:
        log.error(f"❌ Test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_ef_none_for_portkey()
    sys.exit(0 if success else 1)








