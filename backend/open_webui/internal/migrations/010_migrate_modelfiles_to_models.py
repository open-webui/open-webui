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
import json

from open_webui.utils.misc import parse_ollama_modelfile

with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""

    # Fetch data from 'modelfile' table and insert into 'model' table
    migrate_modelfile_to_model(migrator, database)
    # Drop the 'modelfile' table
    migrator.remove_model("modelfile")


def migrate_modelfile_to_model(migrator: Migrator, database: pw.Database):
    ModelFile = migrator.orm["modelfile"]
    Model = migrator.orm["model"]

    modelfiles = ModelFile.select()

    for modelfile in modelfiles:
        # Extract and transform data in Python

        modelfile.modelfile = json.loads(modelfile.modelfile)
        meta = json.dumps(
            {
                "description": modelfile.modelfile.get("desc"),
                "profile_image_url": modelfile.modelfile.get("imageUrl"),
                "ollama": {"modelfile": modelfile.modelfile.get("content")},
                "suggestion_prompts": modelfile.modelfile.get("suggestionPrompts"),
                "categories": modelfile.modelfile.get("categories"),
                "user": {**modelfile.modelfile.get("user", {}), "community": True},
            }
        )

        info = parse_ollama_modelfile(modelfile.modelfile.get("content"))

        # Insert the processed data into the 'model' table
        Model.create(
            id=f"ollama-{modelfile.tag_name}",
            user_id=modelfile.user_id,
            base_model_id=info.get("base_model_id"),
            name=modelfile.modelfile.get("title"),
            meta=meta,
            params=json.dumps(info.get("params", {})),
            created_at=modelfile.timestamp,
            updated_at=modelfile.timestamp,
        )


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    recreate_modelfile_table(migrator, database)
    move_data_back_to_modelfile(migrator, database)
    migrator.remove_model("model")


def recreate_modelfile_table(migrator: Migrator, database: pw.Database):
    query = """
    CREATE TABLE IF NOT EXISTS modelfile (
        user_id TEXT,
        tag_name TEXT,
        modelfile JSON,
        timestamp BIGINT
    )
    """
    migrator.sql(query)


def move_data_back_to_modelfile(migrator: Migrator, database: pw.Database):
    Model = migrator.orm["model"]
    Modelfile = migrator.orm["modelfile"]

    models = Model.select()

    for model in models:
        # Extract and transform data in Python
        meta = json.loads(model.meta)

        modelfile_data = {
            "title": model.name,
            "desc": meta.get("description"),
            "imageUrl": meta.get("profile_image_url"),
            "content": meta.get("ollama", {}).get("modelfile"),
            "suggestionPrompts": meta.get("suggestion_prompts"),
            "categories": meta.get("categories"),
            "user": {k: v for k, v in meta.get("user", {}).items() if k != "community"},
        }

        # Insert the processed data back into the 'modelfile' table
        Modelfile.create(
            user_id=model.user_id,
            tag_name=model.id,
            modelfile=modelfile_data,
            timestamp=model.created_at,
        )
