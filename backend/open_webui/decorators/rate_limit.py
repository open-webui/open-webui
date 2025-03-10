from functools import wraps
from fastapi import HTTPException, status
from open_webui.internal.redis import inc_rate_usage, get_rate_usage
from open_webui.models.users import UserModel
from open_webui.env import (
    ENABLE_RATE_LIMIT
)

async def should_limit_user(user: UserModel) -> bool:
    """
    Apply rate limiting per user, per minute
    """
    if not ENABLE_RATE_LIMIT:
        return False
    
    current_request_count = await inc_rate_usage(user, 'request')

    # Check rate limit for request
    if user.rate_limit and user.rate_limit.request_limit_per_minute and current_request_count > user.rate_limit.request_limit_per_minute:
        return True

    current_token_count = await get_rate_usage(user, 'token')
    # Check rate limit for token
    if user.rate_limit and user.rate_limit.token_limit_per_minute and current_token_count > user.rate_limit.token_limit_per_minute:
        return True
    
    return False

def rate_limit(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if await should_limit_user(kwargs["user"]):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests"
                )
            return await func(*args, **kwargs)
        return wrapper