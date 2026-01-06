"""Add tenant help text column populated from default markdown

Revision ID: 7bd26b4a8c12
Revises: 6a50f39757df
Create Date: 2025-03-20 00:00:00.000000

"""

import os
from typing import Sequence, Union

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import MEDIUMTEXT

# revision identifiers, used by Alembic.
revision: str = "7bd26b4a8c12"
down_revision: Union[str, None] = "6a50f39757df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def _load_default_help_text() -> str:
    bucket = os.environ.get("S3_PROMPT_BUCKET_NAME") or os.environ.get(
        "S3_BUCKET_NAME"
    )
    key = os.environ.get("DEFAULT_HELP_S3_KEY", "prompts/default-help.md")

    if not bucket or not key:
        raise RuntimeError(
            "S3_PROMPT_BUCKET_NAME and DEFAULT_HELP_S3_KEY must be configured."
        )
    
    print(f"Bucket: {bucket}\nKey: {key}")

    client = boto3.client(
        "s3",
        region_name=os.environ.get("S3_REGION_NAME"),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("S3_SECRET_ACCESS_KEY"),
        endpoint_url=os.environ.get("S3_ENDPOINT_URL"),
        config=Config(
            s3={
                "use_accelerate_endpoint": os.environ.get(
                    "S3_USE_ACCELERATE_ENDPOINT", "false"
                ).lower()
                == "true",
                "addressing_style": os.environ.get("S3_ADDRESSING_STYLE"),
            }
        ),
    )

    try:
        obj = client.get_object(Bucket=bucket, Key=key)
    except (ClientError, BotoCoreError) as exc:
        raise RuntimeError(
            f"Failed to load default help markdown from s3://{bucket}/{key}"
        ) from exc

    body = obj.get("Body")
    if not body:
        raise RuntimeError(
            f"Empty response body when loading s3://{bucket}/{key}"
        )

    return body.read().decode("utf-8")


def upgrade() -> None:
    help_text_type = sa.Text().with_variant(MEDIUMTEXT, "mysql")
    default_help_text = _load_default_help_text()


    op.add_column(
        "tenant",
        sa.Column("help_text", help_text_type, nullable=True),
    )

    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE tenant SET help_text = :default_text"),
        {"default_text": default_help_text},
    )

    op.alter_column(
        "tenant",
        "help_text",
        existing_type=help_text_type,
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("tenant", "help_text")
