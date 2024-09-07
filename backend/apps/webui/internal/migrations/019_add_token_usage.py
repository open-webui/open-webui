from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator


with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext
    

def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Add token_usage field to user table."""
    migrator.add_fields("user", token_usage=pw.BigIntegerField(default=0))

def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Remove token_usage field from user table."""
    migrator.remove_fields("user", "token_usage")
