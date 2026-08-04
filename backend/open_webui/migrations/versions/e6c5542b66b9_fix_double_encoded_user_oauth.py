"""fix double-encoded user oauth

Revision b10670c03dd5 migrated the legacy `oauth_sub` column into the new
`oauth` JSON column by writing `json.dumps({...})` (a string) into a
column already typed `sa.JSON()`. SQLAlchemy's JSON type serializes
whatever Python value it's given, so the pre-serialized string was
serialized a second time, leaving affected rows with `oauth` holding a
JSON string (e.g. '{"oidc": {"sub": "..."}}') instead of a JSON object.
That breaks `UserModel.oauth: dict | None` validation on OAuth login for
any instance upgraded from a version that still had `oauth_sub`.

This migration re-parses any string-valued `oauth` cell back into its
underlying dict, fixing the double encoding in place. Rows that were
never double-encoded (already a dict, or null) are left untouched, so
this is idempotent and safe to run more than once.

Revision ID: e6c5542b66b9
Revises: 1ce6ade7d93b
Create Date: 2026-08-04 14:00:05.328172

"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e6c5542b66b9'
down_revision: str | None = '1ce6ade7d93b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_user = sa.table('user', sa.column('id', sa.Text), sa.column('oauth', sa.JSON))


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.select(_user.c.id, _user.c.oauth).where(_user.c.oauth.is_not(None))).fetchall()

    for uid, oauth in rows:
        if not isinstance(oauth, str):
            continue

        try:
            parsed = json.loads(oauth)
        except Exception:
            continue

        if isinstance(parsed, dict):
            conn.execute(sa.update(_user).where(_user.c.id == uid).values(oauth=parsed))


def downgrade() -> None:
    # Data repair only; nothing structural to revert.
    pass
