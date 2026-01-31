"""Peewee migrations -- 009_add_models.py.

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


def _col(database, table: str, col: str) -> bool:
    try:
        if isinstance(database, pw.SqliteDatabase):
            c = database.execute_sql(f'PRAGMA table_info("{table}")')
            return any(r[1] == col for r in c.fetchall())
        c = database.execute_sql(
            "SELECT 1 FROM information_schema.columns WHERE table_name=%s AND column_name=%s",
            (table, col),
        )
        return c.fetchone() is not None
    except Exception:
        return False


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""

    if not _col(database, "tool", "valves"):
        try:
            migrator.add_fields("tool", valves=pw.TextField(null=True))
        except Exception as e:
            if (
                "duplicate column" not in str(e).lower()
                and "already exists" not in str(e).lower()
            ):
                raise
    if not _col(database, "function", "valves"):
        try:
            migrator.add_fields("function", valves=pw.TextField(null=True))
        except Exception as e:
            if (
                "duplicate column" not in str(e).lower()
                and "already exists" not in str(e).lower()
            ):
                raise
    if not _col(database, "function", "is_active"):
        try:
            migrator.add_fields("function", is_active=pw.BooleanField(default=False))
        except Exception as e:
            if (
                "duplicate column" not in str(e).lower()
                and "already exists" not in str(e).lower()
            ):
                raise


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    migrator.remove_fields("tool", "valves")
    migrator.remove_fields("function", "valves")
    migrator.remove_fields("function", "is_active")
