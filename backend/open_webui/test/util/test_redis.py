import pytest
from unittest.mock import Mock, patch, AsyncMock
import redis
from open_webui.utils.redis import (
    SentinelRedisProxy,
    parse_redis_service_url,
    get_redis_connection,
    get_sentinels_from_env,
    MAX_RETRY_COUNT,
)
import inspect


class TestSentinelRedisProxy:
    """Test Redis Sentinel failover functionality"""

    def test_parse_redis_service_url_valid(self):
        """Test parsing valid Redis service URL"""
        url = "redis://user:pass@mymaster:6379/0"
        result = parse_redis_service_url(url)

        assert result["username"] == "user"
        assert result["password"] == "pass"
        assert result["service"] == "mymaster"
        assert result["port"] == 6379
        assert result["db"] == 0

    def test_parse_redis_service_url_defaults(self):
        """Test parsing Redis service URL with defaults"""
        url = "redis://mymaster"
        result = parse_redis_service_url(url)

        assert result["username"] is None
        assert result["password"] is None
        assert result["service"] == "mymaster"
        assert result["port"] == 6379
        assert result["db"] == 0

    def test_parse_redis_service_url_invalid_scheme(self):
        """Test parsing invalid URL scheme"""
        with pytest.raises(ValueError, match="Invalid Redis URL scheme"):
            parse_redis_service_url("http://invalid")

    def test_get_sentinels_from_env(self):
        """Test parsing sentinel hosts from environment"""
        hosts = "sentinel1,sentinel2,sentinel3"
        port = "26379"

        result = get_sentinels_from_env(hosts, port)
        expected = [("sentinel1", 26379), ("sentinel2", 26379), ("sentinel3", 26379)]

        assert result == expected

    def test_get_sentinels_from_env_empty(self):
        """Test empty sentinel hosts"""
        result = get_sentinels_from_env(None, "26379")
        assert result == []

    @patch("redis.sentinel.Sentinel")
    def test_sentinel_redis_proxy_sync_success(self, mock_sentinel_class):
        """Test successful sync operation with SentinelRedisProxy"""
        mock_sentinel = Mock()
        mock_master = Mock()
        mock_master.get.return_value = "test_value"
        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=False)

        # Test attribute access
        get_method = proxy.__getattr__("get")
        result = get_method("test_key")

        assert result == "test_value"
        mock_sentinel.master_for.assert_called_with("mymaster")
        mock_master.get.assert_called_with("test_key")

    @patch("redis.sentinel.Sentinel")
    @pytest.mark.asyncio
    async def test_sentinel_redis_proxy_async_success(self, mock_sentinel_class):
        """Test successful async operation with SentinelRedisProxy"""
        mock_sentinel = Mock()
        mock_master = Mock()
        mock_master.get = AsyncMock(return_value="test_value")
        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=True)

        # Test async attribute access
        get_method = proxy.__getattr__("get")
        result = await get_method("test_key")

        assert result == "test_value"
        mock_sentinel.master_for.assert_called_with("mymaster")
        mock_master.get.assert_called_with("test_key")

    @patch("redis.sentinel.Sentinel")
    def test_sentinel_redis_proxy_failover_retry(self, mock_sentinel_class):
        """Test retry mechanism during failover"""
        mock_sentinel = Mock()
        mock_master = Mock()

        # First call fails, second succeeds
        mock_master.get.side_effect = [
            redis.exceptions.ConnectionError("Master down"),
            "test_value",
        ]
        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=False)

        get_method = proxy.__getattr__("get")
        result = get_method("test_key")

        assert result == "test_value"
        assert mock_master.get.call_count == 2

    @patch("redis.sentinel.Sentinel")
    def test_sentinel_redis_proxy_max_retries_exceeded(self, mock_sentinel_class):
        """Test failure after max retries exceeded"""
        mock_sentinel = Mock()
        mock_master = Mock()

        # All calls fail
        mock_master.get.side_effect = redis.exceptions.ConnectionError("Master down")
        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=False)

        get_method = proxy.__getattr__("get")

        with pytest.raises(redis.exceptions.ConnectionError):
            get_method("test_key")

        assert mock_master.get.call_count == MAX_RETRY_COUNT

    @patch("redis.sentinel.Sentinel")
    def test_sentinel_redis_proxy_readonly_error_retry(self, mock_sentinel_class):
        """Test retry on ReadOnlyError"""
        mock_sentinel = Mock()
        mock_master = Mock()

        # First call gets ReadOnlyError (old master), second succeeds (new master)
        mock_master.get.side_effect = [
            redis.exceptions.ReadOnlyError("Read only"),
            "test_value",
        ]
        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=False)

        get_method = proxy.__getattr__("get")
        result = get_method("test_key")

        assert result == "test_value"
        assert mock_master.get.call_count == 2

    @patch("redis.sentinel.Sentinel")
    def test_sentinel_redis_proxy_factory_methods(self, mock_sentinel_class):
        """Test factory methods are passed through directly"""
        mock_sentinel = Mock()
        mock_master = Mock()
        mock_pipeline = Mock()
        mock_master.pipeline.return_value = mock_pipeline
        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=False)

        # Factory methods should be passed through without wrapping
        pipeline_method = proxy.__getattr__("pipeline")
        result = pipeline_method()

        assert result == mock_pipeline
        mock_master.pipeline.assert_called_once()

    @patch("redis.sentinel.Sentinel")
    @patch("redis.from_url")
    def test_get_redis_connection_with_sentinel(
        self, mock_from_url, mock_sentinel_class
    ):
        """Test getting Redis connection with Sentinel"""
        mock_sentinel = Mock()
        mock_sentinel_class.return_value = mock_sentinel

        sentinels = [("sentinel1", 26379), ("sentinel2", 26379)]
        redis_url = "redis://user:pass@mymaster:6379/0"

        result = get_redis_connection(
            redis_url=redis_url, redis_sentinels=sentinels, async_mode=False
        )

        assert isinstance(result, SentinelRedisProxy)
        mock_sentinel_class.assert_called_once()
        mock_from_url.assert_not_called()

    @patch("redis.Redis.from_url")
    def test_get_redis_connection_without_sentinel(self, mock_from_url):
        """Test getting Redis connection without Sentinel"""
        mock_redis = Mock()
        mock_from_url.return_value = mock_redis

        redis_url = "redis://localhost:6379/0"

        result = get_redis_connection(
            redis_url=redis_url, redis_sentinels=None, async_mode=False
        )

        assert result == mock_redis
        mock_from_url.assert_called_once_with(redis_url, decode_responses=True)

    @patch("redis.asyncio.from_url")
    def test_get_redis_connection_without_sentinel_async(self, mock_from_url):
        """Test getting async Redis connection without Sentinel"""
        mock_redis = Mock()
        mock_from_url.return_value = mock_redis

        redis_url = "redis://localhost:6379/0"

        result = get_redis_connection(
            redis_url=redis_url, redis_sentinels=None, async_mode=True
        )

        assert result == mock_redis
        mock_from_url.assert_called_once_with(redis_url, decode_responses=True)


class TestSentinelRedisProxyCommands:
    """Test Redis commands through SentinelRedisProxy"""

    @patch("redis.sentinel.Sentinel")
    def test_hash_commands_sync(self, mock_sentinel_class):
        """Test Redis hash commands in sync mode"""
        mock_sentinel = Mock()
        mock_master = Mock()

        # Mock hash command responses
        mock_master.hset.return_value = 1
        mock_master.hget.return_value = "test_value"
        mock_master.hgetall.return_value = {"key1": "value1", "key2": "value2"}
        mock_master.hdel.return_value = 1

        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=False)

        # Test hset
        hset_method = proxy.__getattr__("hset")
        result = hset_method("test_hash", "field1", "value1")
        assert result == 1
        mock_master.hset.assert_called_with("test_hash", "field1", "value1")

        # Test hget
        hget_method = proxy.__getattr__("hget")
        result = hget_method("test_hash", "field1")
        assert result == "test_value"
        mock_master.hget.assert_called_with("test_hash", "field1")

        # Test hgetall
        hgetall_method = proxy.__getattr__("hgetall")
        result = hgetall_method("test_hash")
        assert result == {"key1": "value1", "key2": "value2"}
        mock_master.hgetall.assert_called_with("test_hash")

        # Test hdel
        hdel_method = proxy.__getattr__("hdel")
        result = hdel_method("test_hash", "field1")
        assert result == 1
        mock_master.hdel.assert_called_with("test_hash", "field1")

    @patch("redis.sentinel.Sentinel")
    @pytest.mark.asyncio
    async def test_hash_commands_async(self, mock_sentinel_class):
        """Test Redis hash commands in async mode"""
        mock_sentinel = Mock()
        mock_master = Mock()

        # Mock async hash command responses
        mock_master.hset = AsyncMock(return_value=1)
        mock_master.hget = AsyncMock(return_value="test_value")
        mock_master.hgetall = AsyncMock(
            return_value={"key1": "value1", "key2": "value2"}
        )

        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=True)

        # Test hset
        hset_method = proxy.__getattr__("hset")
        result = await hset_method("test_hash", "field1", "value1")
        assert result == 1
        mock_master.hset.assert_called_with("test_hash", "field1", "value1")

        # Test hget
        hget_method = proxy.__getattr__("hget")
        result = await hget_method("test_hash", "field1")
        assert result == "test_value"
        mock_master.hget.assert_called_with("test_hash", "field1")

        # Test hgetall
        hgetall_method = proxy.__getattr__("hgetall")
        result = await hgetall_method("test_hash")
        assert result == {"key1": "value1", "key2": "value2"}
        mock_master.hgetall.assert_called_with("test_hash")

    @patch("redis.sentinel.Sentinel")
    def test_string_commands_sync(self, mock_sentinel_class):
        """Test Redis string commands in sync mode"""
        mock_sentinel = Mock()
        mock_master = Mock()

        # Mock string command responses
        mock_master.set.return_value = True
        mock_master.get.return_value = "test_value"
        mock_master.delete.return_value = 1
        mock_master.exists.return_value = True

        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=False)

        # Test set
        set_method = proxy.__getattr__("set")
        result = set_method("test_key", "test_value")
        assert result is True
        mock_master.set.assert_called_with("test_key", "test_value")

        # Test get
        get_method = proxy.__getattr__("get")
        result = get_method("test_key")
        assert result == "test_value"
        mock_master.get.assert_called_with("test_key")

        # Test delete
        delete_method = proxy.__getattr__("delete")
        result = delete_method("test_key")
        assert result == 1
        mock_master.delete.assert_called_with("test_key")

        # Test exists
        exists_method = proxy.__getattr__("exists")
        result = exists_method("test_key")
        assert result is True
        mock_master.exists.assert_called_with("test_key")

    @patch("redis.sentinel.Sentinel")
    def test_list_commands_sync(self, mock_sentinel_class):
        """Test Redis list commands in sync mode"""
        mock_sentinel = Mock()
        mock_master = Mock()

        # Mock list command responses
        mock_master.lpush.return_value = 1
        mock_master.rpop.return_value = "test_value"
        mock_master.llen.return_value = 5
        mock_master.lrange.return_value = ["item1", "item2", "item3"]

        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=False)

        # Test lpush
        lpush_method = proxy.__getattr__("lpush")
        result = lpush_method("test_list", "item1")
        assert result == 1
        mock_master.lpush.assert_called_with("test_list", "item1")

        # Test rpop
        rpop_method = proxy.__getattr__("rpop")
        result = rpop_method("test_list")
        assert result == "test_value"
        mock_master.rpop.assert_called_with("test_list")

        # Test llen
        llen_method = proxy.__getattr__("llen")
        result = llen_method("test_list")
        assert result == 5
        mock_master.llen.assert_called_with("test_list")

        # Test lrange
        lrange_method = proxy.__getattr__("lrange")
        result = lrange_method("test_list", 0, -1)
        assert result == ["item1", "item2", "item3"]
        mock_master.lrange.assert_called_with("test_list", 0, -1)

    @patch("redis.sentinel.Sentinel")
    def test_pubsub_commands_sync(self, mock_sentinel_class):
        """Test Redis pubsub commands in sync mode"""
        mock_sentinel = Mock()
        mock_master = Mock()
        mock_pubsub = Mock()

        # Mock pubsub responses
        mock_master.pubsub.return_value = mock_pubsub
        mock_master.publish.return_value = 1
        mock_pubsub.subscribe.return_value = None
        mock_pubsub.get_message.return_value = {"type": "message", "data": "test_data"}

        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=False)

        # Test pubsub (factory method - should pass through)
        pubsub_method = proxy.__getattr__("pubsub")
        result = pubsub_method()
        assert result == mock_pubsub
        mock_master.pubsub.assert_called_once()

        # Test publish
        publish_method = proxy.__getattr__("publish")
        result = publish_method("test_channel", "test_message")
        assert result == 1
        mock_master.publish.assert_called_with("test_channel", "test_message")

    @patch("redis.sentinel.Sentinel")
    def test_pipeline_commands_sync(self, mock_sentinel_class):
        """Test Redis pipeline commands in sync mode"""
        mock_sentinel = Mock()
        mock_master = Mock()
        mock_pipeline = Mock()

        # Mock pipeline responses
        mock_master.pipeline.return_value = mock_pipeline
        mock_pipeline.set.return_value = mock_pipeline
        mock_pipeline.get.return_value = mock_pipeline
        mock_pipeline.execute.return_value = [True, "test_value"]

        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=False)

        # Test pipeline (factory method - should pass through)
        pipeline_method = proxy.__getattr__("pipeline")
        result = pipeline_method()
        assert result == mock_pipeline
        mock_master.pipeline.assert_called_once()

    @patch("redis.sentinel.Sentinel")
    def test_commands_with_failover_retry(self, mock_sentinel_class):
        """Test Redis commands with failover retry mechanism"""
        mock_sentinel = Mock()
        mock_master = Mock()

        # First call fails with connection error, second succeeds
        mock_master.hget.side_effect = [
            redis.exceptions.ConnectionError("Connection failed"),
            "recovered_value",
        ]

        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=False)

        # Test hget with retry
        hget_method = proxy.__getattr__("hget")
        result = hget_method("test_hash", "field1")

        assert result == "recovered_value"
        assert mock_master.hget.call_count == 2

        # Verify both calls were made with same parameters
        expected_calls = [(("test_hash", "field1"),), (("test_hash", "field1"),)]
        actual_calls = [call.args for call in mock_master.hget.call_args_list]
        assert actual_calls == expected_calls

    @patch("redis.sentinel.Sentinel")
    def test_commands_with_readonly_error_retry(self, mock_sentinel_class):
        """Test Redis commands with ReadOnlyError retry mechanism"""
        mock_sentinel = Mock()
        mock_master = Mock()

        # First call fails with ReadOnlyError, second succeeds
        mock_master.hset.side_effect = [
            redis.exceptions.ReadOnlyError(
                "READONLY You can't write against a read only replica"
            ),
            1,
        ]

        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=False)

        # Test hset with retry
        hset_method = proxy.__getattr__("hset")
        result = hset_method("test_hash", "field1", "value1")

        assert result == 1
        assert mock_master.hset.call_count == 2

        # Verify both calls were made with same parameters
        expected_calls = [
            (("test_hash", "field1", "value1"),),
            (("test_hash", "field1", "value1"),),
        ]
        actual_calls = [call.args for call in mock_master.hset.call_args_list]
        assert actual_calls == expected_calls

    @patch("redis.sentinel.Sentinel")
    @pytest.mark.asyncio
    async def test_async_commands_with_failover_retry(self, mock_sentinel_class):
        """Test async Redis commands with failover retry mechanism"""
        mock_sentinel = Mock()
        mock_master = Mock()

        # First call fails with connection error, second succeeds
        mock_master.hget = AsyncMock(
            side_effect=[
                redis.exceptions.ConnectionError("Connection failed"),
                "recovered_value",
            ]
        )

        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=True)

        # Test async hget with retry
        hget_method = proxy.__getattr__("hget")
        result = await hget_method("test_hash", "field1")

        assert result == "recovered_value"
        assert mock_master.hget.call_count == 2

        # Verify both calls were made with same parameters
        expected_calls = [(("test_hash", "field1"),), (("test_hash", "field1"),)]
        actual_calls = [call.args for call in mock_master.hget.call_args_list]
        assert actual_calls == expected_calls


class TestSentinelRedisProxyFactoryMethods:
    """Test Redis factory methods in async mode - these are special cases that remain sync"""

    @patch("redis.sentinel.Sentinel")
    @pytest.mark.asyncio
    async def test_pubsub_factory_method_async(self, mock_sentinel_class):
        """Test pubsub factory method in async mode - should pass through without wrapping"""
        mock_sentinel = Mock()
        mock_master = Mock()
        mock_pubsub = Mock()

        # Mock pubsub factory method
        mock_master.pubsub.return_value = mock_pubsub
        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=True)

        # Test pubsub factory method - should NOT be wrapped as async
        pubsub_method = proxy.__getattr__("pubsub")
        result = pubsub_method()

        assert result == mock_pubsub
        mock_master.pubsub.assert_called_once()

        # Verify it's not wrapped as async (no await needed)
        assert not inspect.iscoroutine(result)

    @patch("redis.sentinel.Sentinel")
    @pytest.mark.asyncio
    async def test_pipeline_factory_method_async(self, mock_sentinel_class):
        """Test pipeline factory method in async mode - should pass through without wrapping"""
        mock_sentinel = Mock()
        mock_master = Mock()
        mock_pipeline = Mock()

        # Mock pipeline factory method
        mock_master.pipeline.return_value = mock_pipeline
        mock_pipeline.set.return_value = mock_pipeline
        mock_pipeline.get.return_value = mock_pipeline
        mock_pipeline.execute.return_value = [True, "test_value"]

        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=True)

        # Test pipeline factory method - should NOT be wrapped as async
        pipeline_method = proxy.__getattr__("pipeline")
        result = pipeline_method()

        assert result == mock_pipeline
        mock_master.pipeline.assert_called_once()

        # Verify it's not wrapped as async (no await needed)
        assert not inspect.iscoroutine(result)

        # Test pipeline usage (these should also be sync)
        pipeline_result = result.set("key", "value").get("key").execute()
        assert pipeline_result == [True, "test_value"]

    @patch("redis.sentinel.Sentinel")
    @pytest.mark.asyncio
    async def test_factory_methods_vs_regular_commands_async(self, mock_sentinel_class):
        """Test that factory methods behave differently from regular commands in async mode"""
        mock_sentinel = Mock()
        mock_master = Mock()

        # Mock both factory method and regular command
        mock_pubsub = Mock()
        mock_master.pubsub.return_value = mock_pubsub
        mock_master.get = AsyncMock(return_value="test_value")

        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=True)

        # Test factory method - should NOT be wrapped
        pubsub_method = proxy.__getattr__("pubsub")
        pubsub_result = pubsub_method()

        # Test regular command - should be wrapped as async
        get_method = proxy.__getattr__("get")
        get_result = get_method("test_key")

        # Factory method returns directly
        assert pubsub_result == mock_pubsub
        assert not inspect.iscoroutine(pubsub_result)

        # Regular command returns coroutine
        assert inspect.iscoroutine(get_result)

        # Regular command needs await
        actual_value = await get_result
        assert actual_value == "test_value"

    @patch("redis.sentinel.Sentinel")
    @pytest.mark.asyncio
    async def test_factory_methods_with_failover_async(self, mock_sentinel_class):
        """Test factory methods with failover in async mode"""
        mock_sentinel = Mock()
        mock_master = Mock()

        # First call fails, second succeeds
        mock_pubsub = Mock()
        mock_master.pubsub.side_effect = [
            redis.exceptions.ConnectionError("Connection failed"),
            mock_pubsub,
        ]

        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=True)

        # Test pubsub factory method with failover
        pubsub_method = proxy.__getattr__("pubsub")
        result = pubsub_method()

        assert result == mock_pubsub
        assert mock_master.pubsub.call_count == 2  # Retry happened

        # Verify it's still not wrapped as async after retry
        assert not inspect.iscoroutine(result)

    @patch("redis.sentinel.Sentinel")
    @pytest.mark.asyncio
    async def test_monitor_factory_method_async(self, mock_sentinel_class):
        """Test monitor factory method in async mode - should pass through without wrapping"""
        mock_sentinel = Mock()
        mock_master = Mock()
        mock_monitor = Mock()

        # Mock monitor factory method
        mock_master.monitor.return_value = mock_monitor
        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=True)

        # Test monitor factory method - should NOT be wrapped as async
        monitor_method = proxy.__getattr__("monitor")
        result = monitor_method()

        assert result == mock_monitor
        mock_master.monitor.assert_called_once()

        # Verify it's not wrapped as async (no await needed)
        assert not inspect.iscoroutine(result)

    @patch("redis.sentinel.Sentinel")
    @pytest.mark.asyncio
    async def test_client_factory_method_async(self, mock_sentinel_class):
        """Test client factory method in async mode - should pass through without wrapping"""
        mock_sentinel = Mock()
        mock_master = Mock()
        mock_client = Mock()

        # Mock client factory method
        mock_master.client.return_value = mock_client
        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=True)

        # Test client factory method - should NOT be wrapped as async
        client_method = proxy.__getattr__("client")
        result = client_method()

        assert result == mock_client
        mock_master.client.assert_called_once()

        # Verify it's not wrapped as async (no await needed)
        assert not inspect.iscoroutine(result)

    @patch("redis.sentinel.Sentinel")
    @pytest.mark.asyncio
    async def test_transaction_factory_method_async(self, mock_sentinel_class):
        """Test transaction factory method in async mode - should pass through without wrapping"""
        mock_sentinel = Mock()
        mock_master = Mock()
        mock_transaction = Mock()

        # Mock transaction factory method
        mock_master.transaction.return_value = mock_transaction
        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=True)

        # Test transaction factory method - should NOT be wrapped as async
        transaction_method = proxy.__getattr__("transaction")
        result = transaction_method()

        assert result == mock_transaction
        mock_master.transaction.assert_called_once()

        # Verify it's not wrapped as async (no await needed)
        assert not inspect.iscoroutine(result)

    @patch("redis.sentinel.Sentinel")
    @pytest.mark.asyncio
    async def test_all_factory_methods_async(self, mock_sentinel_class):
        """Test all factory methods in async mode - comprehensive test"""
        mock_sentinel = Mock()
        mock_master = Mock()

        # Mock all factory methods
        mock_objects = {
            "pipeline": Mock(),
            "pubsub": Mock(),
            "monitor": Mock(),
            "client": Mock(),
            "transaction": Mock(),
        }

        for method_name, mock_obj in mock_objects.items():
            setattr(mock_master, method_name, Mock(return_value=mock_obj))

        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=True)

        # Test all factory methods
        for method_name, expected_obj in mock_objects.items():
            method = proxy.__getattr__(method_name)
            result = method()

            assert result == expected_obj
            assert not inspect.iscoroutine(result)
            getattr(mock_master, method_name).assert_called_once()

            # Reset mock for next iteration
            getattr(mock_master, method_name).reset_mock()

    @patch("redis.sentinel.Sentinel")
    @pytest.mark.asyncio
    async def test_mixed_factory_and_regular_commands_async(self, mock_sentinel_class):
        """Test using both factory methods and regular commands in async mode"""
        mock_sentinel = Mock()
        mock_master = Mock()

        # Mock pipeline factory and regular commands
        mock_pipeline = Mock()
        mock_master.pipeline.return_value = mock_pipeline
        mock_pipeline.set.return_value = mock_pipeline
        mock_pipeline.get.return_value = mock_pipeline
        mock_pipeline.execute.return_value = [True, "pipeline_value"]

        mock_master.get = AsyncMock(return_value="regular_value")

        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=True)

        # Use factory method (sync)
        pipeline = proxy.__getattr__("pipeline")()
        pipeline_result = pipeline.set("key1", "value1").get("key1").execute()

        # Use regular command (async)
        get_method = proxy.__getattr__("get")
        regular_result = await get_method("key2")

        # Verify both work correctly
        assert pipeline_result == [True, "pipeline_value"]
        assert regular_result == "regular_value"

        # Verify calls
        mock_master.pipeline.assert_called_once()
        mock_master.get.assert_called_with("key2")
