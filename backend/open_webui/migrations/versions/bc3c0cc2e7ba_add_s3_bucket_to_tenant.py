"""Add s3 bucket column to tenant

Revision ID: bc3c0cc2e7ba
Revises: 018012973d35
Create Date: 2025-12-01 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "bc3c0cc2e7ba"
down_revision = "f2c9b3e46a8e"
branch_labels = None
depends_on = None


def _generate_bucket_name(name: str) -> str:
    """Mirror application logic for generating default bucket names."""

    if name is None:
        return ""
    return name.replace("/", " ").replace(" ", "_").lower()


def upgrade():
    op.add_column(
        "tenant",
        sa.Column("s3_bucket", sa.String(length=255), nullable=True),
    )

    connection = op.get_bind()
    tenants = connection.execute(sa.text("SELECT id, name FROM tenant")).fetchall()
    for tenant in tenants:
        bucket_name = _generate_bucket_name(tenant.name)
        connection.execute(
            sa.text("UPDATE tenant SET s3_bucket = :bucket WHERE id = :id"),
            {"bucket": bucket_name, "id": tenant.id},
        )

    op.alter_column(
        "tenant",
        "s3_bucket",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.create_unique_constraint("uq_tenant_s3_bucket", "tenant", ["s3_bucket"])


def downgrade():
    op.drop_constraint("uq_tenant_s3_bucket", "tenant", type_="unique")
    op.drop_column("tenant", "s3_bucket")
