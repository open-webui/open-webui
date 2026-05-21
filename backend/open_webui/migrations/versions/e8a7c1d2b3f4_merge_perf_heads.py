"""Merge perf-pass heads

Reconciles the three sibling migrations created by Units 3, 4, and 6 of
the goated-perf-pass batch, which all share ``fa1c3b27e891`` as their
``down_revision``:

  * ``b1f1e9a4c7d2`` - file.user_id index (Unit 3)
  * ``bab38fc89261`` - chat columns and indexes (Unit 4)
  * ``c4d8e6f1a902`` - chat_message table (Unit 6)

This revision exists only so ``alembic upgrade head`` resolves to a single
revision. It has no schema effect of its own.

Revision ID: e8a7c1d2b3f4
Revises: b1f1e9a4c7d2, bab38fc89261, c4d8e6f1a902
Create Date: 2026-05-20 00:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "e8a7c1d2b3f4"
down_revision = ("b1f1e9a4c7d2", "bab38fc89261", "c4d8e6f1a902")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
