"""Peewee migrations -- 019_add_rag_config_to_knowledge.py.
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
"""Add rag_config field to knowledge table if not present."""
from contextlib import suppress
from peewee_migrate import Migrator
import peewee as pw
import json

# Try importing JSONField from playhouse.postgres_ext
with suppress(ImportError):
    from playhouse.postgres_ext import JSONField as PostgresJSONField


# Fallback JSONField for SQLite (stores JSON as text)
class SQLiteJSONField(pw.TextField):
    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        if value is not None:
            return json.loads(value)
        return None


def get_compatible_json_field(database: pw.Database):
    """Return a JSON-compatible field for the current database."""
    if isinstance(database, pw.SqliteDatabase):
        return SQLiteJSONField(null=False, default={"DEFAULT_RAG_SETTINGS": True})
    else:
        return PostgresJSONField(null=False, default={"DEFAULT_RAG_SETTINGS": True})


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Add rag_config JSON field to knowledge table"""
    if 'knowledge' not in database.get_tables():
        print("Knowledge table hasn't been created yet, skipping migration.")
        return

    class Knowledge(pw.Model):
        class Meta:
            table_name = 'knowledge'

    Knowledge._meta.database = database  # bind DB

    migrator.add_fields(
        Knowledge,
        rag_config=get_compatible_json_field(database)
    )


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Remove rag_config field from knowledge table."""
    if 'knowledge' not in database.get_tables():
        print("Knowledge table hasn't been created yet, skipping migration.")
        return

    class Knowledge(pw.Model):
        class Meta:
            table_name = 'knowledge'

    Knowledge._meta.database = database
    migrator.remove_fields(Knowledge, 'rag_config')
