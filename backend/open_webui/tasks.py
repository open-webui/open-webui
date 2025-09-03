# tasks.py
import asyncio
import logging
from typing import Dict
from uuid import uuid4

# A dictionary to keep track of active tasks
tasks: Dict[str, asyncio.Task] = {}

log = logging.getLogger(__name__)

# Import domain assignment function at module level
try:
    from open_webui.utils.domain_group_assignment import run_domain_assignment_job

    log.info("Successfully imported domain assignment module")
except Exception as e:
    log.exception(f"Failed to import domain assignment module: {e}")
    run_domain_assignment_job = None


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


# Domain Assignment Task
domain_assignment_task_id = None


async def domain_assignment_worker():
    """
    Background worker that periodically runs domain-based group assignments.
    Runs every 30 seconds to check for new users that should be assigned to groups.
    """
    log.info("Domain assignment worker starting...")

    # Import the async service here to avoid circular imports
    try:
        from open_webui.utils.domain_group_assignment import domain_assignment_service

        log.info("Domain assignment service imported successfully")
    except ImportError as e:
        log.error(f"Failed to import domain assignment service: {e}")
        return

    log.info("Domain assignment worker started")

    # Run immediately on startup
    try:
        stats = await domain_assignment_service.process_domain_assignments()
        log.info(f"Initial domain assignment completed: {stats}")
    except Exception as e:
        log.exception(f"Error in initial domain assignment: {e}")

    while True:
        try:
            # Wait 30 seconds before next run
            await asyncio.sleep(30)

            print("DOMAIN WORKER: Running periodic domain assignment...")
            stats = await domain_assignment_service.process_domain_assignments()
            print(f"DOMAIN WORKER: Completed: {stats}")
        except Exception as e:
            log.exception(f"Error in periodic domain assignment: {e}")


def start_domain_assignment_task():
    """
    Start the domain assignment background task.
    """
    global domain_assignment_task_id

    log.info("start_domain_assignment_task() called")

    if (
        domain_assignment_task_id
        and not tasks.get(domain_assignment_task_id, {}).done()
    ):
        log.info("Domain assignment task is already running")
        return domain_assignment_task_id

    log.info("Starting domain assignment background task")

    try:
        domain_assignment_task_id, task = create_task(domain_assignment_worker())
        log.info(f"Domain assignment task created with ID: {domain_assignment_task_id}")
        return domain_assignment_task_id
    except Exception as e:
        log.exception(f"Error creating domain assignment task: {e}")
        return None


def stop_domain_assignment_task():
    """
    Stop the domain assignment background task.
    """
    global domain_assignment_task_id

    if domain_assignment_task_id:
        task = tasks.get(domain_assignment_task_id)
        if task and not task.done():
            task.cancel()
            log.info("Domain assignment task stopped")
            return True

    log.info("No domain assignment task to stop")
    return False
