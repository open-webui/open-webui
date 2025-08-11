# Open WebUI: PostgreSQL with AWS RDS IAM and SSL

Set the following environment variables to enable IAM token auth and pinned SSL CA for Aurora/RDS PostgreSQL:

- ENABLE_AWS_RDS_IAM=true
- AWS_REGION=us-east-1
- DATABASE_URL=postgresql://<db_user>@<db_host>:5432/<db_name>
- PG_SSLMODE=verify-full  # or require/verify-ca as needed
- PG_SSLROOTCERT=/app/certs/rds-combined-ca-bundle.pem  # path inside container, world-readable

Notes:
- When IAM is enabled, a token is generated at startup and injected as the password.
- Ensure the DB user has rds_iam role and the container has AWS credentials (EC2/ECS role or static env).
- The code avoids libpq default ~/.postgresql lookup, preventing permission errors like "/app/.postgresql/postgresql.crt".
- Alembic migrations, Peewee pre-migrations, and optional PGVector connections all use the same settings. 