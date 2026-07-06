import asyncio
import time
from unittest.mock import MagicMock
import pytest
import open_webui.socket.main as socket_main

@pytest.mark.asyncio
async def test_periodic_usage_pool_cleanup_recovery():
    # Save original functions
    orig_aquire = socket_main.aquire_func
    orig_renew = socket_main.renew_func
    orig_release = socket_main.release_func
    orig_lock_timeout = socket_main.WEBSOCKET_REDIS_LOCK_TIMEOUT
    orig_timeout_duration = socket_main.TIMEOUT_DURATION

    # Configure short timeouts for tests
    socket_main.WEBSOCKET_REDIS_LOCK_TIMEOUT = 0.02
    socket_main.TIMEOUT_DURATION = 0.01

    try:
        # Mock behavior for periodic_usage_pool_cleanup:
        # 1. First acquire_lock fails
        # 2. Second acquire_lock succeeds
        # 3. First renew_lock succeeds
        # 4. Second renew_lock fails
        # 5. Subsequent acquire_lock succeeds and renew_lock succeeds
        
        acquire_calls = []
        renew_calls = []
        release_calls = []

        def mock_acquire():
            acquire_calls.append(True)
            if len(acquire_calls) == 1:
                return False
            return True

        def mock_renew():
            renew_calls.append(True)
            if len(renew_calls) == 2:
                return False
            return True

        def mock_release():
            release_calls.append(True)
            return True

        socket_main.aquire_func = mock_acquire
        socket_main.renew_func = mock_renew
        socket_main.release_func = mock_release

        # Populate USAGE_POOL
        socket_main.USAGE_POOL = {
            'model1': {
                'sid1': {'updated_at': int(time.time()) - 100}
            }
        }

        # Start cleanup task
        task = asyncio.create_task(socket_main.periodic_usage_pool_cleanup())

        # Give it some time to run and trigger a few loops and failures
        await asyncio.sleep(0.2)

        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Assertions
        assert len(acquire_calls) >= 2, "Should have retried lock acquisition"
        assert len(renew_calls) >= 2, "Should have called renew"
        assert len(release_calls) >= 2, "Should have released lock on breakage"
        assert 'model1' not in socket_main.USAGE_POOL, "Should have cleaned up expired entries"

    finally:
        # Restore original functions
        socket_main.aquire_func = orig_aquire
        socket_main.renew_func = orig_renew
        socket_main.release_func = orig_release
        socket_main.WEBSOCKET_REDIS_LOCK_TIMEOUT = orig_lock_timeout
        socket_main.TIMEOUT_DURATION = orig_timeout_duration


@pytest.mark.asyncio
async def test_periodic_session_pool_cleanup_recovery():
    # Save original functions
    orig_acquire = socket_main.session_aquire_func
    orig_renew = socket_main.session_renew_func
    orig_release = socket_main.session_release_func
    orig_lock_timeout = socket_main.WEBSOCKET_REDIS_LOCK_TIMEOUT
    orig_session_timeout = socket_main.SESSION_POOL_TIMEOUT

    # Configure short timeouts for tests
    socket_main.WEBSOCKET_REDIS_LOCK_TIMEOUT = 0.02
    socket_main.SESSION_POOL_TIMEOUT = 0.01

    try:
        # Mock behavior for periodic_session_pool_cleanup:
        # 1. First acquire_lock fails
        # 2. Second acquire_lock succeeds
        # 3. First renew_lock succeeds
        # 4. Second renew_lock fails
        # 5. Subsequent acquire_lock succeeds and renew_lock succeeds
        
        acquire_calls = []
        renew_calls = []
        release_calls = []

        def mock_acquire():
            acquire_calls.append(True)
            if len(acquire_calls) == 1:
                return False
            return True

        def mock_renew():
            renew_calls.append(True)
            if len(renew_calls) == 2:
                return False
            return True

        def mock_release():
            release_calls.append(True)
            return True

        socket_main.session_aquire_func = mock_acquire
        socket_main.session_renew_func = mock_renew
        socket_main.session_release_func = mock_release

        # Populate SESSION_POOL
        socket_main.SESSION_POOL = {
            'sid1': {'id': 'user1', 'last_seen_at': int(time.time()) - 100}
        }

        # Start cleanup task
        task = asyncio.create_task(socket_main.periodic_session_pool_cleanup())

        # Give it some time to run and trigger a few loops and failures
        await asyncio.sleep(0.2)

        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Assertions
        assert len(acquire_calls) >= 2, "Should have retried lock acquisition"
        assert len(renew_calls) >= 2, "Should have called renew"
        assert len(release_calls) >= 2, "Should have released lock on breakage"
        assert 'sid1' not in socket_main.SESSION_POOL, "Should have cleaned up expired session"

    finally:
        # Restore original functions
        socket_main.session_aquire_func = orig_acquire
        socket_main.session_renew_func = orig_renew
        socket_main.session_release_func = orig_release
        socket_main.WEBSOCKET_REDIS_LOCK_TIMEOUT = orig_lock_timeout
        socket_main.SESSION_POOL_TIMEOUT = orig_session_timeout
