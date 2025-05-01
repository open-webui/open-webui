import logging
import os
from contextlib import contextmanager
from datetime import datetime, timedelta
import fcntl
from pathlib import Path
from typing import Iterator, Literal

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from open_webui.config import CACHE_DIR
from open_webui.env import DATABASE_URL, SRC_LOG_LEVELS
from open_webui.internal.db import get_db
from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT
from open_webui.storage.provider import Storage
from sqlalchemy import text

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DATA_CLEANUP"])

DATA_CLEANUP_ENABLED = os.getenv("DATA_CLEANUP_ENABLED", "false").lower() == "true"
if DATA_CLEANUP_ENABLED:
    if "DATA_CLEANUP_MAX_CHAT_AGE_DAYS" not in os.environ:
        raise ValueError(
            "If DATA_CLEANUP_ENABLED is set, DATA_CLEANUP_MAX_CHAT_AGE_DAYS must be set"
        )
    DATA_CLEANUP_MAX_CHAT_AGE_DAYS = float(os.environ["DATA_CLEANUP_MAX_CHAT_AGE_DAYS"])

    if "DATA_CLEANUP_MAX_CACHE_AGE_DAYS" not in os.environ:
        raise ValueError(
            "If DATA_CLEANUP_ENABLED is set, DATA_CLEANUP_MAX_CHAT_AGE_DAYS must be set"
        )
    DATA_CLEANUP_MAX_CACHE_AGE_DAYS = float(
        os.environ["DATA_CLEANUP_MAX_CACHE_AGE_DAYS"]
    )

    if "DATA_CLEANUP_CRON_SCHEDULE" not in os.environ:
        raise ValueError(
            "If DATA_CLEANUP_ENABLED is set, DATA_CLEANUP_CRON_SCHEDULE must be set"
        )
    DATA_CLEANUP_CRON_SCHEDULE = os.environ["DATA_CLEANUP_CRON_SCHEDULE"]

db_type: Literal["postgres", "sqlite"]
if DATABASE_URL.startswith("postgres"):
    db_type = "postgres"
elif DATABASE_URL.startswith("sqlite"):
    db_type = "sqlite"
else:
    raise ValueError(
        "Only postgres and sqlite are supported by OpenWebUI"
    )


async def setup_data_cleanup_schedule() -> None:
    """
    Sets up a cron job to run data cleanup policy with apscheduler.
    """
    assert DATA_CLEANUP_ENABLED

    log.info(
        f"Data cleanup policy enabled. "
        f"Chats older than {DATA_CLEANUP_MAX_CHAT_AGE_DAYS} days will be deleted. "
        f"Cache files older than {DATA_CLEANUP_MAX_CACHE_AGE_DAYS} days will be deleted. "
        f"Running on cron schedule '{DATA_CLEANUP_CRON_SCHEDULE}'"
    )
    scheduler = AsyncIOScheduler()
    # use sqlalchemy job store to sync across multiple instances
    scheduler.add_jobstore(
        SQLAlchemyJobStore(DATABASE_URL, tablename="data_cleanup_tasks")
    )
    # keep only the jobs defined in this function
    scheduler.remove_all_jobs()
    scheduler.start()
    scheduler.add_job(
        cleanup_data,
        CronTrigger.from_crontab(DATA_CLEANUP_CRON_SCHEDULE),
        id="data_cleanup_task",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )


def cleanup_data() -> None:
    """
    Cleans up old chats and files from the database and storage.
    """
    with try_acquire_db_lock("data_cleanup_task") as acquired:
        if acquired:
            now = datetime.now()
            log.info("Applying data cleanup policy")
            delete_chats_and_uploads(
                now - timedelta(days=DATA_CLEANUP_MAX_CHAT_AGE_DAYS)
            )
            delete_cache_files(now - timedelta(days=DATA_CLEANUP_MAX_CACHE_AGE_DAYS))


@contextmanager
def try_acquire_db_lock(id: str) -> Iterator[bool]:
    """
    Context manager which attempts to acquire a db lock with the given id.
    Yields a boolean indicating whether the lock was acquired, or False if it was already held.

    Needed to prevent multiple instances of the data cleanup task from running at the same time when horizontally scaling.
    This functionality is inbuilt in apscheduler v4.x, but it is still in alpha (after 3 years ;_;)
    """
    log.debug(f"Acquiring '{id}' db lock")
    lock_provider = (
        _try_acquire_db_lock_postgres(id)
        if DATABASE_URL.startswith("postgres")
        else _try_acquire_file_lock(id)
    )
    with lock_provider as acquired:
        if acquired:
            log.debug(f"Acquired '{id}' db lock")
        else:
            log.debug(f"'{id}' db lock already held by another process")

        yield acquired

        if acquired:
            log.debug(f"Releasing '{id}' db lock")
            # lock released on session close


@contextmanager
def _try_acquire_db_lock_postgres(id: str) -> Iterator[bool]:
    with get_db() as db:
        acquired = db.execute(
            text(f"SELECT pg_try_advisory_lock(hashtext('{id}'))")
        ).scalar_one()
        assert isinstance(acquired, bool)
        yield acquired


@contextmanager
def _try_acquire_file_lock(id: str) -> Iterator[bool]:
    # SQLite only supports single node, so we can use a file lock
    lock_path = f"/tmp/{id}.lock"
    with open(lock_path, "w") as lock_file:
        try:
            # Try to acquire the lock
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield True
        except BlockingIOError:
            yield False


def delete_chats_and_uploads(cutoff: datetime) -> None:

    chats_sql = f"select *, updated_at < {int(cutoff.timestamp())} as expired from chat"

    json_array_elements = "json_each" if db_type == "sqlite" else "json_array_elements"

    chat_file_jsons_sql = f"""
        with chats as ({chats_sql})
        select value, chats.expired as expired
        from chats, {json_array_elements}(chat -> 'files')
        -- only use 'status' = 'uploaded' files to prevent deleting knowledge base collections
        where value->>'status' = 'uploaded'
    """

    expired_files_sql = f"""
        with chat_file_jsons as ({chat_file_jsons_sql})
        select * from file
        join chat_file_jsons on file.id = chat_file_jsons.value->>'id'
        where chat_file_jsons.expired
    """

    with get_db() as db:
        
        expired_chat_file_paths = db.execute(text(f"""
            with expired_files as ({expired_files_sql})
            select path from expired_files
        """))

        for [path] in expired_chat_file_paths:
            log.debug(f"- Deleting file {path} from storage")
            # WARNING: this could fail without exception (but with printed note) if the file is not found in storage
            Storage.delete_file(path)

        # delete expired chat files from the db
        n_files_deleted = db.execute(text(f"""
            with expired_files as ({expired_files_sql})
            delete from file
            where id in (select id from expired_files)
        """)).rowcount # type: ignore
        assert isinstance(n_files_deleted, int)
        log.info(f"Deleted {n_files_deleted} file rows from the db")
        
        # delete the expired chat files from the db
        expired_collection_names = db.execute(text(f"""
            with chat_file_jsons as ({chat_file_jsons_sql})
            select distinct value->>'collection_name' from chat_file_jsons a
            where a.expired and not exists (
                select 1 from chat_file_jsons b
                where a.value->>'collection_name' = b.value->>'collection_name'
                and not b.expired
            )
        """))

        for [collection_name] in expired_collection_names:
            log.debug(f"- Deleting expired collection {collection_name} from vector db")
            VECTOR_DB_CLIENT.delete_collection(collection_name)

        # delete the expired chats from the db
        n_chats_deleted = db.execute(text(f"""
            with chats as ({chats_sql})
            delete from chat
            where id in (select id from chats where expired)
        """)).rowcount # type: ignore
        assert isinstance(n_chats_deleted, int)
        log.info(f"Deleted {n_chats_deleted} chat rows from the db")

        db.commit()


def delete_cache_files(cutoff: datetime) -> None:
    """
    Deletes files older than cutoff from /app/data/cache/[audio|image]/**
    """
    FOLDERS_TO_CLEAN = ["audio", "image"]

    cache_paths = [
        fp
        for folder in FOLDERS_TO_CLEAN
        for fp in Path(CACHE_DIR).glob(f"{folder}/**/*")
        if fp.is_file()
    ]
    log.info(f"Found {len(cache_paths)} total cache files in {CACHE_DIR}")
    log.debug(f"Cache files created before {cutoff} will be deleted")
    min_ctime = cutoff.timestamp()

    c = 0
    for fp in cache_paths:
        ctime = fp.stat().st_ctime
        log.debug(f"- {fp}: {ctime}")
        if ctime < min_ctime:
            fp.unlink()
            c += 1

    log.info(f"Deleted {c} cache files")
