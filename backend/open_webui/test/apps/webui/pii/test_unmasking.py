"""
Tests for PII unmasking functionality.

These tests verify that masked PII placeholders like [{PERSON_1}] are correctly
replaced with their original values when preparing messages for RAG queries.
"""

from open_webui.utils.pii import unmask_text_with_known_entities
from open_webui.utils.middleware import unmask_messages_for_rag


def test_unmask_text_basic():
    """Test basic text unmasking with standard pattern [{LABEL}]"""
    text = "Hello [{PERSON_1}], your email is [{EMAIL_2}]"
    known_entities = [
        {"label": "PERSON_1", "name": "John Doe"},
        {"label": "EMAIL_2", "name": "john@example.com"},
    ]
    
    result = unmask_text_with_known_entities(text, known_entities)
    expected = "Hello John Doe, your email is john@example.com"
    
    assert result == expected


def test_unmask_text_multiple_occurrences():
    """Test unmasking multiple occurrences of the same entity"""
    text = "[{PERSON_1}] called [{PERSON_1}] but [{PERSON_1}] didn't answer"
    known_entities = [
        {"label": "PERSON_1", "name": "Charlie"},
    ]
    
    result = unmask_text_with_known_entities(text, known_entities)
    expected = "Charlie called Charlie but Charlie didn't answer"
    
    assert result == expected


def test_unmask_text_with_special_characters():
    """Test unmasking with special characters in entity names"""
    text = "Visit [{ADDRESS_1}] or email [{EMAIL_1}]"
    known_entities = [
        {"label": "ADDRESS_1", "name": "123 Main St., Apt #5"},
        {"label": "EMAIL_1", "name": "test+user@example.com"},
    ]
    
    result = unmask_text_with_known_entities(text, known_entities)
    expected = "Visit 123 Main St., Apt #5 or email test+user@example.com"
    
    assert result == expected


def test_unmask_text_empty_entities():
    """Test unmasking with empty known_entities list"""
    text = "Hello [{PERSON_1}], your email is [{EMAIL_2}]"
    known_entities = []
    
    result = unmask_text_with_known_entities(text, known_entities)
    # Should return unchanged text when no entities provided
    assert result == text


def test_unmask_text_none_entities():
    """Test unmasking with None entities"""
    text = "Hello [{PERSON_1}]"
    known_entities = None
    
    result = unmask_text_with_known_entities(text, known_entities)
    # Should handle None gracefully
    assert result == text


def test_unmask_text_empty_string():
    """Test unmasking empty text"""
    text = ""
    known_entities = [{"label": "PERSON_1", "name": "John"}]
    
    result = unmask_text_with_known_entities(text, known_entities)
    assert result == ""


def test_unmask_text_no_placeholders():
    """Test unmasking text without any placeholders"""
    text = "This is plain text without any PII placeholders"
    known_entities = [
        {"label": "PERSON_1", "name": "John Doe"},
    ]
    
    result = unmask_text_with_known_entities(text, known_entities)
    # Should return unchanged
    assert result == text


def test_unmask_text_partial_match():
    """Test unmasking doesn't match partial labels"""
    text = "[{PERSON_10}] and [{PERSON_1}]"
    known_entities = [
        {"label": "PERSON_1", "name": "Alice"},
        {"label": "PERSON_10", "name": "Bob"},
    ]
    
    result = unmask_text_with_known_entities(text, known_entities)
    expected = "Bob and Alice"
    
    assert result == expected


def test_unmask_text_missing_label():
    """Test unmasking with missing label in known_entities"""
    text = "Hello [{PERSON_1}], contact [{EMAIL_1}]"
    known_entities = [
        {"label": "PERSON_1", "name": "John Doe"},
        # EMAIL_1 is missing
    ]
    
    result = unmask_text_with_known_entities(text, known_entities)
    expected = "Hello John Doe, contact [{EMAIL_1}]"
    
    # EMAIL_1 should remain masked
    assert result == expected


def test_unmask_text_organization_types():
    """Test unmasking with different PII types"""
    text = "Contact [{PERSON_1}] at [{ORG_1}] via [{PHONE_1}]"
    known_entities = [
        {"label": "PERSON_1", "name": "Sarah Johnson"},
        {"label": "ORG_1", "name": "Acme Corporation"},
        {"label": "PHONE_1", "name": "+1-555-123-4567"},
    ]
    
    result = unmask_text_with_known_entities(text, known_entities)
    expected = "Contact Sarah Johnson at Acme Corporation via +1-555-123-4567"
    
    assert result == expected


# Tests for unmask_messages_for_rag


def test_unmask_messages_simple_string_content():
    """Test unmasking messages with simple string content"""
    messages = [
        {"role": "user", "content": "Tell me about [{PERSON_1}]"},
        {"role": "assistant", "content": "Here's info about [{PERSON_1}]"},
        {"role": "user", "content": "What about [{ORG_1}]?"},
    ]
    known_entities = [
        {"label": "PERSON_1", "name": "John Smith"},
        {"label": "ORG_1", "name": "Tech Corp"},
    ]
    
    result = unmask_messages_for_rag(messages, known_entities)
    
    assert len(result) == 3
    assert result[0]["content"] == "Tell me about John Smith"
    assert result[1]["content"] == "Here's info about John Smith"
    assert result[2]["content"] == "What about Tech Corp?"


def test_unmask_messages_list_content():
    """Test unmasking messages with list content (multimodal)"""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Look at [{PERSON_1}]"},
                {"type": "image", "url": "https://example.com/image.jpg"},
            ],
        },
    ]
    known_entities = [
        {"label": "PERSON_1", "name": "Alice Cooper"},
    ]
    
    result = unmask_messages_for_rag(messages, known_entities)
    
    assert len(result) == 1
    assert isinstance(result[0]["content"], list)
    assert result[0]["content"][0]["text"] == "Look at Alice Cooper"
    assert result[0]["content"][1]["type"] == "image"  # Image unchanged


def test_unmask_messages_mixed_content():
    """Test unmasking with mix of string and list content"""
    messages = [
        {"role": "user", "content": "Simple text about [{PERSON_1}]"},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Complex about [{PERSON_1}]"},
            ],
        },
    ]
    known_entities = [
        {"label": "PERSON_1", "name": "David Lee"},
    ]
    
    result = unmask_messages_for_rag(messages, known_entities)
    
    assert result[0]["content"] == "Simple text about David Lee"
    assert result[1]["content"][0]["text"] == "Complex about David Lee"


def test_unmask_messages_preserves_other_fields():
    """Test unmasking preserves other message fields"""
    messages = [
        {
            "role": "user",
            "content": "[{PERSON_1}] needs help",
            "timestamp": 1234567890,
            "metadata": {"source": "web"},
        },
    ]
    known_entities = [
        {"label": "PERSON_1", "name": "Emma"},
    ]
    
    result = unmask_messages_for_rag(messages, known_entities)
    
    assert result[0]["content"] == "Emma needs help"
    assert result[0]["role"] == "user"
    assert result[0]["timestamp"] == 1234567890
    assert result[0]["metadata"] == {"source": "web"}


def test_unmask_messages_empty_list():
    """Test unmasking with empty message list"""
    messages = []
    known_entities = [{"label": "PERSON_1", "name": "Test"}]
    
    result = unmask_messages_for_rag(messages, known_entities)
    
    assert result == []


def test_unmask_messages_no_entities():
    """Test unmasking with no known entities"""
    messages = [
        {"role": "user", "content": "[{PERSON_1}] is here"},
    ]
    known_entities = []
    
    result = unmask_messages_for_rag(messages, known_entities)
    
    # Should return original messages when no entities
    assert result == messages


def test_unmask_messages_creates_deep_copy():
    """Test that unmasking creates a deep copy (doesn't mutate original)"""
    original_messages = [
        {"role": "user", "content": "[{PERSON_1}] visited"},
    ]
    known_entities = [
        {"label": "PERSON_1", "name": "Frank"},
    ]
    
    result = unmask_messages_for_rag(original_messages, known_entities)
    
    # Original should be unchanged
    assert original_messages[0]["content"] == "[{PERSON_1}] visited"
    # Result should be unmasked
    assert result[0]["content"] == "Frank visited"


def test_unmask_messages_multiple_entities_in_one_message():
    """Test unmasking multiple entities in a single message"""
    messages = [
        {
            "role": "user",
            "content": "[{PERSON_1}] from [{ORG_1}] emailed [{EMAIL_1}]",
        },
    ]
    known_entities = [
        {"label": "PERSON_1", "name": "Grace Lee"},
        {"label": "ORG_1", "name": "Global Inc"},
        {"label": "EMAIL_1", "name": "info@global.com"},
    ]
    
    result = unmask_messages_for_rag(messages, known_entities)
    
    expected = "Grace Lee from Global Inc emailed info@global.com"
    assert result[0]["content"] == expected


def test_unmask_messages_system_role():
    """Test unmasking works with system messages"""
    messages = [
        {"role": "system", "content": "You are helping [{PERSON_1}]"},
        {"role": "user", "content": "I need assistance"},
    ]
    known_entities = [
        {"label": "PERSON_1", "name": "Dr. Smith"},
    ]
    
    result = unmask_messages_for_rag(messages, known_entities)
    
    assert result[0]["role"] == "system"
    assert result[0]["content"] == "You are helping Dr. Smith"


def test_unmask_messages_empty_content():
    """Test unmasking handles empty content gracefully"""
    messages = [
        {"role": "user", "content": ""},
        {"role": "user"},  # Missing content
    ]
    known_entities = [
        {"label": "PERSON_1", "name": "Test"},
    ]
    
    result = unmask_messages_for_rag(messages, known_entities)
    
    assert len(result) == 2
    assert result[0]["content"] == ""
    assert result[1].get("content", "") == ""


def test_unmask_messages_non_text_list_items():
    """Test unmasking preserves non-text items in content list"""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "[{PERSON_1}] attached a file"},
                {"type": "image", "url": "img.jpg"},
                {"type": "file", "id": "file-123"},
                {"type": "text", "text": "Check [{EMAIL_1}]"},
            ],
        },
    ]
    known_entities = [
        {"label": "PERSON_1", "name": "Helen"},
        {"label": "EMAIL_1", "name": "helen@test.com"},
    ]
    
    result = unmask_messages_for_rag(messages, known_entities)
    
    content = result[0]["content"]
    assert len(content) == 4
    assert content[0]["text"] == "Helen attached a file"
    assert content[1]["type"] == "image"
    assert content[2]["type"] == "file"
    assert content[3]["text"] == "Check helen@test.com"


def test_unmask_messages_realistic_conversation():
    """Test unmasking a realistic conversation for RAG"""
    messages = [
        {
            "role": "user",
            "content": "What projects has [{PERSON_1}] worked on at [{ORG_1}]?",
        },
        {
            "role": "assistant",
            "content": "[{PERSON_1}] has led several initiatives at [{ORG_1}].",
        },
        {
            "role": "user",
            "content": "Can you tell me more about their work in [{LOCATION_1}]?",
        },
    ]
    known_entities = [
        {"label": "PERSON_1", "name": "Dr. Sarah Johnson"},
        {"label": "ORG_1", "name": "Research Institute"},
        {"label": "LOCATION_1", "name": "Silicon Valley"},
    ]
    
    result = unmask_messages_for_rag(messages, known_entities)
    
    assert result[0]["content"] == "What projects has Dr. Sarah Johnson worked on at Research Institute?"
    assert result[1]["content"] == "Dr. Sarah Johnson has led several initiatives at Research Institute."
    assert result[2]["content"] == "Can you tell me more about their work in Silicon Valley?"

