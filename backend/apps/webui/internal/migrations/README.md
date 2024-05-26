# Database Migrations

This directory contains all the database migrations for the web app.
Migrations are done using the [`peewee-migrate`](https://github.com/klen/peewee_migrate) library.

Migrations are automatically ran at app startup.

## Creating a migration

Have you made a change to the schema of an existing model?
You will need to create a migration file to ensure that existing databases are updated for backwards compatibility.

1. Have a database file (`webui.db`) that has the old schema prior to any of your changes.
2. Make your changes to the models.
3. From the `backend` directory, run the following command:
   ```bash
   pw_migrate create --auto --auto-source apps.webui.models --database sqlite:///${SQLITE_DB} --directory apps/web/internal/migrations ${MIGRATION_NAME}
   ```
   - `$SQLITE_DB` should be the path to the database file.
   - `$MIGRATION_NAME` should be a descriptive name for the migration.
4. The migration file will be created in the `apps/web/internal/migrations` directory.
