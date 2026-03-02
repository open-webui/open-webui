"""Peewee migrations -- 006_migrate_timestamps_and_charfields.py.

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

    # Alter the tables with timestamps
    migrator.change_fields(
        "chatidtag",
        timestamp=pw.BigIntegerField(),
    )
    migrator.change_fields(
        "document",
        timestamp=pw.BigIntegerField(),
    )
    migrator.change_fields(
        "modelfile",
        timestamp=pw.BigIntegerField(),
    )
    migrator.change_fields(
        "prompt",
        timestamp=pw.BigIntegerField(),
    )
    migrator.change_fields(
        "user",
        timestamp=pw.BigIntegerField(),
    )
    # Alter the tables with varchar to text where necessary
    migrator.change_fields(
        "auth",
        password=pw.TextField(),
    )
    migrator.change_fields(
        "chat",
        title=pw.TextField(),
    )
    migrator.change_fields(
        "document",
        title=pw.TextField(),
        filename=pw.TextField(),
    )
    migrator.change_fields(
        "prompt",
        title=pw.TextField(),
    )
    migrator.change_fields(
        "user",
        profile_image_url=pw.TextField(),
    )


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    if isinstance(database, pw.SqliteDatabase):
        # Alter the tables with timestamps
        migrator.change_fields(
            "chatidtag",
            timestamp=pw.DateField(),
        )
        migrator.change_fields(
            "document",
            timestamp=pw.DateField(),
        )
        migrator.change_fields(
            "modelfile",
            timestamp=pw.DateField(),
        )
        migrator.change_fields(
            "prompt",
            timestamp=pw.DateField(),
        )
        migrator.change_fields(
            "user",
            timestamp=pw.DateField(),
        )
    migrator.change_fields(
        "auth",
        password=pw.CharField(max_length=255),
    )
    migrator.change_fields(
        "chat",
        title=pw.CharField(),
    )
    migrator.change_fields(
        "document",
        title=pw.CharField(),
        filename=pw.CharField(),
    )
    migrator.change_fields(
        "prompt",
        title=pw.CharField(),
    )
    migrator.change_fields(
        "user",
        profile_image_url=pw.CharField(),
    )
