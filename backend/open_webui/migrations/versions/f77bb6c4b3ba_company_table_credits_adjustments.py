"""Company table credits adjustments

Revision ID: f77bb6c4b3ba
Revises: 6bc9c6298daf
Create Date: 2025-05-14 13:15:53.482988

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'f77bb6c4b3ba'
down_revision: Union[str, None] = '6bc9c6298daf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Create a new temporary table with the updated schema
    op.create_table(
        'company_tmp',
        sa.Column('id', sa.String, primary_key=True, unique=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('profile_image_url', sa.Text, nullable=True),
        sa.Column('default_model', sa.String, nullable=True),
        sa.Column('allowed_models', sa.Text, nullable=True),
        sa.Column('credit_balance', sa.Float(), nullable=False),
        sa.Column('flex_credit_balance', sa.Float(), nullable=True),
        sa.Column('auto_recharge', sa.Boolean, default=False),
        sa.Column('credit_card_number', sa.String, nullable=True),
        sa.Column('size', sa.String, nullable=True),
        sa.Column('industry', sa.String, nullable=True),
        sa.Column('team_function', sa.String, nullable=True),
        sa.Column('stripe_customer_id', sa.String, nullable=True),
        sa.Column('budget_mail_80_sent', sa.Boolean, nullable=True),
        sa.Column('budget_mail_100_sent', sa.Boolean, nullable=True),
    )

    # Copy data from old table to new table
    op.execute("""
        INSERT INTO company_tmp (id, name, profile_image_url, default_model, allowed_models, 
                                credit_balance, flex_credit_balance, auto_recharge, credit_card_number,
                                size, industry, team_function, stripe_customer_id, 
                                budget_mail_80_sent, budget_mail_100_sent)
        SELECT id, name, profile_image_url, default_model, allowed_models, 
               credit_balance, flex_credit_balance, auto_recharge, credit_card_number,
               size, industry, team_function, stripe_customer_id,
               budget_mail_80_sent, budget_mail_100_sent
        FROM company;
    """)

    # Drop the old table
    op.drop_table('company')

    # Rename the new table to the original name
    op.rename_table('company_tmp', 'company')


def downgrade():
    # Reverse the process
    op.create_table(
        'company_tmp',
        sa.Column('id', sa.String, primary_key=True, unique=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('profile_image_url', sa.Text, nullable=True),
        sa.Column('default_model', sa.String, nullable=True),
        sa.Column('allowed_models', sa.Text, nullable=True),
        sa.Column('credit_balance', sa.Integer(), nullable=False),
        sa.Column('flex_credit_balance', sa.Integer(), nullable=True),
        sa.Column('auto_recharge', sa.Boolean, default=False),
        sa.Column('credit_card_number', sa.String, nullable=True),
        sa.Column('size', sa.String, nullable=True),
        sa.Column('industry', sa.String, nullable=True),
        sa.Column('team_function', sa.String, nullable=True),
        sa.Column('stripe_customer_id', sa.String, nullable=True),
        sa.Column('budget_mail_80_sent', sa.Boolean, nullable=True),
        sa.Column('budget_mail_100_sent', sa.Boolean, nullable=True),
    )

    op.execute("""
        INSERT INTO company_tmp (id, name, profile_image_url, default_model, allowed_models, 
                                credit_balance, flex_credit_balance, auto_recharge, credit_card_number,
                                size, industry, team_function, stripe_customer_id, 
                                budget_mail_80_sent, budget_mail_100_sent)
        SELECT id, name, profile_image_url, default_model, allowed_models, 
               CAST(credit_balance AS INTEGER), CAST(flex_credit_balance AS INTEGER), 
               auto_recharge, credit_card_number, size, industry, team_function, 
               stripe_customer_id, budget_mail_80_sent, budget_mail_100_sent
        FROM company;
    """)

    op.drop_table('company')
    op.rename_table('company_tmp', 'company')
