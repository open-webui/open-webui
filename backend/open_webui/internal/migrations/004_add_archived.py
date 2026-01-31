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

    column_exists = False
    try:
        if isinstance(database, pw.SqliteDatabase):
            cursor = database.execute_sql("PRAGMA table_info(chat)")
            columns = [row[1] for row in cursor.fetchall()]
            column_exists = "archived" in columns
        else:
            cursor = database.execute_sql(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'chat' AND column_name = 'archived'"
            )
            column_exists = cursor.fetchone() is not None
    except Exception:
        column_exists = False

    if not column_exists:
        try:
            migrator.add_fields("chat", archived=pw.BooleanField(default=False))
        except Exception as e:
            error_msg = str(e).lower()
            if (
                "duplicate column" not in error_msg
                and "already exists" not in error_msg
            ):
                raise


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    migrator.remove_fields("chat", "archived")
