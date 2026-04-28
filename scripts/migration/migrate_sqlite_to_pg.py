"""
Copy data from the legacy SQLite database (webui.db) into a PostgreSQL
database whose schema has already been created by the application's own
migrations (alembic / peewee_migrate).

Cutover runbook (run on the deploy host):

  1. Stop the app container so SQLite is quiescent:
         cd /opt/hyu-math && sudo docker compose down

  2. Make sure /opt/hyu-math/.env points DATABASE_URL at the new PG instance.

  3. Bring the container up once so alembic creates the schema in PG (no data
     yet), then bring it back down:
         sudo docker compose up -d
         # wait for HTTP 200 on http://localhost:8080/health, then:
         sudo docker compose down

  4. Run this script with both URLs in env. It opens the SQLite file directly
     and copies row-by-row into PG, in FK-respecting order, then resets
     PG sequences so subsequent inserts don't collide:

         SQLITE_PATH=/home/shared/hyu-math/backend/open_webui/data/webui.db \\
         DATABASE_URL=postgresql://hyumath_admin:...@pg-...:5432/hyumath \\
             python3 scripts/migration/migrate_sqlite_to_pg.py

  5. Bring the app back up. It now reads from PG with the migrated data:
         sudo docker compose up -d

The script is destructive on the destination: it TRUNCATEs each target table
before copying, so it can be re-run safely while you iterate. It only touches
tables that exist on BOTH sides; new app tables (added after migration) are
left for alembic.
"""

import os
import sys
from sqlalchemy import create_engine, MetaData, inspect, text


def main() -> int:
    sqlite_path = os.environ.get("SQLITE_PATH")
    dst_url = os.environ.get("DATABASE_URL")
    if not sqlite_path or not dst_url:
        print("ERROR: set SQLITE_PATH and DATABASE_URL", file=sys.stderr)
        return 1
    if not dst_url.startswith(("postgresql://", "postgresql+psycopg2://")):
        print(f"ERROR: DATABASE_URL must be PostgreSQL, got: {dst_url}", file=sys.stderr)
        return 1

    src = create_engine(f"sqlite:///{sqlite_path}")
    dst = create_engine(dst_url)

    src_meta = MetaData()
    src_meta.reflect(bind=src)

    dst_tables = set(inspect(dst).get_table_names())
    print(f"src tables: {len(src_meta.tables)}, dst tables: {len(dst_tables)}")

    skipped, copied = [], []
    with src.connect() as src_conn, dst.begin() as dst_conn:
        # Disable FK checks for the duration of the load (PG: defer constraints).
        dst_conn.execute(text("SET session_replication_role = 'replica'"))

        # Truncate destination first so re-runs are idempotent.
        present = [t for t in src_meta.sorted_tables if t.name in dst_tables]
        if present:
            names = ", ".join(f'"{t.name}"' for t in present)
            dst_conn.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))

        for table in present:
            rows = src_conn.execute(table.select()).mappings().all()
            if not rows:
                copied.append((table.name, 0))
                continue
            dst_conn.execute(table.insert(), [dict(r) for r in rows])
            copied.append((table.name, len(rows)))

        for table in src_meta.sorted_tables:
            if table.name not in dst_tables:
                skipped.append(table.name)

        # Re-sync PG sequences so subsequent INSERTs pick up where we left off.
        for table in present:
            for col in table.primary_key.columns:
                if col.autoincrement is False:
                    continue
                dst_conn.execute(
                    text(
                        "SELECT setval(pg_get_serial_sequence(:t, :c), "
                        "COALESCE((SELECT MAX(\"" + col.name + "\") FROM \"" + table.name + "\"), 1))"
                    ),
                    {"t": table.name, "c": col.name},
                )

        dst_conn.execute(text("SET session_replication_role = 'origin'"))

    for name, n in copied:
        print(f"  {name:30} {n:>8} rows")
    if skipped:
        print(f"\nskipped (not present in destination): {skipped}")
    print(f"\nDone. {len(copied)} tables copied, {len(skipped)} skipped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
