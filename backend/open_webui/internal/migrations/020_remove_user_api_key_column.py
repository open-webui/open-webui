"""Peewee migrations -- 020_remove_user_api_key_column.py

"""

from contextlib import suppress
import peewee as pw
from peewee_migrate import Migrator

with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""
    migrator.remove_fields("user", "api_key")


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""
    migrator.add_fields(
        "user", api_key=pw.TextField(null=True, unique=True)
    ) 