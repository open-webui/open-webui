"""merge kb01embedstatus with upstream head

Topology-only merge revision. After syncing upstream main, the migration
graph forked at 461111b60977 into two heads:
  - upstream chain ... -> 42e2978c7933 (add_memory_path_and_meta)
  - fork's kb01embedstatus (add knowledge_file embedding status)

This join produces a single head so `alembic upgrade head` resolves. It
performs no schema changes of its own: both branches touch disjoint schema
(upstream reshapes the `config` table and adds memory columns; the fork only
adds `status`/`error` columns to `knowledge_file`), so merge order is safe.

Revision ID: kb02mergeheads
Revises: 42e2978c7933, kb01embedstatus
Create Date: 2026-07-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'kb02mergeheads'
down_revision: Union[str, None] = ('42e2978c7933', 'kb01embedstatus')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
