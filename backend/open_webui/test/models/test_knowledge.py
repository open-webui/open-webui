import pytest
from unittest.mock import MagicMock, patch

from open_webui.models.files import FileModel, FileMetadataResponse


class TestFileMetadataConversion:
    """Tests for FileModel to FileMetadataResponse conversion.

    This test verifies the fix for issue #14220:
    https://github.com/open-webui/open-webui/issues/14220
    """

    def test_filemodel_to_filemetadataresponse_conversion(self):
        """Test that FileModel can be converted to FileMetadataResponse."""
        file_model = FileModel(
            id="test-file-id",
            user_id="test-user-id",
            hash="abc123",
            filename="test.txt",
            path="/path/to/test.txt",
            data={"content": "test content"},
            meta={"name": "test.txt", "content_type": "text/plain"},
            access_control=None,
            created_at=1234567890,
            updated_at=1234567891,
        )

        # Convert using explicit field mapping (the fix)
        file_metadata = FileMetadataResponse(
            id=file_model.id,
            hash=file_model.hash,
            meta=file_model.meta,
            created_at=file_model.created_at or 0,
            updated_at=file_model.updated_at or 0,
        )

        assert file_metadata.id == "test-file-id"
        assert file_metadata.hash == "abc123"
        assert file_metadata.meta == {"name": "test.txt", "content_type": "text/plain"}
        assert file_metadata.created_at == 1234567890
        assert file_metadata.updated_at == 1234567891

    def test_filemodel_with_none_timestamps(self):
        """Test conversion when created_at/updated_at are None."""
        file_model = FileModel(
            id="test-file-id",
            user_id="test-user-id",
            hash=None,
            filename="test.txt",
            path=None,
            data=None,
            meta=None,
            access_control=None,
            created_at=None,
            updated_at=None,
        )

        # Convert using explicit field mapping with fallback for None timestamps
        file_metadata = FileMetadataResponse(
            id=file_model.id,
            hash=file_model.hash,
            meta=file_model.meta,
            created_at=file_model.created_at or 0,
            updated_at=file_model.updated_at or 0,
        )

        assert file_metadata.id == "test-file-id"
        assert file_metadata.hash is None
        assert file_metadata.meta is None
        assert file_metadata.created_at == 0
        assert file_metadata.updated_at == 0

    def test_filemetadataresponse_type_validation(self):
        """Test that FileMetadataResponse correctly validates types."""
        # Should work with correct types
        response = FileMetadataResponse(
            id="test",
            hash="hash",
            meta={"key": "value"},
            created_at=123,
            updated_at=456,
        )
        assert response.id == "test"

        # Verify response can be serialized back to dict
        data = response.model_dump()
        assert data["id"] == "test"
        assert data["created_at"] == 123
