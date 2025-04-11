import logging

import pytest
from feddersen.config import EXTRA_MIDDLEWARE_METADATA_KEY
from feddersen.connectors.pgvector.pgvector import DocumentAuthChunk


class TestDocumentAuthChunk:
    def test_document_auth_chunk_create(self, mocker):
        # Test data
        id = "test_id"
        collection_name = "test_collection"
        text = "test text"
        vector = [0.1] * 1536
        metadata = {
            EXTRA_MIDDLEWARE_METADATA_KEY: {
                "auth": {"groups": ["group1"], "users": ["user1"]},
                "metadata": {"title": "Test Document"},
            },
            "source": "test_source",
        }

        mocker.patch("feddersen.connectors.pgvector.pgvector.DocumentAuthChunk")
        # Mock prepare_metadata
        mocker.patch.object(
            DocumentAuthChunk,
            "prepare_metadata",
            return_value=(
                {
                    "source": "test_source",
                    EXTRA_MIDDLEWARE_METADATA_KEY: {"title": "Test Document"},
                },
                {"groups": ["group1"], "users": ["user1"]},
            ),
        )

        # Call the create method
        chunk = DocumentAuthChunk.create(
            id=id,
            collection_name=collection_name,
            text=text,
            vector=vector,
            vmetadata=metadata,
            custom_metadata_key=EXTRA_MIDDLEWARE_METADATA_KEY,
        )

        # Assertions
        assert chunk.id == id
        assert chunk.collection_name == collection_name
        assert chunk.text == text
        assert chunk.vector == vector

    def test_prepare_metadata_empty_input(self):
        # Test with None metadata
        meta, auth = DocumentAuthChunk.prepare_metadata(
            None, EXTRA_MIDDLEWARE_METADATA_KEY
        )
        assert meta == {}
        assert auth == {"groups": [], "users": []}

        # Test with empty dict
        meta, auth = DocumentAuthChunk.prepare_metadata(
            {}, EXTRA_MIDDLEWARE_METADATA_KEY
        )
        assert meta == {}
        assert auth == {"groups": [], "users": []}

    @pytest.mark.parametrize("users", [["first.last@test.de"], ["First.Last@test.de"]])
    def test_prepare_metadata_with_custom_metadata(self, mocker, users):
        expected_users = [user.lower() for user in users]
        # Setup mock for ExtraMetadata
        mock_metadata = mocker.MagicMock()
        mock_metadata.model_dump.return_value = {
            "title": "Test Document",
            "url": "test_url",
            "date": "2021-01-01T00:00:00Z",
            "context_url": "test_context_url",
        }

        mock_auth = mocker.MagicMock()
        mock_auth.model_dump.return_value = {
            "groups": ["group1"],
            "users": expected_users,
        }

        mock_extra = mocker.MagicMock()
        mock_extra.metadata = mock_metadata
        mock_extra.auth = mock_auth

        mock_extra_metadata = mocker.patch("feddersen.models.ExtraMetadata")
        mock_extra_metadata.model_validate.return_value = mock_extra

        # Test data
        metadata = {
            EXTRA_MIDDLEWARE_METADATA_KEY: {
                "auth": {"groups": ["group1"], "users": users},
                "metadata": {
                    "title": "Test Document",
                    "url": "test_url",
                    "date": "2021-01-01T00:00:00Z",
                    "context_url": "test_context_url",
                    "source": "test_source",
                },
            },
        }

        # Call method
        meta, auth = DocumentAuthChunk.prepare_metadata(
            metadata, EXTRA_MIDDLEWARE_METADATA_KEY
        )

        # Assertions
        assert meta == {
            EXTRA_MIDDLEWARE_METADATA_KEY: {
                "title": "Test Document",
                "url": "test_url",
                "date": "2021-01-01T00:00:00Z",
                "context_url": "test_context_url",
                "source": "test_source",
            }
        }
        assert auth == {"groups": ["group1"], "users": expected_users}

    def test_prepare_metadata_with_key_replacements(self):
        # Test data with actual values
        metadata = {
            "name": "asldkfjasldfj.pdf",
            EXTRA_MIDDLEWARE_METADATA_KEY: {
                "auth": {"groups": ["group1"], "users": ["user1"]},
                "metadata": {
                    "title": "Test Document",
                    "url": "test_url",
                    "date": "2021-01-01T00:00:00Z",
                    "source": "test_source",
                },
            },
        }
        replace_keys = {"name": "title"}

        # Call method
        meta, auth = DocumentAuthChunk.prepare_metadata(
            metadata, EXTRA_MIDDLEWARE_METADATA_KEY, replace_keys
        )

        # Assertions
        assert "name" in meta
        assert meta["name"] == "Test Document"

    def test_prepare_metadata_key_replacement_error(self, caplog):
        # Test data
        metadata = {
            EXTRA_MIDDLEWARE_METADATA_KEY: {
                "auth": {"groups": ["group1"], "users": ["user1"]},
                "metadata": {
                    "title": "Test Document",
                    "url": "test_url",
                    "context_url": "test_context_url",
                    "date": "2021-01-01T00:00:00Z",
                    "source": "test_source",
                },
            },
        }
        # Attempt to replace 'title' with 'name', but the attribute doesn't exist
        replace_keys = {"name": "nonexistent_attribute"}

        with caplog.at_level(logging.WARNING):
            # Call the actual method
            meta, auth = DocumentAuthChunk.prepare_metadata(
                metadata, EXTRA_MIDDLEWARE_METADATA_KEY, replace_keys
            )

        # Assertions
        assert (
            "name" not in meta
        )  # 'name' should not be in metadata since replacement failed
        assert meta == {
            EXTRA_MIDDLEWARE_METADATA_KEY: {
                "title": "Test Document",
                "url": "test_url",
                "context_url": "test_context_url",
                "date": "2021-01-01T00:00:00Z",
                "source": "test_source",
            }
        }
        assert auth == {"groups": ["group1"], "users": ["user1"]}
        assert "Couldn't replace" in caplog.text

    def test_prepare_metadata_empty_middleware_metadata(self):
        # Test data with empty middleware_metadata
        metadata = {EXTRA_MIDDLEWARE_METADATA_KEY: "{}"}

        # Call method
        meta, auth = DocumentAuthChunk.prepare_metadata(
            metadata, EXTRA_MIDDLEWARE_METADATA_KEY
        )

        # Assertions
        assert meta == {}
        assert auth == {"groups": [], "users": []}
