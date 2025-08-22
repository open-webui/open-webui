# tasks.py
import asyncio
from typing import Dict
from uuid import uuid4

# A dictionary to keep track of active tasks
tasks: Dict[str, asyncio.Task] = {}
chat_tasks = {}


def cleanup_task(task_id: str, id=None):
    """
    Remove a completed or canceled task from the global `tasks` dictionary.
    """
    tasks.pop(task_id, None)  # Remove the task if it exists

    # If an ID is provided, remove the task from the chat_tasks dictionary
    if id and task_id in chat_tasks.get(id, []):
        chat_tasks[id].remove(task_id)
        if not chat_tasks[id]:  # If no tasks left for this ID, remove the entry
            chat_tasks.pop(id, None)


def create_task(coroutine, id=None):
    """
    Create a new asyncio task and add it to the global task dictionary.
    """
    task_id = str(uuid4())  # Generate a unique ID for the task
    task = asyncio.create_task(coroutine)  # Create the task

    # Add a done callback for cleanup
    task.add_done_callback(lambda t: cleanup_task(task_id, id))
    tasks[task_id] = task

    # If an ID is provided, associate the task with that ID
    if chat_tasks.get(id):
        chat_tasks[id].append(task_id)
    else:
        chat_tasks[id] = [task_id]

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


def list_task_ids_by_chat_id(id):
    """
    List all tasks associated with a specific ID.
    """
    return chat_tasks.get(id, [])


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
