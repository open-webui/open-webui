import redis
from open_webui.env import REDIS_URL

redis_client = redis.StrictRedis.from_url(
    REDIS_URL, decode_responses=True)


def publish_status(task_id, status):

    # Updates status in Redis
    redis_client.set(f"task_status:{task_id}", status)


def get_status(task_id):
    status = redis_client.get(f"task_status:{task_id}")
    return status
