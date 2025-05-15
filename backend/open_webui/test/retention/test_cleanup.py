from unittest.mock import patch, MagicMock
from open_webui.retention.cleanup import _cleanup_old_data


@patch("open_webui.retention.cleanup.get_db")
@patch("open_webui.retention.cleanup.Storage.delete_file")
@patch("open_webui.retention.cleanup.VECTOR_DB_CLIENT.delete_collection")
def test_cleanup_old_data_once(mock_delete_collection, mock_delete_file, mock_get_db):
    # Setup mock DB session and return values
    mock_session = MagicMock()
    mock_get_db.return_value.__enter__.return_value = mock_session

    # Mock queries
    mock_session.query().filter().count.side_effect = [
        2,
        3,
        1,
    ]  # chats, messages, files
    mock_session.query().filter().all.return_value = [
        MagicMock(path="file1", meta={"collection_name": "col1"}),
        MagicMock(path="file2", meta={"collection_name": "col2"}),
    ]

    # Call the function
    results = _cleanup_old_data()

    # Assertions
    assert results["deleted_chats"] == 2
    assert results["deleted_messages"] == 3
    assert results["deleted_files"] == 1
    assert results["deleted_collections"] == 2
    assert mock_delete_file.call_count == 2
    assert mock_delete_collection.call_count == 2
