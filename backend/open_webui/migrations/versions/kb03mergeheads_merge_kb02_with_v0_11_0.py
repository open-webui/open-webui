"""merge kb02mergeheads with upstream v0.11.0 head

Topology-only merge revision. After syncing upstream v0.11.0, the migration
graph forked at 42e2978c7933 (the v0.10.2 head) into two heads:
  - fork's kb02mergeheads (which itself joins kb01embedstatus + 42e2978c7933)
  - upstream's v0.11.0 chain 42e2978c7933 -> 856c5b02fb54 -> 9a1b2c3d4e5f ->
    c49178636c78 -> b0018471bbbe -> 55f1302ac17c -> 959eaac8f909 ->
    f0bd01a18a3d (add_unique_normalized_user_email_index)

This join produces a single head so `alembic upgrade head` resolves cleanly.
It performs no schema changes of its own: the two branches touch disjoint
schema (fork only adds `status`/`error` columns to `knowledge_file`;
upstream's v0.11.0 chain adds chat_message_meta, current_message_id on chat,
chat_variables, user_variables, memory covering index, automation folder_id,
and a unique normalized-user-email index), so merge order is safe.

Revision ID: kb03mergeheads
Revises: kb02mergeheads, f0bd01a18a3d
Create Date: 2026-08-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'kb03mergeheads'
down_revision: Union[str, None] = ('kb02mergeheads', 'f0bd01a18a3d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
