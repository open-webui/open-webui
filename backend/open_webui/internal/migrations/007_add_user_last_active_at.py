"""Peewee migrations -- 002_add_local_sharing.py.

Some examples (model - class or model name)::

    > Model = migrator.orm['table_name']            # Return model in current state by name
    > Model = migrator.ModelClass                   # Return model in current state by name

    > migrator.sql(sql)                             # Run custom SQL
    > migrator.run(func, *args, **kwargs)           # Run python function with the given args
    > migrator.create_model(Model)                  # Create a model (could be used as decorator)
    > migrator.remove_model(model, cascade=True)    # Remove a model
    > migrator.add_fields(model, **fields)          # Add fields to a model
    > migrator.change_fields(model, **fields)       # Change fields
    > migrator.remove_fields(model, *field_names, cascade=True)
    > migrator.rename_field(model, old_field_name, new_field_name)
    > migrator.rename_table(model, new_table_name)
    > migrator.add_index(model, *col_names, unique=False)
    > migrator.add_not_null(model, *field_names)
    > migrator.add_default(model, field_name, default)
    > migrator.add_constraint(model, name, sql)
    > migrator.drop_index(model, *col_names)
    > migrator.drop_not_null(model, *field_names)
    > migrator.drop_constraints(model, *constraints)

"""

from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator


with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""

    # Adding fields created_at and updated_at to the 'user' table
    def add_columns_if_missing(db):
        cols = {c.name for c in db.get_columns("user")}
        to_add = {}
        if "created_at" not in cols:
            to_add["created_at"] = pw.BigIntegerField(null=True)
        if "updated_at" not in cols:
            to_add["updated_at"] = pw.BigIntegerField(null=True)
        if "last_active_at" not in cols:
            to_add["last_active_at"] = pw.BigIntegerField(null=True)

        if to_add:
            db.execute_sql(
                "ALTER TABLE `user` "
                + ", ".join(
                    f"ADD COLUMN `{name}` BIGINT NULL" for name in to_add.keys()
                )
            )

    migrator.run(add_columns_if_missing, database)

    def backfill_user_timestamps(db):
        class UserWithTimestamps(pw.Model):
            timestamp = pw.BigIntegerField(null=True)
            created_at = pw.BigIntegerField(null=True)
            updated_at = pw.BigIntegerField(null=True)
            last_active_at = pw.BigIntegerField(null=True)

            class Meta:
                table_name = "user"

        UserWithTimestamps._meta.database = db

        cols = {c.name for c in db.get_columns("user")}
        timestamp_exists = "timestamp" in cols

        timestamp_field = (
            UserWithTimestamps.timestamp if timestamp_exists else pw.Value(0)
        )

        query = UserWithTimestamps.update(
            created_at=timestamp_field,
            updated_at=timestamp_field,
            last_active_at=timestamp_field,
        )

        if timestamp_exists:
            query = query.where(UserWithTimestamps.timestamp.is_null(False))

        query.execute()

    # Queue the data migration so it runs after the schema changes above.
    migrator.run(backfill_user_timestamps, database)

    # Now that the data has been copied, remove the original 'timestamp' field
    def drop_timestamp(db):
        cols = {c.name for c in db.get_columns("user")}
        if "timestamp" in cols:
            db.execute_sql("ALTER TABLE `user` DROP COLUMN `timestamp`")

    migrator.run(drop_timestamp, database)

    # Update the fields to be not null now that they are populated
    def enforce_not_null(db):
        db.execute_sql("ALTER TABLE `user` MODIFY COLUMN `created_at` BIGINT NOT NULL")
        db.execute_sql("ALTER TABLE `user` MODIFY COLUMN `updated_at` BIGINT NOT NULL")
        db.execute_sql(
            "ALTER TABLE `user` MODIFY COLUMN `last_active_at` BIGINT NOT NULL"
        )

    migrator.run(enforce_not_null, database)


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    # Recreate the timestamp field initially allowing null values for safe transition
    migrator.add_fields("user", timestamp=pw.BigIntegerField(null=True))

    def restore_timestamp(db):
        class UserWithTimestamps(pw.Model):
            timestamp = pw.BigIntegerField(null=True)
            created_at = pw.BigIntegerField(null=True)

            class Meta:
                table_name = "user"

        UserWithTimestamps._meta.database = db
        UserWithTimestamps.update(
            timestamp=UserWithTimestamps.created_at
        ).execute()

    migrator.run(restore_timestamp, database)

    # Remove the created_at and updated_at fields
    def drop_new_columns(db):
        cols = {c.name for c in db.get_columns("user")}
        for col in ("created_at", "updated_at", "last_active_at"):
            if col in cols:
                db.execute_sql(f"ALTER TABLE `user` DROP COLUMN `{col}`")

    migrator.run(drop_new_columns, database)

    # Finally, alter the timestamp field to not allow nulls if that was the original setting
    def enforce_timestamp_not_null(db):
        db.execute_sql("ALTER TABLE `user` MODIFY COLUMN `timestamp` BIGINT NOT NULL")

    migrator.run(enforce_timestamp_not_null, database)
