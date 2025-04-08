"""Add prebuilt prompts to prompt table

Revision ID: 54243f6ae1ba
Revises: d0d528b0ec66
Create Date: 2025-04-08 13:57:53.447122

"""
from typing import Sequence, Union
import csv
import time
import io
import json
import os
import pathlib

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session


# revision identifiers, used by Alembic.
revision: str = '54243f6ae1ba'
down_revision: Union[str, None] = 'd0d528b0ec66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create a connection and bind a session
    connection = op.get_bind()
    session = Session(bind=connection)
    
    # Get the path to the CSV file
    current_dir = pathlib.Path(__file__).parent.parent
    csv_file_path = current_dir / "data" / "prebuilt_prompts.csv"
    
    # Read the CSV data from file
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        csv_reader = csv.DictReader(f)
        
        # Insert prompts into the database
        current_time = int(time.time())
        system_user_id = "system"  # Use a system user ID for prebuilt prompts

        for row in csv_reader:
            # Generate a command from the title (lowercase, replace spaces with underscores)
            command = row['title'].lower().replace(' ', '-')
            
            # Create meta with tags
            meta = {
                "tags": [{"name": row['tag']}]
            }
            
            # Insert the prompt using parameterized query
            insert_query = sa.text("""
                INSERT INTO prompt (command, user_id, title, content, timestamp, meta, prebuilt, description)
                VALUES (:command, :user_id, :title, :content, :timestamp, :meta, :prebuilt, :description)
            """)
            
            session.execute(insert_query, {
                "command": f"/{command}",
                "user_id": system_user_id,
                "title": row['title'],
                "content": row['content'],
                "timestamp": current_time,
                "meta": json.dumps(meta),
                "prebuilt": True,
                "description": row['description']
            })
        
        # Commit the changes
        session.commit()


def downgrade() -> None:
    # Create a connection
    connection = op.get_bind()
    session = Session(bind=connection)
    
    # Delete all prebuilt prompts
    delete_query = sa.text("DELETE FROM prompt WHERE prebuilt = :prebuilt")
    session.execute(delete_query, {"prebuilt": True})
    
    # Commit the changes
    session.commit()
