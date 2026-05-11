"""Alembic migration utilities."""

from alembic import op
from sqlalchemy import inspect as sa_inspect


def get_existing_tables() -> set[str]:
    """Return the set of table names already present in the database."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    return set(inspector.get_table_names())


def get_revision_id() -> str:
    """Generate a short random revision identifier."""
    import uuid

    return uuid.uuid4().hex[:12]
