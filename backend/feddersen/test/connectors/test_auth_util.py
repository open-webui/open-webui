import json

import pytest
from sqlalchemy import Column, Integer
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import declarative_base

from ...connectors.pgvector.auth_util import FilterUtils

Base = declarative_base()


class CustomModel(Base):
    """Mock model for testing"""

    __tablename__ = "test_table"
    id = Column(Integer, primary_key=True)  # Add primary key column
    metadata_column = Column("metadata", MutableDict.as_mutable(postgresql.JSONB))


@pytest.fixture
def filter_utils():
    return FilterUtils()


@pytest.fixture
def metadata_column():
    return CustomModel.metadata_column


def test_filter_for_empty_auth(metadata_column):
    """Test the filter for documents with empty auth metadata"""
    filter_clause = FilterUtils.filter_for_empty_auth(
        metadata_column, group_field_name="groups", user_field_name="users"
    )

    # Convert the filter clause to a SQL string for verification
    sql_str = str(
        filter_clause.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )

    # Check that the SQL correctly tests for NULL or empty arrays
    assert "metadata IS NULL" in sql_str
    assert "metadata -> 'groups'" in sql_str
    assert "metadata -> 'users'" in sql_str


def test_create_auth_filter_clause(filter_utils, metadata_column):
    """Test the complete auth filter clause creation"""
    user_mail = "test@example.com"
    user_entra_groups = ["group1", "group2"]

    filter_clause = filter_utils.create_auth_filter_clause(
        user_mail=user_mail,
        user_entra_groups=user_entra_groups,
        metadata_column=metadata_column,
        group_field_name="groups",
        user_field_name="users",
    )

    sql_str = str(
        filter_clause.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    # Check that the SQL contains all necessary conditions
    assert "metadata IS NULL" in sql_str  # Public documents
    assert json.dumps(user_mail) in sql_str  # User-specific access
    assert f"ARRAY{user_entra_groups} in sql_str"  # Group-specific access
