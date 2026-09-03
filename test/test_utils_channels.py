from open_webui.utils.channels import contains_user_mentions, extract_user_mention_ids


def test_extract_user_mention_ids_returns_unique_authorized_users():
    message = '<@U:user-2|Ada> <@U:user-2|Ada> <@U:user-3|Grace>'

    assert extract_user_mention_ids(message, 'user-1', {'user-2', 'user-4'}) == ['user-2']


def test_extract_user_mention_ids_excludes_sender_and_non_users():
    message = '<@U:user-1|Sender> <@U:user-2|Ada> <@M:model-1|Model> <@U:user-3|Other>'

    assert extract_user_mention_ids(message, 'user-1', {'user-1', 'user-2'}) == ['user-2']


def test_extract_user_mention_ids_requires_encoded_mentions():
    message = '@user-2 <@M:user-2|Model> <@U:user-2|Teammate'

    assert extract_user_mention_ids(message, 'user-1', {'user-2'}) == []


def test_extract_user_mention_ids_accepts_only_user_mentions():
    message = '@user-2 <@M:user-2|Model> <@U:user-2|Teammate>'

    assert extract_user_mention_ids(message, 'user-1', {'user-2'}) == ['user-2']


def test_extract_user_mention_ids_rejects_unauthorized_and_self_mentions():
    message = '<@U:user-1|Sender> <@U:user-2|Teammate> <@U:user-3|Other>'

    assert extract_user_mention_ids(message, 'user-1', {'user-1', 'user-4'}) == []


def test_contains_user_mentions_only_matches_encoded_user_mentions():
    assert contains_user_mentions('<@U:user-1|Teammate> hello') is True
    assert contains_user_mentions('@Teammate <@M:model-1|Model>') is False
