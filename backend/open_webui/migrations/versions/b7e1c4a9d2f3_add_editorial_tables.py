"""Add editorial tables (project, project_sheet versionada, document)

Revision ID: b7e1c4a9d2f3
Revises: 461111b60977
Create Date: 2026-06-19 12:00:00.000000

Funcionalidade editorial (Nidum) - Fatia 1: camada de dados.
- editorial_project: projeto/obra de um autor (user_id).
- editorial_project_sheet: ficha viva VERSIONADA. Indice unico PARCIAL garante,
  no banco, no maximo UMA linha is_current por projeto (ajuste pedido).
- editorial_document: registro de documento ingerido (parse vem na Fatia 2/3).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from open_webui.migrations.util import get_existing_tables

revision: str = 'b7e1c4a9d2f3'
down_revision: Union[str, None] = '461111b60977'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    if 'editorial_project' not in existing_tables:
        op.create_table(
            'editorial_project',
            sa.Column('id', sa.Text(), nullable=False, primary_key=True),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('name', sa.Text(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=True),
            sa.Column('updated_at', sa.BigInteger(), nullable=True),
        )
        op.create_index(
            'ix_editorial_project_user_id', 'editorial_project', ['user_id']
        )

    if 'editorial_project_sheet' not in existing_tables:
        op.create_table(
            'editorial_project_sheet',
            sa.Column('id', sa.Text(), nullable=False, primary_key=True),
            sa.Column('project_id', sa.Text(), nullable=False),
            sa.Column('version', sa.Integer(), nullable=False),
            sa.Column('is_current', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('data', sa.Text(), nullable=False),
            sa.Column('change_note', sa.Text(), nullable=True),
            sa.Column('created_by', sa.Text(), nullable=False),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.ForeignKeyConstraint(
                ['project_id'], ['editorial_project.id'], ondelete='CASCADE'
            ),
            sa.UniqueConstraint(
                'project_id', 'version', name='uq_sheet_project_version'
            ),
        )
        op.create_index(
            'ix_editorial_project_sheet_project_id',
            'editorial_project_sheet',
            ['project_id'],
        )
        # Ajuste #1: UMA so current por projeto, garantido NO BANCO.
        # Indice unico PARCIAL (so cobre linhas com is_current verdadeiro).
        op.create_index(
            'uq_sheet_one_current_per_project',
            'editorial_project_sheet',
            ['project_id'],
            unique=True,
            sqlite_where=sa.text('is_current = 1'),
            postgresql_where=sa.text('is_current = true'),
        )

    if 'editorial_document' not in existing_tables:
        op.create_table(
            'editorial_document',
            sa.Column('id', sa.Text(), nullable=False, primary_key=True),
            sa.Column('project_id', sa.Text(), nullable=False),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('file_id', sa.Text(), nullable=True),
            sa.Column('filename', sa.Text(), nullable=True),
            sa.Column('format', sa.Text(), nullable=True),
            sa.Column('status', sa.Text(), nullable=False, server_default='pending'),
            sa.Column('error', sa.Text(), nullable=True),
            sa.Column('meta', sa.Text(), nullable=True),
            sa.Column('tree_ref', sa.Text(), nullable=True),
            sa.Column('chunks_ref', sa.Text(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=True),
            sa.Column('updated_at', sa.BigInteger(), nullable=True),
            sa.ForeignKeyConstraint(
                ['project_id'], ['editorial_project.id'], ondelete='CASCADE'
            ),
        )
        op.create_index(
            'ix_editorial_document_project_id', 'editorial_document', ['project_id']
        )
        op.create_index(
            'ix_editorial_document_user_id', 'editorial_document', ['user_id']
        )


def downgrade() -> None:
    op.drop_table('editorial_document')
    op.drop_index(
        'uq_sheet_one_current_per_project', table_name='editorial_project_sheet'
    )
    op.drop_table('editorial_project_sheet')
    op.drop_table('editorial_project')
