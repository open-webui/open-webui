"""merge lazy history storage with current dev migrations

Revision ID: b8f1c2d3e4a5
Revises: 9c0e2f4a6b81, 1ce6ade7d93b
Create Date: 2026-08-01 00:00:00.000000

"""

from collections.abc import Sequence

revision: str = 'b8f1c2d3e4a5'
down_revision: tuple[str, str] = ('9c0e2f4a6b81', '1ce6ade7d93b')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
