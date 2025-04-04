import socketio
import redis
from redis import asyncio as aioredis
from urllib.parse import urlparse


def parse_redis_sentinel_url(redis_url):
    parsed_url = urlparse(redis_url)
    if parsed_url.scheme != "redis":
        raise ValueError("Invalid Redis URL scheme. Must be 'redis'.")

    return {
        "username": parsed_url.username or None,
        "password": parsed_url.password or None,
        "service": parsed_url.hostname or "mymaster",
        "port": parsed_url.port or 6379,
        "db": int(parsed_url.path.lstrip("/") or 0),
    }


def get_redis_connection(redis_url, redis_sentinels, decode_responses=True):
    if redis_sentinels:
        redis_config = parse_redis_sentinel_url(redis_url)
        sentinel = redis.sentinel.Sentinel(
            redis_sentinels,
            port=redis_config["port"],
            db=redis_config["db"],
            username=redis_config["username"],
            password=redis_config["password"],
            decode_responses=decode_responses,
        )

        # Get a master connection from Sentinel
        return sentinel.master_for(redis_config["service"])
    else:
        # Standard Redis connection
        return redis.Redis.from_url(redis_url, decode_responses=decode_responses)


def get_sentinels_from_env(sentinel_hosts_env, sentinel_port_env):
    if sentinel_hosts_env:
        sentinel_hosts = sentinel_hosts_env.split(",")
        sentinel_port = int(sentinel_port_env)
        return [(host, sentinel_port) for host in sentinel_hosts]
    return []


class AsyncRedisSentinelManager(socketio.AsyncRedisManager):
    def __init__(
        self,
        sentinel_hosts,
        sentinel_port=26379,
        redis_port=6379,
        service="mymaster",
        db=0,
        username=None,
        password=None,
        channel="socketio",
        write_only=False,
        logger=None,
        redis_options=None,
    ):
        """
        Initialize the Redis Sentinel Manager.
        This implementation mostly replicates the __init__ of AsyncRedisManager and
        overrides _redis_connect() with a version that uses Redis Sentinel

        :param sentinel_hosts: List of Sentinel hosts
        :param sentinel_port: Sentinel Port
        :param redis_port: Redis Port (currently unsupported by aioredis!)
        :param service: Master service name in Sentinel
        :param db: Redis database to use
        :param username: Redis username (if any) (currently unsupported by aioredis!)
        :param password: Redis password (if any)
        :param channel: The channel name on which the server sends and receives
                        notifications. Must be the same in all the servers.
        :param write_only: If set to ``True``, only initialize to emit events. The
                           default of ``False`` initializes the class for emitting
                           and receiving.
        :param redis_options: additional keyword arguments to be passed to
                              ``aioredis.from_url()``.
        """
        self._sentinels = [(host, sentinel_port) for host in sentinel_hosts]
        self._redis_port = redis_port
        self._service = service
        self._db = db
        self._username = username
        self._password = password
        self._channel = channel
        self.redis_options = redis_options or {}

        # connect and call grandparent constructor
        self._redis_connect()
        super(socketio.AsyncRedisManager, self).__init__(
            channel=channel, write_only=write_only, logger=logger
        )

    def _redis_connect(self):
        """Establish connections to Redis through Sentinel."""
        sentinel = aioredis.sentinel.Sentinel(
            self._sentinels,
            port=self._redis_port,
            db=self._db,
            password=self._password,
            **self.redis_options,
        )

        self.redis = sentinel.master_for(self._service)
        self.pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
