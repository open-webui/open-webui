"""consolidated_chat_and_group_permissions

Revision ID: 79fba6b72c04
Revises: d31026856c01
Create Date: 2025-08-07 17:07:53.857718

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db
import json


# revision identifiers, used by Alembic.
revision: str = '79fba6b72c04'
down_revision: Union[str, None] = 'd31026856c01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    conn = op.get_bind()
    
    inspector = sa.inspect(conn)
    columns = inspector.get_columns("chat")
    if "share_id" not in [c["name"] for c in columns]:
        op.add_column("chat", sa.Column("share_id", sa.TEXT(), nullable=True))

    op.add_column('chat', sa.Column('views', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('chat', sa.Column('clones', sa.Integer(), nullable=False, server_default='0'))
    
    # Merged column additions
    op.add_column('chat', sa.Column('expires_at', sa.BigInteger(), nullable=True))
    op.add_column('chat', sa.Column('expire_on_views', sa.Integer(), nullable=True))

    with op.batch_alter_table('chat', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_public', sa.Boolean(), server_default=sa.text('0'), nullable=False))

    groups = conn.execute(sa.text("SELECT id, permissions FROM \"group\"")).fetchall()

    for group_id, permissions_str in groups:
        if permissions_str is None:
            permissions = {}
        else:
            permissions = json.loads(permissions_str)

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
    
    groups = conn.execute(sa.text("SELECT id, permissions FROM \"group\"")).fetchall()

    for group_id, permissions_str in groups:
        if permissions_str is not None:
            permissions = json.loads(permissions_str)
            if permissions and 'sharing' in permissions and 'shared_chats' in permissions['sharing']:
                del permissions['sharing']['shared_chats']
                conn.execute(
                    sa.text("UPDATE \"group\" SET permissions = :permissions WHERE id = :id"),
                    {'permissions': json.dumps(permissions), 'id': group_id}
                )

    with op.batch_alter_table('chat', schema=None) as batch_op:
        try:
            batch_op.drop_index('chat_share_id')
        except Exception as e:
            print(f"Warning: Could not drop index chat_share_id. It might not exist or another error occurred: {e}")
            pass

        # Merged column drops (in reverse order of upgrade additions)
        batch_op.drop_column('is_public')
        batch_op.drop_column('expire_on_views')
        batch_op.drop_column('expires_at')

        batch_op.drop_column('clones')
        batch_op.drop_column('views')
        batch_op.drop_column("share_id")