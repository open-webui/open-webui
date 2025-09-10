import json
from open_webui.utils.pii import consolidate_pii_data, text_masking, set_file_entity_ids


def test_set_file_entity_ids():
    """Test set file entity ids functionality - set id from known entities or next free id"""
    known_entities = [
        {"id": 1, "label": "PERSON_1", "name": "john doe"},
        {"id": 2, "label": "EMAIL_1", "name": "john@example.com"},
    ]
    file_entities_dict = {
        "jane smith": {
            "id": 1,
            "label": "PERSON_1",
            "text": "jane smith",
            "type": "PERSON",
            "occurrences": [{"start_idx": 0, "end_idx": 8}],
            "raw_text": "Jane Smith",
        },
        "john doe": {
            "id": 2,
            "label": "PERSON_2",
            "text": "john doe",
            "type": "PERSON",
            "occurrences": [{"start_idx": 10, "end_idx": 18}],
            "raw_text": "John Doe",
        },
    }
    result = set_file_entity_ids(file_entities_dict, known_entities)
    assert len(result) == 2
    assert result["jane smith"]["id"] == 3  # changed to next 'free' id
    assert result["jane smith"]["label"] == "PERSON_3"
    assert result["jane smith"]["raw_text"] == "Jane Smith"
    assert result["jane smith"]["text"] == "jane smith"
    assert result["jane smith"]["type"] == "PERSON"
    assert result["jane smith"]["occurrences"] == [{"start_idx": 0, "end_idx": 8}]
    assert result["john doe"]["id"] == 1  # set id from known entities
    assert result["john doe"]["label"] == "PERSON_1"
    assert result["john doe"]["raw_text"] == "John Doe"
    assert result["john doe"]["text"] == "john doe"
    assert result["john doe"]["type"] == "PERSON"
    assert result["john doe"]["occurrences"] == [{"start_idx": 10, "end_idx": 18}]


def test_consolidate_pii_data_basic():
    """
    Test basic PII consolidation functionality - same text, different ID
    file_entities_dict is already consolidated
    """

    pii_data = [
        {
            "text": "john doe",
            "label": "PERSON_3",
            "type": "PERSON",
            "occurrences": [{"start_idx": 0, "end_idx": 8}],
            "id": 3,
            "raw_text": "John Doe",
        },
        {
            "text": "john@example.com",
            "label": "EMAIL_4",
            "type": "EMAIL",
            "occurrences": [{"start_idx": 10, "end_idx": 25}],
            "id": 4,
            "raw_text": "john@example.com",
        },
    ]

    file_entities_dict = {
        "john doe": {
            "text": "john doe",
            "label": "PERSON_1",
            "type": "PERSON",
            "occurrences": [{"start_idx": 0, "end_idx": 8}],
            "id": 1,
            "raw_text": "John Doe",
        },
        "john@example.com": {
            "text": "john@example.com",
            "label": "EMAIL_2",
            "type": "EMAIL",
            "occurrences": [{"start_idx": 10, "end_idx": 25}],
            "id": 2,
            "raw_text": "john@example.com",
        },
        "ACME Inc.": {
            "text": "ACME Inc.",
            "label": "ORGANIZATION_3",
            "type": "ORGANIZATION",
            "occurrences": [{"start_idx": 26, "end_idx": 34}],
            "id": 3,
            "raw_text": "ACME Inc.",
        },
    }

    result = consolidate_pii_data(pii_data, file_entities_dict)

    # Check that IDs are properly assigned
    assert len(result) == 2
    assert result[0]["id"] == 1  # John Doe should get ID 1
    assert result[1]["id"] == 2  # john@example.com should get ID 2


def test_text_masking_basic():
    """Test basic text masking functionality"""
    text = "Hello John Doe, your email is john@example.com"

    pii_list = [
        {
            "type": "PERSON",
            "id": 1,
            "text": "John Doe",
            "occurrences": [{"start_idx": 6, "end_idx": 14}],
        },
        {
            "type": "EMAIL",
            "id": 2,
            "text": "john@example.com",
            "occurrences": [{"start_idx": 30, "end_idx": 46}],
        },
    ]

    result = text_masking(text, pii_list, [])

    expected = "Hello [{PERSON_1}], your email is [{EMAIL_2}]"
    assert result == expected


def test_text_masking_overlapping_entities():
    """Test text masking with overlapping entities"""
    text = "John Doe Smith"

    pii_list = [
        {
            "type": "PERSON",
            "id": 1,
            "text": "John Doe",
            "occurrences": [{"start_idx": 0, "end_idx": 8}],
        },
        {
            "type": "PERSON",
            "id": 2,
            "text": "Doe Smith",
            "occurrences": [{"start_idx": 5, "end_idx": 14}],
        },
    ]

    result = text_masking(text, pii_list, [])

    # Should handle overlapping entities (longer span takes precedence)
    assert "John [{PERSON_2}]" in result  # Doe Smith should be masked


def test_pii_data_parsing_from_metadata():
    """Test parsing PII data from document metadata"""
    # Simulate PII data stored as JSON string in metadata
    pii_dict = {
        "John Doe": {
            "id": 1,
            "label": "PERSON_1",
            "type": "PERSON",
            "text": "John Doe",
            "occurrences": [{"start_idx": 0, "end_idx": 8}],
        },
        "john@example.com": {
            "id": 2,
            "label": "EMAIL_1",
            "type": "EMAIL",
            "text": "john@example.com",
            "occurrences": [{"start_idx": 10, "end_idx": 25}],
        },
    }

    pii_json = json.dumps(pii_dict)
    parsed_pii = json.loads(pii_json)
    pii_data = list(parsed_pii.values())

    assert len(pii_data) == 2
    assert pii_data[0]["text"] == "John Doe"
    assert pii_data[1]["text"] == "john@example.com"


def test_consolidation_with_empty_data():
    """Test consolidation with empty or invalid data"""
    # Empty PII data
    result = consolidate_pii_data([], {})
    assert len(result) == 0


def test_set_file_entity_ids_with_empty_known_entities():
    """Test set file entity ids with empty known entities"""
    known_entities = []
    file_entities_dict = {
        "john doe": {
            "id": 2,
            "label": "PERSON_2",
            "text": "john doe",
            "type": "PERSON",
            "occurrences": [{"start_idx": 0, "end_idx": 8}],
        }
    }
    result = set_file_entity_ids(file_entities_dict, known_entities)
    assert len(result) == 1
    assert result["john doe"]["id"] == 1
    assert result["john doe"]["label"] == "PERSON_1"
    assert result["john doe"]["type"] == "PERSON"
    assert result["john doe"]["occurrences"] == [{"start_idx": 0, "end_idx": 8}]
