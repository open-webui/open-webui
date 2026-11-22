"""Rename the 'terminal' access grant type to 'machine' (Terminals became Machines).

Revision ID: c4e1a7d93b20
Revises: 9f6c2a8d1b43
"""

import sqlalchemy as sa
from alembic import op

revision = 'c4e1a7d93b20'
down_revision = '9f6c2a8d1b43'
branch_labels = None
depends_on = None


def _rename(old: str, new: str):
    # Drop rows the rename would duplicate, then move the rest.
    op.execute(
        sa.text(
            """
            DELETE FROM access_grant
            WHERE resource_type = :old
              AND EXISTS (
                SELECT 1 FROM access_grant AS other
                WHERE other.resource_type = :new
                  AND other.resource_id = access_grant.resource_id
                  AND other.principal_type = access_grant.principal_type
                  AND other.principal_id = access_grant.principal_id
                  AND other.permission = access_grant.permission
              )
            """
        ).bindparams(old=old, new=new)
    )
    op.execute(
        sa.text('UPDATE access_grant SET resource_type = :new WHERE resource_type = :old').bindparams(old=old, new=new)
    )


def upgrade():
    _rename('terminal', 'machine')


def downgrade():
    _rename('machine', 'terminal')
