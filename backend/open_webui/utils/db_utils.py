import redis
from open_webui.env import REDIS_URL

redis_client = redis.StrictRedis.from_url(
    REDIS_URL, decode_responses=True)


def get_status(task_id):
    status = redis_client.get(f"task_status:{task_id}")
    return status
