"""Peewee migrations -- 019_add_providers_table.py.

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
import time
import json

import peewee as pw
from peewee_migrate import Migrator


with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""

    @migrator.create_model
    class Provider(pw.Model):
        id = pw.TextField(primary_key=True)
        name = pw.TextField()
        logo_light_url = pw.TextField(null=True)
        logo_dark_url = pw.TextField(null=True)
        logo_url = pw.TextField(null=True)
        model_id_patterns = pw.TextField()  # JSON stored as text
        model_patterns = pw.TextField(null=True)  # JSON: Model-specific logo overrides
        priority = pw.IntegerField(default=0)
        is_active = pw.BooleanField(default=True)
        created_at = pw.BigIntegerField()
        updated_at = pw.BigIntegerField()

        class Meta:
            table_name = "provider"

    # Seed default providers
    now = int(time.time())

    providers = [
        {
            'id': 'openai',
            'name': 'OpenAI',
            'logo_light_url': '/providers/openai-light.svg',
            'logo_dark_url': '/providers/openai-dark.svg',
            'logo_url': '/providers/openai-light.svg',
            'model_id_patterns': json.dumps(["^gpt-", "^o1-", "^text-davinci", "^text-curie", "^text-babbage"]),
            'priority': 100,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': 'anthropic',
            'name': 'Anthropic',
            'logo_light_url': '/providers/anthropic-light.svg',
            'logo_dark_url': '/providers/anthropic-dark.svg',
            'logo_url': '/providers/anthropic-light.svg',
            'model_id_patterns': json.dumps(["^claude-"]),
            'model_patterns': json.dumps([{
                'name': 'claude',
                'patterns': ['^claude-3', '^claude-instant'],
                'logo_url': '/providers/models/claude-light.svg',
                'logo_light_url': '/providers/models/claude-light.svg',
                'logo_dark_url': '/providers/models/claude-dark.svg',
            }]),
            'priority': 100,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': 'google',
            'name': 'Google',
            'logo_light_url': '/providers/google-light.svg',
            'logo_dark_url': '/providers/google-dark.svg',
            'logo_url': '/providers/google-light.svg',
            'model_id_patterns': json.dumps(["^gemini-", "^gemini:", "^palm-", "^gemma:", "^gemma[0-9]"]),
            'model_patterns': json.dumps([{
                'name': 'gemini',
                'patterns': ['^gemini-', '^gemini:'],
                'logo_url': '/providers/models/gemini-light.svg',
                'logo_light_url': '/providers/models/gemini-light.svg',
                'logo_dark_url': '/providers/models/gemini-dark.svg',
            }]),
            'priority': 100,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': 'meta',
            'name': 'Meta',
            'logo_light_url': '/providers/meta-light.svg',
            'logo_dark_url': '/providers/meta-dark.svg',
            'logo_url': '/providers/meta-light.svg',
            'model_id_patterns': json.dumps(["^llama[0-9]", "^llama-", "^llama2", "^llama3", "^codellama"]),
            'priority': 90,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': 'ollama',
            'name': 'Ollama',
            'logo_light_url': '/providers/ollama-light.svg',
            'logo_dark_url': '/providers/ollama-dark.svg',
            'logo_url': '/providers/ollama-light.svg',
            'model_id_patterns': json.dumps([]),
            'priority': 10,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
    ]

    # Insert providers using Peewee ORM (database-agnostic)
    def seed_providers():
        """Seed default provider data."""
        Provider = migrator.orm['provider']
        for provider_data in providers:
            Provider.create(**provider_data)

    migrator.run(seed_providers)


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    migrator.remove_model("provider")
