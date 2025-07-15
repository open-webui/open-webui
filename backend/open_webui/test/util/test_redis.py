import pytest
from unittest.mock import Mock, patch, AsyncMock
import redis
from open_webui.utils.redis import (
    SentinelRedisProxy,
    parse_redis_service_url,
    get_redis_connection,
    get_sentinels_from_env,
    MAX_RETRY_COUNT
)


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

    @patch('redis.sentinel.Sentinel')
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

    @patch('redis.sentinel.Sentinel')
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

    @patch('redis.sentinel.Sentinel')
    def test_sentinel_redis_proxy_failover_retry(self, mock_sentinel_class):
        """Test retry mechanism during failover"""
        mock_sentinel = Mock()
        mock_master = Mock()

        # First call fails, second succeeds
        mock_master.get.side_effect = [
            redis.exceptions.ConnectionError("Master down"),
            "test_value"
        ]
        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=False)

        get_method = proxy.__getattr__("get")
        result = get_method("test_key")

        assert result == "test_value"
        assert mock_master.get.call_count == 2

    @patch('redis.sentinel.Sentinel')
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

    @patch('redis.sentinel.Sentinel')
    def test_sentinel_redis_proxy_readonly_error_retry(self, mock_sentinel_class):
        """Test retry on ReadOnlyError"""
        mock_sentinel = Mock()
        mock_master = Mock()

        # First call gets ReadOnlyError (old master), second succeeds (new master)
        mock_master.get.side_effect = [
            redis.exceptions.ReadOnlyError("Read only"),
            "test_value"
        ]
        mock_sentinel.master_for.return_value = mock_master

        proxy = SentinelRedisProxy(mock_sentinel, "mymaster", async_mode=False)

        get_method = proxy.__getattr__("get")
        result = get_method("test_key")

        assert result == "test_value"
        assert mock_master.get.call_count == 2

    @patch('redis.sentinel.Sentinel')
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

    @patch('redis.sentinel.Sentinel')
    @patch('redis.from_url')
    def test_get_redis_connection_with_sentinel(self, mock_from_url, mock_sentinel_class):
        """Test getting Redis connection with Sentinel"""
        mock_sentinel = Mock()
        mock_sentinel_class.return_value = mock_sentinel

        sentinels = [("sentinel1", 26379), ("sentinel2", 26379)]
        redis_url = "redis://user:pass@mymaster:6379/0"

        result = get_redis_connection(
            redis_url=redis_url,
            redis_sentinels=sentinels,
            async_mode=False
        )

        assert isinstance(result, SentinelRedisProxy)
        mock_sentinel_class.assert_called_once()
        mock_from_url.assert_not_called()

    @patch('redis.Redis.from_url')
    def test_get_redis_connection_without_sentinel(self, mock_from_url):
        """Test getting Redis connection without Sentinel"""
        mock_redis = Mock()
        mock_from_url.return_value = mock_redis

        redis_url = "redis://localhost:6379/0"

        result = get_redis_connection(
            redis_url=redis_url,
            redis_sentinels=None,
            async_mode=False
        )

        assert result == mock_redis
        mock_from_url.assert_called_once_with(redis_url, decode_responses=True)

    @patch('redis.asyncio.from_url')
    def test_get_redis_connection_without_sentinel_async(self, mock_from_url):
        """Test getting async Redis connection without Sentinel"""
        mock_redis = Mock()
        mock_from_url.return_value = mock_redis

        redis_url = "redis://localhost:6379/0"

        result = get_redis_connection(
            redis_url=redis_url,
            redis_sentinels=None,
            async_mode=True
        )

        assert result == mock_redis
        mock_from_url.assert_called_once_with(redis_url, decode_responses=True)