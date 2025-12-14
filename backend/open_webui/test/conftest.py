from __future__ import annotations

import atexit
import os
import sys
import time
from pathlib import Path
from typing import Final

import docker
from docker.errors import NotFound
from pytest_docker.plugin import get_docker_ip
from sqlalchemy import create_engine, text

_MANAGED_POSTGRES_ENV: Final[str] = "OPEN_WEBUI_TEST_MANAGED_POSTGRES"
_USE_EXISTING_DB_ENV: Final[str] = "OPEN_WEBUI_TEST_USE_EXISTING_DATABASE_URL"

_POSTGRES_CONTAINER_NAME: Final[str] = "postgres-test-container-will-get-deleted"
_POSTGRES_IMAGE: Final[str] = "postgres:16.2"
_POSTGRES_HOST_PORT: Final[int] = 8081
_POSTGRES_ENV_VARS: Final[dict[str, str]] = {
    "POSTGRES_USER": "user",
    "POSTGRES_PASSWORD": "example",
    "POSTGRES_DB": "openwebui",
}

_docker_client = None


def _ensure_test_import_paths() -> None:
    # These tests expect:
    # - `import open_webui` to resolve from `backend/`
    # - `import main` and `import test.*` to resolve from `backend/open_webui/`
    test_dir = Path(__file__).resolve().parent
    open_webui_dir = test_dir.parent
    backend_dir = open_webui_dir.parent

    for path in (open_webui_dir, backend_dir):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


def _create_db_url() -> str:
    host = get_docker_ip()
    user = _POSTGRES_ENV_VARS["POSTGRES_USER"]
    pw = _POSTGRES_ENV_VARS["POSTGRES_PASSWORD"]
    db = _POSTGRES_ENV_VARS["POSTGRES_DB"]
    return f"postgresql://{user}:{pw}@{host}:{_POSTGRES_HOST_PORT}/{db}"


def _wait_for_postgres(database_url: str, *, timeout_s: float = 30.0) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)
    deadline = time.time() + timeout_s
    last_exc: Exception | None = None
    while time.time() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:
            last_exc = exc
            time.sleep(0.5)

    raise RuntimeError("Postgres did not become ready in time") from last_exc


def _ensure_managed_postgres() -> None:
    global _docker_client

    if os.environ.get(_MANAGED_POSTGRES_ENV) == "1":
        return

    if os.environ.get(_USE_EXISTING_DB_ENV, "").lower() == "true":
        os.environ[_MANAGED_POSTGRES_ENV] = "0"
        return

    _docker_client = docker.from_env()

    try:
        container = _docker_client.containers.get(_POSTGRES_CONTAINER_NAME)
        if container.status != "running":
            container.start()
    except NotFound:
        _docker_client.containers.run(
            _POSTGRES_IMAGE,
            detach=True,
            environment=_POSTGRES_ENV_VARS,
            name=_POSTGRES_CONTAINER_NAME,
            ports={5432: ("0.0.0.0", _POSTGRES_HOST_PORT)},
            command="postgres -c log_statement=all",
        )

    database_url = _create_db_url()
    os.environ["DATABASE_URL"] = database_url
    os.environ[_MANAGED_POSTGRES_ENV] = "1"
    _wait_for_postgres(database_url)


def _cleanup_managed_postgres() -> None:
    global _docker_client

    if os.environ.get(_MANAGED_POSTGRES_ENV) != "1":
        return

    if _docker_client is None:
        try:
            _docker_client = docker.from_env()
        except Exception:
            return

    try:
        _docker_client.containers.get(_POSTGRES_CONTAINER_NAME).remove(force=True)
    except Exception:
        return


_ensure_test_import_paths()
_ensure_managed_postgres()
atexit.register(_cleanup_managed_postgres)

