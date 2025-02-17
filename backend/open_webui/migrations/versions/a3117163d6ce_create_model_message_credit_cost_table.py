"""Create model_message_credit_cost table

Revision ID: a3117163d6ce
Revises: 804d2918bcd7
Create Date: 2025-02-17 17:46:17.063293

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'a3117163d6ce'
down_revision: Union[str, None] = '804d2918bcd7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the table
    op.create_table(
        'model_message_credit_cost',
        sa.Column('model_name', sa.String(length=255), nullable=False),
        sa.Column('message_credit_cost', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('model_name')
    )

    # Insert initial values
    op.bulk_insert(
        sa.table(
            'model_message_credit_cost',
            sa.column('model_name', sa.String),
            sa.column('message_credit_cost', sa.Integer)
        ),
        [
            {'model_name': 'GPT 4o', 'message_credit_cost': 20},
            {'model_name': 'GPT 4o Mini', 'message_credit_cost': 1},
            {'model_name': 'Claude 3 Haiku', 'message_credit_cost': 2},
            {'model_name': 'Claude 3.5 Sonnet', 'message_credit_cost': 25},
            {'model_name': 'Gemini 1.5 Pro', 'message_credit_cost': 2},
            {'model_name': 'Perplexity', 'message_credit_cost': 25},
            {'model_name': 'GPT 3.5 Turbo', 'message_credit_cost': 25},
            {'model_name': 'Gemini 1.5 Flash', 'message_credit_cost': 25},
            {'model_name': 'Dall-E', 'message_credit_cost': 300},
        ]
    )


def downgrade() -> None:
    op.drop_table('model_message_credit_cost')
