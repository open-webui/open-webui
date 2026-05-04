"""Peewee migrations -- 019_encrypt_user_valves.py.

Encrypts existing plaintext user valve data stored in user.settings JSON.

Some examples (model - class or model name)::

    > Model = migrator.orm['table_name']            # Return model in current state by name
    > Model = migrator.ModelClass                    # Return model in current state by name

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

import json
import logging

import peewee as pw
from peewee_migrate import Migrator

from open_webui.utils.valve_encryption import encrypt_user_valves

with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext

log = logging.getLogger(__name__)


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Encrypt existing plaintext user valves in user.settings."""
    User = migrator.orm["user"]

    for user in User.select().where(User.settings.is_null(False)).iterator():
        settings_raw = user.settings
        if not settings_raw:
            continue

        try:
            settings = (
                json.loads(settings_raw)
                if isinstance(settings_raw, str)
                else settings_raw
            )
        except (json.JSONDecodeError, TypeError):
            log.warning("Skipping user %s: malformed settings JSON", user.id)
            continue

        if not isinstance(settings, dict):
            log.warning("Skipping user %s: settings is not a dict", user.id)
            continue

        changed = False

        for category in ("tools", "functions"):
            valves = (
                settings.get(category, {}).get("valves", {})
                if isinstance(settings.get(category), dict)
                else {}
            )
            for valve_id, valve_data in valves.items():
                if isinstance(valve_data, dict) and valve_data:
                    settings[category]["valves"][valve_id] = encrypt_user_valves(
                        valve_data
                    )
                    changed = True

        if changed:
            User.update(settings=json.dumps(settings)).where(
                User.id == user.id
            ).execute()


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Decrypt user valves back to plaintext."""
    from open_webui.utils.valve_encryption import _fernet

    User = migrator.orm["user"]

    for user in User.select().where(User.settings.is_null(False)).iterator():
        settings_raw = user.settings
        if not settings_raw:
            continue

        try:
            settings = (
                json.loads(settings_raw)
                if isinstance(settings_raw, str)
                else settings_raw
            )
        except (json.JSONDecodeError, TypeError):
            log.warning("Rollback skipping user %s: malformed settings JSON", user.id)
            continue

        if not isinstance(settings, dict):
            log.warning("Rollback skipping user %s: settings is not a dict", user.id)
            continue

        changed = False

        for category in ("tools", "functions"):
            valves = (
                settings.get(category, {}).get("valves", {})
                if isinstance(settings.get(category), dict)
                else {}
            )
            for valve_id, valve_data in valves.items():
                if isinstance(valve_data, str):
                    try:
                        decrypted = json.loads(_fernet.decrypt(valve_data.encode()).decode())
                        if not isinstance(decrypted, dict):
                            raise ValueError(f"Expected dict, got {type(decrypted).__name__}")
                        settings[category]["valves"][valve_id] = decrypted
                        changed = True
                    except Exception:
                        log.warning(
                            "Rollback failed to decrypt valve %s/%s for user %s; skipping",
                            category, valve_id, user.id,
                        )

        if changed:
            User.update(settings=json.dumps(settings)).where(
                User.id == user.id
            ).execute()
