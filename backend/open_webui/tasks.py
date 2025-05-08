# tasks.py
import asyncio
from typing import Dict
from uuid import uuid4

from open_webui.celery_worker import celery_app
from open_webui.routers.retrieval import (
    process_file,
    process_file_async,
)
# from app.core.pdf import extract_text


@celery_app.task
def process_tasks(request, form_data, user, task_id):
    """Executa OCR e processamento do PDF de forma assíncrona."""
    try:
        # Decodifica base64 para bytes
        content = process_file_async(request=request,
                                     form_data=form_data, task_id=task_id, user=user)

        return {"status": "completed", "result": content, "cd_hash": task_id}

    except Exception as e:
        return {"status": "failed", "error": str(e), "cd_hash": task_id}


# A dictionary to keep track of active tasks
tasks: Dict[str, asyncio.Task] = {}


def cleanup_task(task_id: str):
    """
    Remove a completed or canceled task from the global `tasks` dictionary.
    """
    tasks.pop(task_id, None)  # Remove the task if it exists


def create_task(coroutine):
    """
    Create a new asyncio task and add it to the global task dictionary.
    """
    task_id = str(uuid4())  # Generate a unique ID for the task
    task = asyncio.create_task(coroutine)  # Create the task

    # Add a done callback for cleanup
    task.add_done_callback(lambda t: cleanup_task(task_id))

    tasks[task_id] = task
    return task_id, task


def get_task(task_id: str):
    """
    Retrieve a task by its task ID.
    """
    return tasks.get(task_id)


def list_tasks():
    """
    List all currently active task IDs.
    """
    return list(tasks.keys())


async def stop_task(task_id: str):
    """
    Cancel a running task and remove it from the global task list.
    """
    task = tasks.get(task_id)
    if not task:
        raise ValueError(f"Task with ID {task_id} not found.")

    task.cancel()  # Request task cancellation
    try:
        await task  # Wait for the task to handle the cancellation
    except asyncio.CancelledError:
        # Task successfully canceled
        tasks.pop(task_id, None)  # Remove it from the dictionary
        return {"status": True, "message": f"Task {task_id} successfully stopped."}

    return {"status": False, "message": f"Failed to stop task {task_id}."}
