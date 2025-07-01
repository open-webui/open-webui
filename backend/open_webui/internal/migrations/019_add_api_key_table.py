"""Peewee migrations -- 019_add_api_key_table.py

"""

from contextlib import suppress
import peewee as pw
from peewee_migrate import Migrator
import uuid
import time

with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""

    @migrator.create_model
    class ApiKey(pw.Model):
        id = pw.TextField(primary_key=True)
        user_id = pw.TextField(null=False)
        api_key = pw.TextField(null=False, unique=True)
        name = pw.TextField(null=True)
        created_at = pw.BigIntegerField(null=False)
        updated_at = pw.BigIntegerField(null=False)
        last_used_at = pw.BigIntegerField(null=True)

        class Meta:
            table_name = "api_key"

    # Migrate existing data
    User = migrator.orm['user']
    users_with_keys = User.select().where(User.api_key.is_null(False))
    
    current_time = int(time.time())

    for user in users_with_keys:
        if hasattr(user, 'api_key') and user.api_key:
            ApiKey.create(
                id=str(uuid.uuid4()),
                user_id=user.id,
                api_key=user.api_key,
                name="Legacy API Key",
                created_at=current_time,
                updated_at=current_time,
            )


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""
    
    # Migrate data back
    User = migrator.orm['user']
    ApiKey = migrator.orm['api_key']
    
    # Get the first API key for each user
    api_keys = ApiKey.select(
        ApiKey.user_id, ApiKey.api_key
    ).distinct(ApiKey.user_id)

    for key_row in api_keys:
        User.update(api_key=key_row.api_key).where(User.id == key_row.user_id).execute()

    migrator.remove_model("api_key") 