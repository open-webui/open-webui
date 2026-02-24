"""Peewee migrations -- 001_initial_schema.py.

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

    # We perform different migrations for SQLite and other databases
    # This is because SQLite is very loose with enforcing its schema, and trying to migrate other databases like SQLite
    # will require per-database SQL queries.
    # Instead, we assume that because external DB support was added at a later date, it is safe to assume a newer base
    # schema instead of trying to migrate from an older schema.
    if isinstance(database, pw.SqliteDatabase):
        migrate_sqlite(migrator, database, fake=fake)
    else:
        migrate_external(migrator, database, fake=fake)


def migrate_sqlite(migrator: Migrator, database: pw.Database, *, fake=False):
    @migrator.create_model
    class Auth(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        email = pw.CharField(max_length=255)
        password = pw.CharField(max_length=255)
        active = pw.BooleanField()

        class Meta:
            table_name = "auth"

    @migrator.create_model
    class Chat(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        user_id = pw.CharField(max_length=255)
        title = pw.CharField()
        chat = pw.TextField()
        timestamp = pw.BigIntegerField()

        class Meta:
            table_name = "chat"

    @migrator.create_model
    class ChatIdTag(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        tag_name = pw.CharField(max_length=255)
        chat_id = pw.CharField(max_length=255)
        user_id = pw.CharField(max_length=255)
        timestamp = pw.BigIntegerField()

        class Meta:
            table_name = "chatidtag"

    @migrator.create_model
    class Document(pw.Model):
        id = pw.AutoField()
        collection_name = pw.CharField(max_length=255, unique=True)
        name = pw.CharField(max_length=255, unique=True)
        title = pw.CharField()
        filename = pw.CharField()
        content = pw.TextField(null=True)
        user_id = pw.CharField(max_length=255)
        timestamp = pw.BigIntegerField()

        class Meta:
            table_name = "document"

    @migrator.create_model
    class Modelfile(pw.Model):
        id = pw.AutoField()
        tag_name = pw.CharField(max_length=255, unique=True)
        user_id = pw.CharField(max_length=255)
        modelfile = pw.TextField()
        timestamp = pw.BigIntegerField()

        class Meta:
            table_name = "modelfile"

    @migrator.create_model
    class Prompt(pw.Model):
        id = pw.AutoField()
        command = pw.CharField(max_length=255, unique=True)
        user_id = pw.CharField(max_length=255)
        title = pw.CharField()
        content = pw.TextField()
        timestamp = pw.BigIntegerField()

        class Meta:
            table_name = "prompt"

    @migrator.create_model
    class Tag(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        name = pw.CharField(max_length=255)
        user_id = pw.CharField(max_length=255)
        data = pw.TextField(null=True)

        class Meta:
            table_name = "tag"

    @migrator.create_model
    class User(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        name = pw.CharField(max_length=255)
        email = pw.CharField(max_length=255)
        role = pw.CharField(max_length=255)
        profile_image_url = pw.CharField(max_length=255)
        timestamp = pw.BigIntegerField()

        class Meta:
            table_name = "user"


def migrate_external(migrator: Migrator, database: pw.Database, *, fake=False):
    @migrator.create_model
    class Auth(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        email = pw.CharField(max_length=255)
        password = pw.TextField()
        active = pw.BooleanField()

        class Meta:
            table_name = "auth"

    @migrator.create_model
    class Chat(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        user_id = pw.CharField(max_length=255)
        title = pw.TextField()
        chat = pw.TextField()
        timestamp = pw.BigIntegerField()

        class Meta:
            table_name = "chat"

    @migrator.create_model
    class ChatIdTag(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        tag_name = pw.CharField(max_length=255)
        chat_id = pw.CharField(max_length=255)
        user_id = pw.CharField(max_length=255)
        timestamp = pw.BigIntegerField()

        class Meta:
            table_name = "chatidtag"

    @migrator.create_model
    class Document(pw.Model):
        id = pw.AutoField()
        collection_name = pw.CharField(max_length=255, unique=True)
        name = pw.CharField(max_length=255, unique=True)
        title = pw.TextField()
        filename = pw.TextField()
        content = pw.TextField(null=True)
        user_id = pw.CharField(max_length=255)
        timestamp = pw.BigIntegerField()

        class Meta:
            table_name = "document"

    @migrator.create_model
    class Modelfile(pw.Model):
        id = pw.AutoField()
        tag_name = pw.CharField(max_length=255, unique=True)
        user_id = pw.CharField(max_length=255)
        modelfile = pw.TextField()
        timestamp = pw.BigIntegerField()

        class Meta:
            table_name = "modelfile"

    @migrator.create_model
    class Prompt(pw.Model):
        id = pw.AutoField()
        command = pw.CharField(max_length=255, unique=True)
        user_id = pw.CharField(max_length=255)
        title = pw.TextField()
        content = pw.TextField()
        timestamp = pw.BigIntegerField()

        class Meta:
            table_name = "prompt"

    @migrator.create_model
    class Tag(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        name = pw.CharField(max_length=255)
        user_id = pw.CharField(max_length=255)
        data = pw.TextField(null=True)

        class Meta:
            table_name = "tag"

    @migrator.create_model
    class User(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        name = pw.CharField(max_length=255)
        email = pw.CharField(max_length=255)
        role = pw.CharField(max_length=255)
        profile_image_url = pw.TextField()
        timestamp = pw.BigIntegerField()

        class Meta:
            table_name = "user"


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    migrator.remove_model("user")

    migrator.remove_model("tag")

    migrator.remove_model("prompt")

    migrator.remove_model("modelfile")

    migrator.remove_model("document")

    migrator.remove_model("chatidtag")

    migrator.remove_model("chat")

    migrator.remove_model("auth")
