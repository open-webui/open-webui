"""Merge migration heads after upstream v0.9.5 sync

Revision ID: f7e8d9c0b1a2
Revises: e1f2a3b4c5d6, a0b1c2d3e4f5
Create Date: 2026-05-11 06:30:00.000000

After merging upstream v0.9.5, we have two heads:
1. e1f2a3b4c5d6 - our prior merge-all-heads migration
2. a0b1c2d3e4f5 - the new tail of the upstream chain (add_memory_user_id_index)

This is a no-op merge migration to unify them into a single head.
"""

from typing import Sequence, Union


revision: str = "f7e8d9c0b1a2"
down_revision: Union[str, None] = ("e1f2a3b4c5d6", "a0b1c2d3e4f5")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
