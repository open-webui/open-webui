import socketio
from urllib.parse import urlparse
from typing import Optional


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


def get_redis_connection(
    redis_url, redis_sentinels, async_mode=False, decode_responses=True
):
    import logging
    log = logging.getLogger(__name__)
    
    log.info(f"🔴 REDIS: get_redis_connection called with async_mode={async_mode}")
    log.info(f"🔴 REDIS: redis_url='{redis_url[:50] if redis_url else 'None'}...'")
    log.info(f"🔴 REDIS: redis_sentinels={redis_sentinels}")
    
    if async_mode:
        log.info("🔴 REDIS: Using async mode...")
        import redis.asyncio as redis

        # If using sentinel in async mode
        if redis_sentinels:
            log.info("🔴 REDIS: Using sentinel configuration...")
            redis_config = parse_redis_service_url(redis_url)
            log.info(f"🔴 REDIS: Parsed redis config: {redis_config}")
            sentinel = redis.sentinel.Sentinel(
                redis_sentinels,
                port=redis_config["port"],
                db=redis_config["db"],
                username=redis_config["username"],
                password=redis_config["password"],
                decode_responses=decode_responses,
            )
            log.info("🔴 REDIS: ✅ Sentinel created, getting master...")
            result = sentinel.master_for(redis_config["service"])
            log.info("🔴 REDIS: ✅ Redis connection via sentinel established")
            return result
        elif redis_url:
            log.info("🔴 REDIS: Using direct Redis URL connection...")
            result = redis.from_url(redis_url, decode_responses=decode_responses)
            log.info("🔴 REDIS: ✅ Redis connection via URL established")
            return result
        else:
            log.info("🔴 REDIS: No Redis URL or sentinels provided, returning None")
            return None
    else:
        log.info("🔴 REDIS: Using sync mode...")
        import redis

        if redis_sentinels:
            log.info("🔴 REDIS: Using sentinel configuration (sync)...")
            redis_config = parse_redis_service_url(redis_url)
            log.info(f"🔴 REDIS: Parsed redis config: {redis_config}")
            sentinel = redis.sentinel.Sentinel(
                redis_sentinels,
                port=redis_config["port"],
                db=redis_config["db"],
                username=redis_config["username"],
                password=redis_config["password"],
                decode_responses=decode_responses,
            )
            log.info("🔴 REDIS: ✅ Sentinel created (sync), getting master...")
            result = sentinel.master_for(redis_config["service"])
            log.info("🔴 REDIS: ✅ Redis connection via sentinel established (sync)")
            return result
        elif redis_url:
            log.info("🔴 REDIS: Using direct Redis URL connection (sync)...")
            result = redis.Redis.from_url(redis_url, decode_responses=decode_responses)
            log.info("🔴 REDIS: ✅ Redis connection via URL established (sync)")
            return result
        else:
            log.info("🔴 REDIS: No Redis URL or sentinels provided, returning None (sync)")
            return None


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
