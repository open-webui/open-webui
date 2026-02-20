"""Add tenant_oauth_config table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-02-19 20:00:00.000000

"""

import json
import time
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    insp = inspect(conn)
    return table_name in insp.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    insp = inspect(conn)
    columns = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # 1. Create the tenant_oauth_config table
    if not _table_exists("tenant_oauth_config"):
        op.create_table(
            "tenant_oauth_config",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True),
            sa.Column("domain", sa.Text(), nullable=False),
            sa.Column(
                "provider", sa.Text(), nullable=False, server_default="microsoft"
            ),
            sa.Column("client_id", sa.Text(), nullable=False),
            sa.Column("client_secret", sa.Text(), nullable=False),
            sa.Column("tenant_id", sa.Text(), nullable=False),
            sa.Column("redirect_uri", sa.Text(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
        op.create_index(
            "tenant_oauth_config_domain_idx",
            "tenant_oauth_config",
            ["domain"],
        )
        op.create_index(
            "tenant_oauth_config_provider_idx",
            "tenant_oauth_config",
            ["provider"],
        )
        op.create_index(
            "tenant_oauth_config_domain_provider_unique_idx",
            "tenant_oauth_config",
            ["domain", "provider"],
            unique=True,
        )

    # 2. Data migration: extract microsoft_* from branding presets into new table
    conn = op.get_bind()

    # Read the branding config from the config table
    result = conn.execute(sa.text("SELECT data FROM config WHERE id = 1")).fetchone()

    if result and result[0]:
        try:
            config_data = (
                json.loads(result[0]) if isinstance(result[0], str) else result[0]
            )
        except (json.JSONDecodeError, TypeError):
            config_data = {}

        branding = config_data.get("ui", {}).get("branding", {})
        presets = branding.get("presets", [])
        domain_mappings = branding.get("domain_mappings", [])

        # Build a reverse map: preset_name -> domain
        preset_to_domain = {}
        for mapping in domain_mappings:
            preset_name = mapping.get("preset_name", "")
            domain = mapping.get("domain", "")
            if preset_name and domain:
                preset_to_domain[preset_name] = domain

        now = int(time.time())
        modified = False

        for preset in presets:
            preset_name = preset.get("name", "")
            client_id = preset.get("microsoft_client_id", "")
            client_secret = preset.get("microsoft_client_secret", "")
            tenant_id = preset.get("microsoft_tenant_id", "")

            # Only migrate if credentials are actually set
            if not (client_id and client_secret and tenant_id):
                continue

            domain = preset_to_domain.get(preset_name, "")
            if not domain:
                continue

            # Check if row already exists (idempotent)
            existing = conn.execute(
                sa.text(
                    "SELECT id FROM tenant_oauth_config "
                    "WHERE domain = :domain AND provider = :provider"
                ),
                {"domain": domain, "provider": "microsoft"},
            ).fetchone()

            if not existing:
                conn.execute(
                    sa.text(
                        "INSERT INTO tenant_oauth_config "
                        "(id, domain, provider, client_id, client_secret, tenant_id, "
                        "redirect_uri, created_at, updated_at) "
                        "VALUES (:id, :domain, :provider, :client_id, :client_secret, "
                        ":tenant_id, :redirect_uri, :created_at, :updated_at)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "domain": domain,
                        "provider": "microsoft",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "tenant_id": tenant_id,
                        "redirect_uri": None,
                        "created_at": now,
                        "updated_at": now,
                    },
                )

            # Remove microsoft_* fields from the preset
            for key in [
                "microsoft_client_id",
                "microsoft_client_secret",
                "microsoft_tenant_id",
            ]:
                if key in preset:
                    del preset[key]
                    modified = True

        # Also clean presets that have microsoft_* fields but no credentials
        for preset in presets:
            for key in [
                "microsoft_client_id",
                "microsoft_client_secret",
                "microsoft_tenant_id",
            ]:
                if key in preset:
                    del preset[key]
                    modified = True

        # Write back the cleaned branding config
        if modified:
            config_data["ui"]["branding"] = branding
            conn.execute(
                sa.text("UPDATE config SET data = :data WHERE id = 1"),
                {"data": json.dumps(config_data)},
            )


def downgrade() -> None:
    op.drop_index(
        "tenant_oauth_config_domain_provider_unique_idx",
        table_name="tenant_oauth_config",
    )
    op.drop_index(
        "tenant_oauth_config_provider_idx",
        table_name="tenant_oauth_config",
    )
    op.drop_index(
        "tenant_oauth_config_domain_idx",
        table_name="tenant_oauth_config",
    )
    op.drop_table("tenant_oauth_config")
