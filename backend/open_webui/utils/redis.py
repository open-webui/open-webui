import socketio
import redis
from redis import asyncio as aioredis
from urllib.parse import urlparse


def parse_redis_service_url(redis_url):
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
        redis_config = parse_redis_service_url(redis_url)
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


def get_sentinel_url_from_env(redis_url, sentinel_hosts_env, sentinel_port_env):
    redis_config = parse_redis_service_url(redis_url)
    username = redis_config["username"] or ""
    password = redis_config["password"] or ""
    auth_part = ""
    if username or password:
        auth_part = f"{username}:{password}@"
    hosts_part = ",".join(
        f"{host}:{sentinel_port_env}" for host in sentinel_hosts_env.split(",")
    )
    return f"redis+sentinel://{auth_part}{hosts_part}/{redis_config['db']}/{redis_config['service']}"
