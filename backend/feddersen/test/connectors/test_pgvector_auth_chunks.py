import datetime
from unittest.mock import MagicMock, patch

import pytest
from pytest_postgresql import factories
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker

from feddersen.config import EXTRA_MIDDLEWARE_METADATA_KEY
from feddersen.connectors.pgvector.pgvector import (
    VECTOR_LENGTH,
    Base,
    DocumentAuthChunk,
    FeddersenPGVectorConnector,
)
from open_webui.models.users import UserModel

# Create a PostgreSQL database for testing
postgresql_noproc = factories.postgresql_noproc(user="postgres", password="postgres")
postgresql_external = factories.postgresql("postgresql_noproc", "test_db")


@pytest.fixture
def db_engine(postgresql_external):
    """Create a SQLAlchemy engine connected to the test database."""
    # Format: postgresql://user:password@host:port/dbname
    connection_str = f"postgresql://{postgresql_external.info.user}:{postgresql_external.info.password}@{postgresql_external.info.host}:{postgresql_external.info.port}/{postgresql_external.info.dbname}"

    engine = create_engine(connection_str)

    # Create extension and tables
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    Base.metadata.create_all(engine)

    yield engine

    # Clean up
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine):
    """Create a SQLAlchemy session for testing."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = scoped_session(SessionLocal)

    yield session

    # Clean up
    session.close()


@pytest.fixture
def mock_user_groups_retriever():
    """Mock the UserGroupsRetriever class."""
    with patch(
        "feddersen.connectors.pgvector.pgvector.UserGroupsRetriever"
    ) as mock_retriever:
        mock_instance = MagicMock()
        mock_instance.get_user_groups.return_value = ["test_group"]
        mock_retriever.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def test_user():
    """Create a test user model."""
    return UserModel(
        id="test_user_id",
        email="test@example.com",
        name="Test User",
        role="user",
        profile_image_url="/docs.png",
        last_active_at=123456789,
        updated_at=123456789,
        created_at=123456789,
    )


def create_chunk(collection_name: str, title: str, users: list[str], groups: list[str]):
    return DocumentAuthChunk(
        id=title,
        collection_name=collection_name,
        text="No access document",
        vector=[0.1] * VECTOR_LENGTH,
        vmetadata={
            "name": title,
            "source": "test",
            EXTRA_MIDDLEWARE_METADATA_KEY: {
                "title": title,
                "url": f"http://example.com/{title}",
                "created_at": datetime.datetime.now().isoformat(),
            },
        },
        file_auth={"groups": groups, "users": users},
    )


@pytest.fixture
def setup_test_data(db_session, test_user):
    """Fixture to initialize the database with test document chunks."""
    collection_name = "test_collection"

    chunks = [
        # User-specific access
        create_chunk(
            collection_name, "user_only_doc", users=[test_user.email], groups=[]
        ),
        # Group-specific access
        create_chunk(
            collection_name, "group_only_doc", users=[], groups=["test_group"]
        ),
        # Both user and group access
        create_chunk(
            collection_name,
            "user_and_group_doc",
            users=[test_user.email],
            groups=["test_group"],
        ),
        # Different user access
        create_chunk(
            collection_name, "different_user_doc", users=["other@test.de"], groups=[]
        ),
        # Different group access
        create_chunk(
            collection_name, "different_group_doc", users=[], groups=["other_group"]
        ),
        # Multiple users access
        create_chunk(
            collection_name,
            "multi_user_doc",
            users=[test_user.email, "other@test.de"],
            groups=[],
        ),
        # Multiple groups access
        create_chunk(
            collection_name,
            "multi_group_doc",
            users=[],
            groups=["test_group", "other_group"],
        ),
        # No access restrictions
        create_chunk(collection_name, "public_doc", users=[], groups=[]),
    ]

    # Insert chunks
    db_session.bulk_save_objects(chunks)
    db_session.commit()

    return collection_name


def test_document_auth_chunk_basic_query(
    db_session, setup_test_data, mock_user_groups_retriever, test_user
):
    """Test basic insertion and querying of DocumentAuthChunk."""
    collection_name = "test_collection"

    # Create connector with mocked session
    with patch(
        "feddersen.connectors.pgvector.pgvector.UserGroupsRetriever",
        return_value=mock_user_groups_retriever,
    ):
        connector = FeddersenPGVectorConnector(db_session)

        # Test query with filter
        result = connector.query(
            collection_name=collection_name,
            filter={"source": "test"},
            limit=10,
            user=test_user,
        )

        # Assertions
        assert result is not None
        # Should find 5 documents (not the no_access one)
        assert len(result.ids[0]) == 6


def test_user_specific_access(
    db_session, setup_test_data, mock_user_groups_retriever, test_user
):
    """Test that a user can access documents specifically shared with them."""
    collection_name = setup_test_data

    with patch(
        "feddersen.connectors.pgvector.pgvector.UserGroupsRetriever",
        return_value=mock_user_groups_retriever,
    ):
        connector = FeddersenPGVectorConnector(db_session)

        # Query by the specific document title
        result = connector.query(
            collection_name=collection_name,
            filter={"name": "user_only_doc"},
            limit=10,
            user=test_user,
        )

        assert len(result.ids[0]) == 1
        assert "user_only_doc" in result.ids[0]


def test_group_specific_access(
    db_session, setup_test_data, mock_user_groups_retriever, test_user
):
    """Test that a user can access documents shared with groups they belong to."""
    collection_name = setup_test_data

    with patch(
        "feddersen.connectors.pgvector.pgvector.UserGroupsRetriever",
        return_value=mock_user_groups_retriever,
    ):
        connector = FeddersenPGVectorConnector(db_session)

        # Query by the specific document title
        result = connector.query(
            collection_name=collection_name,
            filter={"name": "group_only_doc"},
            limit=10,
            user=test_user,
        )

        assert len(result.ids[0]) == 1
        assert "group_only_doc" in result.ids[0]


def test_public_document_access(
    db_session, setup_test_data, mock_user_groups_retriever, test_user
):
    """Test that a user can access documents with no access restrictions."""
    collection_name = setup_test_data

    with patch(
        "feddersen.connectors.pgvector.pgvector.UserGroupsRetriever",
        return_value=mock_user_groups_retriever,
    ):
        connector = FeddersenPGVectorConnector(db_session)

        # Query by the specific document title
        result = connector.query(
            collection_name=collection_name,
            filter={"name": "public_doc"},
            limit=10,
            user=test_user,
        )

        assert len(result.ids[0]) == 1
        assert "public_doc" in result.ids[0]


def test_different_user_access_denied(
    db_session, setup_test_data, mock_user_groups_retriever, test_user
):
    """Test that a user cannot access documents shared with different users only."""
    collection_name = setup_test_data

    with patch(
        "feddersen.connectors.pgvector.pgvector.UserGroupsRetriever",
        return_value=mock_user_groups_retriever,
    ):
        connector = FeddersenPGVectorConnector(db_session)

        # Query by the specific document title
        result = connector.query(
            collection_name=collection_name,
            filter={"name": "different_user_doc"},
            limit=10,
            user=test_user,
        )

        assert result is None


def test_different_group_access_denied(
    db_session, setup_test_data, mock_user_groups_retriever, test_user
):
    """Test that a user cannot access documents shared with groups they don't belong to."""
    collection_name = setup_test_data

    with patch(
        "feddersen.connectors.pgvector.pgvector.UserGroupsRetriever",
        return_value=mock_user_groups_retriever,
    ):
        connector = FeddersenPGVectorConnector(db_session)

        # Query by the specific document title
        result = connector.query(
            collection_name=collection_name,
            filter={"title": "different_group_doc"},
            limit=10,
            user=test_user,
        )

        assert result is None


def test_multi_user_access(
    db_session, setup_test_data, mock_user_groups_retriever, test_user
):
    """Test that a user can access documents shared with multiple users including them."""
    collection_name = setup_test_data

    with patch(
        "feddersen.connectors.pgvector.pgvector.UserGroupsRetriever",
        return_value=mock_user_groups_retriever,
    ):
        connector = FeddersenPGVectorConnector(db_session)

        # Query by the specific document title
        result = connector.query(
            collection_name=collection_name,
            filter={"name": "multi_user_doc"},
            limit=10,
            user=test_user,
        )

        assert len(result.ids[0]) == 1
        assert "multi_user_doc" in result.ids[0]


def test_multi_group_access(
    db_session, setup_test_data, mock_user_groups_retriever, test_user
):
    """Test that a user can access documents shared with multiple groups including their groups."""
    collection_name = setup_test_data

    with patch(
        "feddersen.connectors.pgvector.pgvector.UserGroupsRetriever",
        return_value=mock_user_groups_retriever,
    ):
        connector = FeddersenPGVectorConnector(db_session)

        # Query by the specific document title
        result = connector.query(
            collection_name=collection_name,
            filter={"name": "multi_group_doc"},
            limit=10,
            user=test_user,
        )

        assert len(result.ids[0]) == 1
        assert "multi_group_doc" in result.ids[0]


def test_anonymous_access(db_session, setup_test_data, mock_user_groups_retriever):
    """Test that an anonymous user (no user object) can only access public documents."""
    collection_name = setup_test_data
    # Mock to return no groups for this user
    mock_user_groups_retriever.get_user_groups.return_value = []

    with patch(
        "feddersen.connectors.pgvector.pgvector.UserGroupsRetriever",
        return_value=mock_user_groups_retriever,
    ):
        connector = FeddersenPGVectorConnector(db_session)

        # Query for all documents with anonymous access
        result = connector.query(
            collection_name=collection_name, filter={}, limit=10, user=None
        )

        # Should only get public documents
        assert len(result.ids[0]) == 1
        assert "public_doc" in result.ids[0]


def test_different_user_with_no_permissions(
    db_session, setup_test_data, mock_user_groups_retriever
):
    """Test access with a user who has no matching groups."""
    collection_name = setup_test_data

    # Create a different user with no matching permissions
    other_user = UserModel(
        id="other_user_id",
        email="no_access@example.com",
        name="Other User",
        role="user",
        profile_image_url="/docs.png",
        last_active_at=123456789,
        updated_at=123456789,
        created_at=123456789,
    )

    # Mock to return no groups for this user
    mock_user_groups_retriever.get_user_groups.return_value = []

    with patch(
        "feddersen.connectors.pgvector.pgvector.UserGroupsRetriever",
        return_value=mock_user_groups_retriever,
    ):
        connector = FeddersenPGVectorConnector(db_session)

        # Query for all documents
        result = connector.query(
            collection_name=collection_name, filter={}, limit=10, user=other_user
        )

        # Should only see public documents and documents shared directly with them
        assert len(result.ids[0]) == 1
        assert "public_doc" in result.ids[0]
