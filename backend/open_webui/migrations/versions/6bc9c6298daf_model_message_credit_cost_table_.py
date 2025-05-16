"""Model message credit cost table adjustments

Revision ID: 6bc9c6298daf
Revises: 1e74585dcf49
Create Date: 2025-05-13 11:08:12.612189

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '6bc9c6298daf'
down_revision: Union[str, None] = '1e74585dcf49'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename the table
    op.rename_table('model_message_credit_cost', 'model_cost')
    
    # Remove message_credit_cost column
    op.drop_column('model_cost', 'message_credit_cost')
    
    # Add new columns
    op.add_column('model_cost', sa.Column('cost_per_million_input_tokens', sa.Float(), nullable=True))
    op.add_column('model_cost', sa.Column('cost_per_million_output_tokens', sa.Float(), nullable=True))
    op.add_column('model_cost', sa.Column('cost_per_image', sa.Float(), nullable=True))
    op.add_column('model_cost', sa.Column('cost_per_minute', sa.Float(), nullable=True))
    op.add_column('model_cost', sa.Column('cost_per_million_characters', sa.Float(), nullable=True))
    op.add_column('model_cost', sa.Column('cost_per_million_reasoning_tokens', sa.Float(), nullable=True))
    op.add_column('model_cost', sa.Column('cost_per_thousand_search_queries', sa.Float(), nullable=True))
    
    # Delete all existing rows
    op.execute(text("DELETE FROM model_cost"))
    
    # Insert new rows with model names and costs
    models_data = [
        ("Claude 3.5 Haiku", 0.80, 4.00, None, None),
        ("Llama 3.1", 5.00, 16.00, None, None),
        ("GPT o1", 16.50, 66.00, None, None),
        ("Perplexity Sonar Pro", 3.00, 15.00, None, 10.00),
        ("Perplexity Sonar Deep Research", 2.00, 8.00, 3.00, 5.00),
        ("Gemini 2.0 Flash", 0.15, 0.60, None, None),
        ("Claude 3.7 Sonnet", 3.00, 15.00, None, None),
        ("Perplexity Sonar Reasoning Pro", 2.00, 8.00, None, 10.00),
        ("Perplexity Sonar", 1.00, 1.00, None, 8.00),
        ("GPT o3-mini", 1.21, 4.84, None, None),
        ("Claude 3.5 Sonnet", 3.00, 15.00, None, None),
        ("GPT 4o", 2.75, 11.00, None, None),
        ("Pixtral Large", 2.00, 6.00, None, None),
        ("Mistral Large 2", 2.00, 6.00, None, None),
        ("GPT 4o-mini", 0.165, 0.66, None, None),
    ]
    
    for name, input_cost, output_cost, reasoning_cost, search_cost in models_data:
        op.execute(
            text(
                "INSERT INTO model_cost (model_name, cost_per_million_input_tokens, cost_per_million_output_tokens, cost_per_million_reasoning_tokens, cost_per_thousand_search_queries) "
                "VALUES (:model_name, :input_cost, :output_cost, :reasoning_cost, :search_cost)"
            ).bindparams(
                model_name=name,
                input_cost=input_cost,
                output_cost=output_cost,
                reasoning_cost=reasoning_cost,
                search_cost=search_cost
            )
        )
    
    # Add embedding model with cost per million input tokens
    op.execute(
        text(
            "INSERT INTO model_cost (model_name, cost_per_million_input_tokens) "
            "VALUES (:model_name, :cost_per_million_input_tokens)"
        ).bindparams(
            model_name="text-embedding-3-small",
            cost_per_million_input_tokens=0.02
        )
    )
    
    # Add DALL·E 3 with cost per image
    op.execute(
        text(
            "INSERT INTO model_cost (model_name, cost_per_image) "
            "VALUES (:model_name, :cost_per_image)"
        ).bindparams(
            model_name="dall-e-3",
            cost_per_image=0.08
        )
    )
    
    # Add tts-1 with cost per million characters
    op.execute(
        text(
            "INSERT INTO model_cost (model_name, cost_per_million_characters) "
            "VALUES (:model_name, :cost_per_million_characters)"
        ).bindparams(
            model_name="tts-1",
            cost_per_million_characters=15.00
        )
    )
    
    # Add whisper-1 with cost per minute
    op.execute(
        text(
            "INSERT INTO model_cost (model_name, cost_per_minute) "
            "VALUES (:model_name, :cost_per_minute)"
        ).bindparams(
            model_name="whisper-1",
            cost_per_minute=0.006
        )
    )



def downgrade() -> None:
    # Remove the new columns
    op.drop_column('model_cost', 'cost_per_million_characters')
    op.drop_column('model_cost', 'cost_per_minute')
    op.drop_column('model_cost', 'cost_per_image')
    op.drop_column('model_cost', 'cost_per_million_output_tokens')
    op.drop_column('model_cost', 'cost_per_million_input_tokens')
    op.drop_column('model_cost', 'cost_per_million_reasoning_tokens')
    op.drop_column('model_cost', 'cost_per_thousand_search_queries')

    
    # Add back the original column
    op.add_column('model_cost', sa.Column('message_credit_cost', sa.Float(), nullable=True))
    
    # Rename the table back to its original name
    op.rename_table('model_cost', 'model_message_credit_cost')
