import json
import logging
import time
from typing import Optional, Dict, Any

import redis

from .config import REDIS_URL, QUEUE_NAME

log = logging.getLogger(__name__)


class JobQueue:
    def __init__(self):
        self.redis = redis.from_url(REDIS_URL, decode_responses=True)
        self.queue_name = QUEUE_NAME

    def enqueue(self, job_data: dict) -> str:
        job_id = job_data.get('job_id', '')
        self.redis.lpush(self.queue_name, json.dumps(job_data))
        log.info(f'Enqueued job {job_id}')
        return job_id

    def dequeue(self, timeout: int = 0) -> Optional[dict]:
        if timeout > 0:
            result = self.redis.brpop(self.queue_name, timeout=timeout)
            if result:
                _, data = result
                return json.loads(data)
        else:
            data = self.redis.rpop(self.queue_name)
            if data:
                return json.loads(data)
        return None

    def get_job_status(self, job_id: str) -> Optional[dict]:
        status_key = f'gitlab_job:{job_id}:status'
        status = self.redis.get(status_key)
        if status:
            return json.loads(status)
        return None

    def set_job_status(self, job_id: str, status: str, progress: int = 0, message: str = '', details: dict = None):
        status_key = f'gitlab_job:{job_id}:status'
        status_data = {
            'status': status,
            'progress': progress,
            'message': message,
            'details': details or {},
        }
        self.redis.set(status_key, json.dumps(status_data))
        log.debug(f'Job {job_id} status: {status} ({progress}%) - {message}')

    def update_progress(self, job_id: str, progress: int, message: str = '', details: dict = None):
        current = self.get_job_status(job_id) or {'status': 'processing'}
        current['progress'] = progress
        current['message'] = message
        if details:
            current['details'] = details
        status_key = f'gitlab_job:{job_id}:status'
        self.redis.set(status_key, json.dumps(current))

    def delete_job_status(self, job_id: str):
        status_key = f'gitlab_job:{job_id}:status'
        self.redis.delete(status_key)


job_queue = JobQueue()