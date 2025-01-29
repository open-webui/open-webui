import redis
from open_webui.env import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD

# Redis configuration
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, decode_responses=True)
