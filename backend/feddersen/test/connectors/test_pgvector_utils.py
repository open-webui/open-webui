import pytest
from copy import deepcopy
from feddersen.connectors.pgvector.pgvector import FeddersenPGVectorConnector
from feddersen.config import EXTRA_MIDDLEWARE_METADATA_KEY


@pytest.fixture
def sample_metadata():
    return [
        {
            "name": "Document1",
            "file_id": "1",
            EXTRA_MIDDLEWARE_METADATA_KEY: {"date": "2023-01-01T00:00:00Z"},
        },
        {
            "name": "Document2",
            "file_id": "2",
            EXTRA_MIDDLEWARE_METADATA_KEY: {"date": "2023-02-01T00:00:00Z"},
        },
        {
            "name": "Document1",
            "file_id": "3",
            EXTRA_MIDDLEWARE_METADATA_KEY: {"date": "2023-03-01T00:00:00Z"},
        },
        {
            "name": "Document3",
            "file_id": "4",
            EXTRA_MIDDLEWARE_METADATA_KEY: {"date": "2023-04-01T00:00:00Z"},
        },
    ]


def test_make_titles_unique_no_duplicates():
    metadata = [
        {
            "name": "Document1",
            "file_id": "1",
            EXTRA_MIDDLEWARE_METADATA_KEY: {"date": "2023-01-01T00:00:00Z"},
        },
        {
            "name": "Document2",
            "file_id": "2",
            EXTRA_MIDDLEWARE_METADATA_KEY: {"date": "2023-02-01T00:00:00Z"},
        },
    ]
    result = FeddersenPGVectorConnector.make_titles_unique(metadata)
    assert result == metadata  # No changes expected


def test_make_titles_unique_with_duplicates(sample_metadata):
    result = FeddersenPGVectorConnector.make_titles_unique(sample_metadata)
    expected = deepcopy(sample_metadata)
    expected[0]["name"] = "Document1 (01/23)"
    expected[2]["name"] = "Document1 (03/23)"
    assert result == expected


def test_make_titles_unique_missing_date():
    metadata = [
        {"name": "Document1", "file_id": "1", EXTRA_MIDDLEWARE_METADATA_KEY: {}},
        {
            "name": "Document1",
            "file_id": "2",
            EXTRA_MIDDLEWARE_METADATA_KEY: {"date": "2023-03-01T00:00:00Z"},
        },
    ]
    result = FeddersenPGVectorConnector.make_titles_unique(metadata)
    expected = deepcopy(metadata)
    expected[1]["name"] = "Document1 (03/23)"
    assert result == expected


def test_make_titles_unique_empty_metadata():
    metadata = []
    result = FeddersenPGVectorConnector.make_titles_unique(metadata)
    assert result == []  # No changes expected
