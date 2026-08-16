from dataclasses import dataclass

from open_webui.utils.knowledge_sync import diff_manifest_files


@dataclass
class ManifestEntry:
    filename: str
    path: str
    checksum: str


def test_matching_in_flight_file_is_not_added_again():
    manifest = [ManifestEntry(filename='guide.md', path='docs', checksum='same-hash')]

    added, modified, deleted, unmodified_count = diff_manifest_files(
        manifest,
        indexed_files={},
        in_flight_files={('docs', 'guide.md', 'same-hash')},
    )

    assert added == []
    assert modified == []
    assert deleted == []
    assert unmodified_count == 1


def test_changed_in_flight_file_can_be_uploaded():
    manifest = [ManifestEntry(filename='guide.md', path='docs', checksum='new-hash')]

    added, modified, deleted, unmodified_count = diff_manifest_files(
        manifest,
        indexed_files={},
        in_flight_files={('docs', 'guide.md', 'old-hash')},
    )

    assert added == [{'filename': 'guide.md', 'path': 'docs'}]
    assert modified == []
    assert deleted == []
    assert unmodified_count == 0


def test_file_absent_from_in_flight_set_can_be_retried():
    manifest = [ManifestEntry(filename='failed.md', path='', checksum='file-hash')]

    added, modified, deleted, unmodified_count = diff_manifest_files(
        manifest,
        indexed_files={},
        in_flight_files=set(),
    )

    assert added == [{'filename': 'failed.md', 'path': ''}]
    assert modified == []
    assert deleted == []
    assert unmodified_count == 0


def test_linked_file_changes_are_preserved():
    manifest = [
        ManifestEntry(filename='changed.md', path='', checksum='new-hash'),
        ManifestEntry(filename='same.md', path='', checksum='same-hash'),
    ]
    indexed_files = {
        ('', 'changed.md'): {'file_id': 'changed-id', 'checksum': 'old-hash'},
        ('', 'same.md'): {'file_id': 'same-id', 'checksum': 'same-hash'},
        ('', 'deleted.md'): {'file_id': 'deleted-id', 'checksum': 'deleted-hash'},
    }

    added, modified, deleted, unmodified_count = diff_manifest_files(
        manifest,
        indexed_files=indexed_files,
        in_flight_files=set(),
    )

    assert added == []
    assert modified == [
        {
            'filename': 'changed.md',
            'path': '',
            'stale_file_id': 'changed-id',
        }
    ]
    assert deleted == [{'file_id': 'deleted-id', 'filename': 'deleted.md'}]
    assert unmodified_count == 1
