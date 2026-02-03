#!/usr/bin/env python3
"""
Generate DATABASE_SCHEMA.md from SQLAlchemy model definitions.

Usage:
    python docs/scripts/generate_schema_docs.py > docs/DATABASE_SCHEMA.md

This script introspects all SQLAlchemy models in the Open WebUI codebase
and generates comprehensive Markdown documentation.

Requirements:
    - Must be run from the project root
    - Backend dependencies must be installed
"""

import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

def get_column_type(column) -> str:
    """Convert SQLAlchemy column type to readable string."""
    type_str = str(column.type)

    # Simplify common types
    type_map = {
        'VARCHAR': 'String',
        'TEXT': 'Text',
        'INTEGER': 'Integer',
        'BIGINT': 'BigInteger',
        'BOOLEAN': 'Boolean',
        'JSON': 'JSON',
        'DATETIME': 'DateTime',
    }

    for sql_type, readable in type_map.items():
        if sql_type in type_str.upper():
            return readable

    return type_str


def get_column_default(column) -> str:
    """Extract default value from column."""
    if column.default is None:
        return '—'

    if hasattr(column.default, 'arg'):
        arg = column.default.arg
        if callable(arg):
            return f'{arg.__name__}()'
        return str(arg)

    return str(column.default)


def generate_table_docs(model_class) -> str:
    """Generate Markdown documentation for a single model."""
    table = model_class.__table__
    lines = []

    lines.append(f"## Table: {table.name}")
    lines.append("")

    # Get docstring if available
    if model_class.__doc__:
        lines.append(model_class.__doc__.strip())
        lines.append("")

    # Column table
    lines.append("| Column | Type | Nullable | Default | Description |")
    lines.append("|--------|------|----------|---------|-------------|")

    for column in table.columns:
        col_type = get_column_type(column)
        nullable = 'Yes' if column.nullable else 'No'
        default = get_column_default(column)

        # Try to get description from column doc or info
        description = ''
        if hasattr(column, 'doc') and column.doc:
            description = column.doc
        elif hasattr(column, 'info') and column.info.get('description'):
            description = column.info['description']

        lines.append(f"| `{column.name}` | {col_type} | {nullable} | {default} | {description} |")

    lines.append("")

    # Primary key
    pk_cols = [col.name for col in table.primary_key.columns]
    if len(pk_cols) > 1:
        lines.append(f"**Primary Key:** `({', '.join(pk_cols)})`")
    else:
        lines.append(f"**Primary Key:** `{pk_cols[0]}`")
    lines.append("")

    # Foreign keys
    if table.foreign_keys:
        lines.append("**Foreign Keys:**")
        for fk in table.foreign_keys:
            lines.append(f"- `{fk.parent.name}` → `{fk.column.table.name}.{fk.column.name}`")
        lines.append("")

    # Indexes
    if table.indexes:
        lines.append("**Indexes:**")
        for idx in table.indexes:
            cols = ', '.join([col.name for col in idx.columns])
            unique = ' (unique)' if idx.unique else ''
            lines.append(f"- `{idx.name}` on `({cols})`{unique}")
        lines.append("")

    lines.append("---")
    lines.append("")

    return '\n'.join(lines)


def main():
    """Generate complete DATABASE_SCHEMA.md content."""

    # Header
    print("# Database Schema Reference")
    print("")
    print(f"> **Generated:** {datetime.now().strftime('%Y-%m-%d')} from SQLAlchemy models")
    print("> **Source:** `backend/open_webui/models/`")
    print("> **Regenerate:** `python docs/scripts/generate_schema_docs.py > docs/DATABASE_SCHEMA.md`")
    print("")
    print("---")
    print("")

    try:
        # Import all models
        from open_webui.models.users import User
        from open_webui.models.auths import Auth, ApiKey
        from open_webui.models.groups import Group, GroupMember
        from open_webui.models.chats import Chat
        from open_webui.models.chat_messages import ChatMessage
        from open_webui.models.channels import Channel, ChannelMember, Message, MessageReaction, ChannelWebhook
        from open_webui.models.files import File
        from open_webui.models.knowledge import Knowledge, KnowledgeFile
        from open_webui.models.memories import Memory
        from open_webui.models.notes import Note
        from open_webui.models.folders import Folder
        from open_webui.models.tags import Tag
        from open_webui.models.prompts import Prompt, PromptHistory
        from open_webui.models.functions import Function
        from open_webui.models.tools import Tool
        from open_webui.models.models import Model
        from open_webui.models.feedbacks import Feedback
        from open_webui.models.oauth_sessions import OAuthSession

        # List of models in logical order
        models = [
            User, Auth, ApiKey,
            Group, GroupMember,
            Chat, ChatMessage,
            Channel, ChannelMember, Message, MessageReaction, ChannelWebhook,
            File,
            Knowledge, KnowledgeFile,
            Memory, Note, Folder, Tag,
            Prompt, PromptHistory,
            Function, Tool, Model,
            Feedback, OAuthSession,
        ]

        # Overview table
        print("## Overview")
        print("")
        print("| Table | Primary Key |")
        print("|-------|-------------|")
        for model in models:
            table = model.__table__
            pk_cols = [col.name for col in table.primary_key.columns]
            pk_str = f"`({', '.join(pk_cols)})`" if len(pk_cols) > 1 else f"`{pk_cols[0]}`"
            print(f"| `{table.name}` | {pk_str} |")
        print("")
        print("---")
        print("")

        # Generate docs for each model
        for model in models:
            print(generate_table_docs(model))

        # Footer
        print("## Related Documents")
        print("")
        print("- `DATA_MODEL.md` — Conceptual entity relationships")
        print("- `DOMAIN_GLOSSARY.md` — Term definitions")
        print("- `DIRECTIVE_database_migration.md` — How to modify schema")
        print("")
        print("---")
        print("")
        print(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    except ImportError as e:
        print(f"Error importing models: {e}", file=sys.stderr)
        print("Make sure you're running from the project root with backend dependencies installed.", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
