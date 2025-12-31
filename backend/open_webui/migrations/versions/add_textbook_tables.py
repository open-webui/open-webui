"""Add textbook tables (section, chapter, question)

Revision ID: add_textbook_tables
Revises: add_chat_settings_columns
Create Date: 2024-12-22 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "add_textbook_tables"
down_revision = "add_chat_settings_columns"
branch_labels = None
depends_on = None


def upgrade():
    # Create textbook_section table
    op.create_table(
        "textbook_section",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("order", sa.Integer(), default=0),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.BigInteger()),
        sa.Column("updated_at", sa.BigInteger()),
    )

    # Create textbook_chapter table
    op.create_table(
        "textbook_chapter",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "section_id",
            sa.String(),
            sa.ForeignKey("textbook_section.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column("order", sa.Integer(), default=0),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("rag_store_name", sa.String(), nullable=True),  # RAG Store 매핑
        sa.Column("created_at", sa.BigInteger()),
        sa.Column("updated_at", sa.BigInteger()),
    )

    # Create textbook_question table
    op.create_table(
        "textbook_question",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "chapter_id",
            sa.String(),
            sa.ForeignKey("textbook_chapter.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("order", sa.Integer(), default=0),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.BigInteger()),
        sa.Column("updated_at", sa.BigInteger()),
    )

    # Create indexes for better query performance
    op.create_index("idx_textbook_chapter_section_id", "textbook_chapter", ["section_id"])
    op.create_index("idx_textbook_question_chapter_id", "textbook_question", ["chapter_id"])


def downgrade():
    op.drop_index("idx_textbook_question_chapter_id", table_name="textbook_question")
    op.drop_index("idx_textbook_chapter_section_id", table_name="textbook_chapter")
    op.drop_table("textbook_question")
    op.drop_table("textbook_chapter")
    op.drop_table("textbook_section")
