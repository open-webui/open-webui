import redis
from open_webui.env import CELERY_RESULT_BACKEND

redis_client = redis.StrictRedis.from_url(
    CELERY_RESULT_BACKEND, decode_responses=True)


def get_status(task_id):
    status = redis_client.get(f"task_status:{task_id}")
    return status
