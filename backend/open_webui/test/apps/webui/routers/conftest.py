import logging
import os
import time

import docker
import pytest
from unittest import mock
from pytest_docker.plugin import get_docker_ip
from fastapi.testclient import TestClient
from sqlalchemy import create_engine


log = logging.getLogger(__name__)


def get_fast_api_client():
    from open_webui.main import app

    with TestClient(app) as c:
        return c


def _create_db_url(env_vars_postgres: dict, port:int) -> str:
    host = get_docker_ip()
    user = env_vars_postgres["POSTGRES_USER"]
    pw = env_vars_postgres["POSTGRES_PASSWORD"]
    db = env_vars_postgres["POSTGRES_DB"]
    return f"postgresql://{user}:{pw}@{host}:{port}/{db}"


@pytest.fixture(scope="session")
def postgres_container():
    docker_client = docker.from_env()

    env_vars_postgres = {
        "POSTGRES_USER": "user",
        "POSTGRES_PASSWORD": "example",
        "POSTGRES_DB": "openwebui",
    }

    port = 8081
    container_name = "postgres-test-container-will-get-deleted"
    docker_client.containers.run(
        "postgres:16.2",
        detach=True,
        environment=env_vars_postgres,
        name=container_name,
        ports={5432: ("0.0.0.0", port)},
        command="postgres -c log_statement=all",
    )

    time.sleep(0.5)

    database_url = _create_db_url(env_vars_postgres, port)
    retries = 10
    db = None
    while retries > 0:
        try:
            db = create_engine(database_url, pool_pre_ping=True)
            db = db.connect()
            log.info("postgres is ready!")
            break
        except Exception as e:
            log.warning(e)
            time.sleep(3)
            retries -= 1

    if not db:
        raise Exception("Could not connect to Postgres")
    else:
        db.close()

    with mock.patch.dict(os.environ, {"DATABASE_URL": database_url}):
        yield get_fast_api_client()

    from open_webui.internal.db import SQLALCHEMY_DATABASE_URL
    assert SQLALCHEMY_DATABASE_URL == database_url

    docker_client.containers.get(container_name).remove(force=True)
        

@pytest.fixture
def postgres_client(postgres_container):
    from open_webui.internal.db import Session
    from sqlalchemy import text

    tables = [
        "auth",
        "chat",
        "chatidtag",
        "document",
        "memory",
        "model",
        "prompt",
        "tag",
        '"user"',
    ]
    for table in tables:
        Session.execute(text(f"TRUNCATE TABLE {table}"))

    Session.commit()

    yield postgres_container
    