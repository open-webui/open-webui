"""Add access_grant table

Revision ID: f1e2d3c4b5a6
Revises: 8452d01d26d7
Create Date: 2026-02-05 10:00:00.000000

Migrates from JSON access_control columns to normalized access_grant table.
Access control semantics:
- NULL: Public access (all users can read) -> insert user:* for read
- {}: Private/owner-only (no grants) -> insert nothing
- {read: {...}, write: {...}}: Custom permissions -> insert specific grants
"""

from typing import Sequence, Union
import time
import uuid

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

revision: str = "f1e2d3c4b5a6"
down_revision: Union[str, None] = "8452d01d26d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    # Create access_grant table
    if "access_grant" not in existing_tables:
        op.create_table(
            "access_grant",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True),
            sa.Column("resource_type", sa.Text(), nullable=False),
            sa.Column("resource_id", sa.Text(), nullable=False),
            sa.Column("principal_type", sa.Text(), nullable=False),
            sa.Column("principal_id", sa.Text(), nullable=False),
            sa.Column("permission", sa.Text(), nullable=False),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.UniqueConstraint(
                "resource_type",
                "resource_id",
                "principal_type",
                "principal_id",
                "permission",
                name="uq_access_grant_grant",
            ),
        )
        op.create_index(
            "idx_access_grant_resource",
            "access_grant",
            ["resource_type", "resource_id"],
        )
        op.create_index(
            "idx_access_grant_principal",
            "access_grant",
            ["principal_type", "principal_id"],
        )

    # Backfill existing access_control JSON data
    conn = op.get_bind()

    # Tables with access_control JSON columns: (table_name, resource_type)
    resource_tables = [
        ("knowledge", "knowledge"),
        ("prompt", "prompt"),
        ("tool", "tool"),
        ("model", "model"),
        ("note", "note"),
        ("channel", "channel"),
        ("file", "file"),
    ]

    now = int(time.time())
    inserted = set()

    for table_name, resource_type in resource_tables:
        if table_name not in existing_tables:
            continue

        # Query all rows
        try:
            result = conn.execute(
                sa.text(f'SELECT id, access_control FROM "{table_name}"')
            )
            rows = result.fetchall()
        except Exception:
            continue

        for row in rows:
            resource_id = row[0]
            access_control_json = row[1]

            # Handle NULL or JSON "null" = public access (user:* for read)
            # Could be Python None (SQL NULL) or string "null" (JSON null)
            # EXCEPTION: files with NULL are PRIVATE (owner-only), not public
            is_null = (
                access_control_json is None
                or access_control_json == "null"
                or (
                    isinstance(access_control_json, str)
                    and access_control_json.strip().lower() == "null"
                )
            )
            if is_null:
                # Files: NULL = private (no entry needed, owner has implicit access)
                # Other resources: NULL = public (insert user:* for read)
                if resource_type == "file":
                    continue  # Private - no entry needed

                key = (resource_type, resource_id, "user", "*", "read")
                if key not in inserted:
                    try:
                        conn.execute(
                            sa.text("""
                                INSERT INTO access_grant (id, resource_type, resource_id, principal_type, principal_id, permission, created_at)
                                VALUES (:id, :resource_type, :resource_id, :principal_type, :principal_id, :permission, :created_at)
                            """),
                            {
                                "id": str(uuid.uuid4()),
                                "resource_type": resource_type,
                                "resource_id": resource_id,
                                "principal_type": "user",
                                "principal_id": "*",
                                "permission": "read",
                                "created_at": now,
                            },
                        )
                        inserted.add(key)
                    except Exception:
                        pass
                continue

            # Handle JSON parsing
            if isinstance(access_control_json, str):
                import json

                try:
                    access_control_json = json.loads(access_control_json)
                except Exception:
                    continue

            # Handle {} = private/owner-only - NO entries needed
            # Owner access is implicit, no grants to store
            if not access_control_json or not isinstance(access_control_json, dict):
                continue

            # Check if it's effectively empty (no read/write keys with content)
            read_data = access_control_json.get("read", {})
            write_data = access_control_json.get("write", {})

            has_read_grants = read_data.get("group_ids", []) or read_data.get(
                "user_ids", []
            )
            has_write_grants = write_data.get("group_ids", []) or write_data.get(
                "user_ids", []
            )

            if not has_read_grants and not has_write_grants:
                # Empty permissions = private, no grants needed
                continue

            # Extract permissions and insert into access_grant table
            for permission in ["read", "write"]:
                perm_data = access_control_json.get(permission, {})
                if not perm_data:
                    continue

                for group_id in perm_data.get("group_ids", []):
                    key = (resource_type, resource_id, "group", group_id, permission)
                    if key in inserted:
                        continue
                    try:
                        conn.execute(
                            sa.text("""
                                INSERT INTO access_grant (id, resource_type, resource_id, principal_type, principal_id, permission, created_at)
                                VALUES (:id, :resource_type, :resource_id, :principal_type, :principal_id, :permission, :created_at)
                            """),
                            {
                                "id": str(uuid.uuid4()),
                                "resource_type": resource_type,
                                "resource_id": resource_id,
                                "principal_type": "group",
                                "principal_id": group_id,
                                "permission": permission,
                                "created_at": now,
                            },
                        )
                        inserted.add(key)
                    except Exception:
                        pass

                for user_id in perm_data.get("user_ids", []):
                    key = (resource_type, resource_id, "user", user_id, permission)
                    if key in inserted:
                        continue
                    try:
                        conn.execute(
                            sa.text("""
                                INSERT INTO access_grant (id, resource_type, resource_id, principal_type, principal_id, permission, created_at)
                                VALUES (:id, :resource_type, :resource_id, :principal_type, :principal_id, :permission, :created_at)
                            """),
                            {
                                "id": str(uuid.uuid4()),
                                "resource_type": resource_type,
                                "resource_id": resource_id,
                                "principal_type": "user",
                                "principal_id": user_id,
                                "permission": permission,
                                "created_at": now,
                            },
                        )
                        inserted.add(key)
                    except Exception:
                        pass

    # Drop access_control columns from resource tables
    for table_name, _ in resource_tables:
        if table_name not in existing_tables:
            continue
        try:
            with op.batch_alter_table(table_name) as batch:
                batch.drop_column("access_control")
        except Exception:
            pass


def downgrade() -> None:
    import json

    conn = op.get_bind()

    # Resource tables mapping: (table_name, resource_type)
    resource_tables = [
        ("knowledge", "knowledge"),
        ("prompt", "prompt"),
        ("tool", "tool"),
        ("model", "model"),
        ("note", "note"),
        ("channel", "channel"),
        ("file", "file"),
    ]

    # Step 1: Re-add access_control columns to resource tables
    for table_name, _ in resource_tables:
        try:
            with op.batch_alter_table(table_name) as batch:
                batch.add_column(sa.Column("access_control", sa.JSON(), nullable=True))
        except Exception:
            pass

    # Step 2: Query access_grant table and reconstruct JSON for each resource
    for table_name, resource_type in resource_tables:
        try:
            # Get all grants for this resource type
            result = conn.execute(
                sa.text("""
                    SELECT resource_id, principal_type, principal_id, permission
                    FROM access_grant
                    WHERE resource_type = :resource_type
                """),
                {"resource_type": resource_type},
            )
            rows = result.fetchall()
        except Exception:
            continue

        # Group by resource_id and reconstruct JSON structure
        resource_grants = {}
        for row in rows:
            resource_id = row[0]
            principal_type = row[1]
            principal_id = row[2]
            permission = row[3]

            if resource_id not in resource_grants:
                resource_grants[resource_id] = {
                    "is_public": False,
                    "read": {"group_ids": [], "user_ids": []},
                    "write": {"group_ids": [], "user_ids": []},
                }

            # Handle public access (user:* for read)
            if (
                principal_type == "user"
                and principal_id == "*"
                and permission == "read"
            ):
                resource_grants[resource_id]["is_public"] = True
                continue

            # Add to appropriate list
            if permission in ["read", "write"]:
                if principal_type == "group":
                    if (
                        principal_id
                        not in resource_grants[resource_id][permission]["group_ids"]
                    ):
                        resource_grants[resource_id][permission]["group_ids"].append(
                            principal_id
                        )
                elif principal_type == "user":
                    if (
                        principal_id
                        not in resource_grants[resource_id][permission]["user_ids"]
                    ):
                        resource_grants[resource_id][permission]["user_ids"].append(
                            principal_id
                        )

        # Step 3: Update each resource with reconstructed JSON
        for resource_id, grants in resource_grants.items():
            if grants["is_public"]:
                # Public = NULL
                access_control_value = None
            elif (
                not grants["read"]["group_ids"]
                and not grants["read"]["user_ids"]
                and not grants["write"]["group_ids"]
                and not grants["write"]["user_ids"]
            ):
                # No grants = should not happen (would mean no entries), default to {}
                access_control_value = json.dumps({})
            else:
                # Custom permissions
                access_control_value = json.dumps(
                    {
                        "read": grants["read"],
                        "write": grants["write"],
                    }
                )

            try:
                conn.execute(
                    sa.text(
                        f'UPDATE "{table_name}" SET access_control = :access_control WHERE id = :id'
                    ),
                    {"access_control": access_control_value, "id": resource_id},
                )
            except Exception:
                pass

        # Step 4: Set all resources WITHOUT entries to private
        # For files: NULL means private (owner-only), so leave as NULL
        # For other resources: {} means private, so update to {}
        if resource_type != "file":
            try:
                conn.execute(
                    sa.text(f"""
                        UPDATE "{table_name}" 
                        SET access_control = :private_value
                        WHERE id NOT IN (
                            SELECT DISTINCT resource_id FROM access_grant WHERE resource_type = :resource_type
                        )
                        AND access_control IS NULL
                    """),
                    {"private_value": json.dumps({}), "resource_type": resource_type},
                )
            except Exception:
                pass
        # For files, NULL stays NULL - no action needed

    # Step 5: Drop the access_grant table
    op.drop_index("idx_access_grant_principal", table_name="access_grant")
    op.drop_index("idx_access_grant_resource", table_name="access_grant")
    op.drop_table("access_grant")
