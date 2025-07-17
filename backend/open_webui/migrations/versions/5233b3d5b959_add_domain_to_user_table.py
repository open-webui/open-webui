"""add domain to user table

Revision ID: 5233b3d5b959
Revises: 3781e22d8b01
Create Date: 2025-04-01 10:45:28.890543

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "5233b3d5b959"
down_revision = "3781e22d8b01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user", sa.Column("domain", sa.String(), nullable=True))
    conn = op.get_bind()
    if conn.dialect.name == "sqlite":
        users = conn.execute(
            sa.text("SELECT id, email FROM user WHERE domain IS NULL")
        ).fetchall()
        for user_id, email in users:
            domain = email.split("@")[1] if "@" in email else None
            conn.execute(
                sa.text("UPDATE user SET domain = :domain WHERE id = :id"),
                {"domain": domain, "id": user_id},
            )
    else:
        op.execute(
            """
            UPDATE "user" 
            SET domain = split_part(email, '@', 2)
            WHERE domain IS NULL
            """
        )


def downgrade() -> None:
    op.drop_column("user", "domain")
