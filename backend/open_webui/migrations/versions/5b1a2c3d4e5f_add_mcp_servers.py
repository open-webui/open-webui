"""Add MCP servers table (minimal)

Revision ID: 5b1a2c3d4e5f
Revises: d31026856c01
Create Date: 2025-08-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from open_webui.internal.db import JSONField

# revision identifiers, used by Alembic.
revision = "5b1a2c3d4e5f"
down_revision = "d31026856c01"
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types
    mcp_connection_type_enum = sa.Enum("http_stream", name="mcpconnectiontype")
    mcp_server_status_enum = sa.Enum(
        "connected", "disconnected", "error", "connecting", name="mcpserverstatus"
    )

    # Create the table
    op.create_table(
        "mcp_server",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("connection_type", mcp_connection_type_enum, nullable=False),
        sa.Column("http_url", sa.String(), nullable=False),
        sa.Column("headers", JSONField, nullable=True),
        # OAuth columns
        sa.Column("oauth_config", sa.Text(), nullable=True),
        sa.Column("oauth_tokens", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.BigInteger(), nullable=True),
        sa.Column("status", mcp_server_status_enum, nullable=True),
        sa.Column("last_connected_at", sa.BigInteger(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("access_control", JSONField, nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes
    op.create_index(op.f("ix_mcp_server_user_id"), "mcp_server", ["user_id"], unique=False)
    op.create_index(op.f("ix_mcp_server_status"), "mcp_server", ["status"], unique=False)
    op.create_index(op.f("ix_mcp_server_is_active"), "mcp_server", ["is_active"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_mcp_server_is_active"), table_name="mcp_server")
    op.drop_index(op.f("ix_mcp_server_status"), table_name="mcp_server")
    op.drop_index(op.f("ix_mcp_server_user_id"), table_name="mcp_server")
    op.drop_table("mcp_server")
    sa.Enum(name="mcpserverstatus").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="mcpconnectiontype").drop(op.get_bind(), checkfirst=False)