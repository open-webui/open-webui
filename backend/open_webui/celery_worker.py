import os

from celery import Celery

celery_app = Celery(
    "worker",
    broker=os.getenv("CELERY_BROKER_URL"),
    backend="rpc://",
)


celery_app.autodiscover_tasks(["open_webui.tasks_celery"])  # <- importante!
