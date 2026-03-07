import asyncio
import os
import time

import requests
from fastapi import Request


LAST_ACTIVITY_TS = time.time()


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


RUNPOD_IDLE_ENABLED = _env_bool("RUNPOD_IDLE_ENABLED", "false")
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY", "")
RUNPOD_POD_ID = os.getenv("RUNPOD_POD_ID", "")
IDLE_SHUTDOWN_MINUTES = int(os.getenv("IDLE_SHUTDOWN_MINUTES", "20"))
IDLE_CHECK_INTERVAL_SECONDS = int(os.getenv("IDLE_CHECK_INTERVAL_SECONDS", "60"))

IDLE_IGNORE_PATHS = [
    p.strip()
    for p in os.getenv(
        "IDLE_IGNORE_PATHS",
        "/health,/healthz,/static,/favicon.ico,/manifest.json,/openapi.json,/docs",
    ).split(",")
    if p.strip()
]


def should_ignore_path(path: str) -> bool:
    for ignored in IDLE_IGNORE_PATHS:
        if path.startswith(ignored):
            return True
    return False


def touch_activity() -> None:
    global LAST_ACTIVITY_TS
    LAST_ACTIVITY_TS = time.time()


async def activity_middleware(request: Request, call_next):
    path = request.url.path

    if not should_ignore_path(path):
        touch_activity()

    response = await call_next(request)
    return response


def get_idle_seconds() -> float:
    return time.time() - LAST_ACTIVITY_TS


def runpod_stop_pod() -> None:
    if not RUNPOD_API_KEY or not RUNPOD_POD_ID:
        print("runpod idle shutdown skipped: missing RUNPOD_API_KEY or RUNPOD_POD_ID")
        return

    query = """
    mutation StopPod($podId: String!) {
      podStop(input: { podId: $podId })
    }
    """

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
    }

    payload = {
        "query": query,
        "variables": {
            "podId": RUNPOD_POD_ID,
        },
    }

    try:
        resp = requests.post(
            "https://api.runpod.io/graphql",
            json=payload,
            headers=headers,
            timeout=30,
        )
        print(f"runpod stop response status: {resp.status_code}")
        print(f"runpod stop response body: {resp.text}")
        resp.raise_for_status()
    except Exception as e:
        print(f"runpod idle shutdown failed: {e}")


async def idle_shutdown_loop() -> None:
    if not RUNPOD_IDLE_ENABLED:
        print("runpod idle shutdown disabled")
        return

    print("runpod idle shutdown enabled")
    print(f"idle timeout minutes: {IDLE_SHUTDOWN_MINUTES}")
    print(f"idle check interval seconds: {IDLE_CHECK_INTERVAL_SECONDS}")
    print(f"ignored paths: {IDLE_IGNORE_PATHS}")

    touch_activity()

    while True:
        await asyncio.sleep(IDLE_CHECK_INTERVAL_SECONDS)

        idle_seconds = get_idle_seconds()
        idle_limit_seconds = IDLE_SHUTDOWN_MINUTES * 60

        print(f"runpod idle check: idle_seconds={idle_seconds:.0f}")

        if idle_seconds >= idle_limit_seconds:
            print("idle timeout reached, attempting to stop pod")
            runpod_stop_pod()
            await asyncio.sleep(5)
            os._exit(0)


def start_idle_shutdown_task(app) -> None:
    @app.on_event("startup")
    async def _startup_idle_shutdown():
        if RUNPOD_IDLE_ENABLED:
            asyncio.create_task(idle_shutdown_loop())