"""consolidated_chat_and_group_permissions

Revision ID: 79fba6b72c04
Revises: d31026856c01
Create Date: 2025-08-07 17:07:53.857718

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '79fba6b72c04'
down_revision: Union[str, None] = 'd31026856c01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    conn = op.get_bind()
    
    # from e1b3b3b3b3b3
    inspector = sa.inspect(conn)
    columns = inspector.get_columns("chat")
    if "share_id" not in [c["name"] for c in columns]:
        op.add_column("chat", sa.Column("share_id", sa.TEXT(), nullable=True))

    # from 9cc80bb2029f
    op.add_column('chat', sa.Column('views', sa.Integer(), nullable=False, server_default='0'))

    # from 5e8b7f9a8c6d
    op.add_column('chat', sa.Column('clones', sa.Integer(), nullable=False, server_default='0'))
    
    # from f1a2b3c4d5e6
    groups = conn.execute(sa.text("SELECT id, permissions FROM \"group\"")).fetchall()

    for group_id, permissions in groups:
        if permissions is None:
            permissions = {}

        if 'sharing' not in permissions:
            permissions['sharing'] = {}

        if 'shared_chats' not in permissions['sharing']:
            permissions['sharing']['shared_chats'] = False
            conn.execute(
                sa.text("UPDATE \"group\" SET permissions = :permissions WHERE id = :id"),
                {'permissions': json.dumps(permissions), 'id': group_id}
            )


def downgrade():
    conn = op.get_bind()
    
    # from f1a2b3c4d5e6
    groups = conn.execute(sa.text("SELECT id, permissions FROM \"group\"")).fetchall()

    for group_id, permissions in groups:
        if permissions and 'sharing' in permissions and 'shared_chats' in permissions['sharing']:
            del permissions['sharing']['shared_chats']
            conn.execute(
                sa.text("UPDATE \"group\" SET permissions = :permissions WHERE id = :id"),
                {'permissions': json.dumps(permissions), 'id': group_id}
            )

    # from 5e8b7f9a8c6d
    op.drop_column('chat', 'clones')

    # from 9cc80bb2029f
    op.drop_column('chat', 'views')

    # from e1b3b3b3b3b3
    op.drop_column("chat", "share_id")
