from redis.asyncio import Redis
from datetime import datetime
from open_webui.env import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_PASSWORD
)


redis_client = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    decode_responses=True,
    password=REDIS_PASSWORD,
)

async def inc_rate_usage(user: str, type: str, amount: int = 1) -> int:
    # Increment our most recent redis key
    username = user.email
    now = datetime.utcnow()
    current_minute = now.strftime("%Y-%m-%dT%H:%M")

    redis_request_key = f"rate_limit_{type}_{username}_{current_minute}"
    current_request_count = await redis_client.incr(redis_request_key, amount)

    # If we just created a new key (count is 1) set an expiration
    if current_request_count == 1:
        await redis_client.expire(name=redis_request_key, time=60)
    return current_request_count

async def get_rate_usage(user: str, type: str) -> int:
    username = user.email
    now = datetime.utcnow()
    current_minute = now.strftime("%Y-%m-%dT%H:%M")

    redis_request_key = f"rate_limit_{type}_{username}_{current_minute}"
    current_request_count = await redis_client.get(redis_request_key)

    return int(current_request_count) if current_request_count is not None else 0