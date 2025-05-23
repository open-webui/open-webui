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
from contextlib import suppress
import peewee as pw
from peewee_migrate import Migrator
import json
with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext

class Knowledge(pw.Model):
    class Meta:
        table_name = 'knowledge'

def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Add rag_config column to knowledge table."""
    Knowledge._meta.database = database  # manually bind DB

    migrator.add_fields(
        Knowledge,
        rag_config=pw.TextField(null=True, default=json.dumps({"DEFAULT_RAG_SETTINGS": True})),
    )


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Remove rag_config column from knowledge table."""
    Knowledge._meta.database = database  # manually bind DB

    migrator.remove_fields(Knowledge, "rag_config")
