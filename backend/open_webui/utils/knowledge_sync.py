"""Helpers for comparing a local directory manifest with knowledge files."""

from collections.abc import Iterable
from typing import Protocol


class ManifestEntry(Protocol):
    filename: str
    path: str
    checksum: str


def diff_manifest_files(
    manifest: Iterable[ManifestEntry],
    indexed_files: dict[tuple[str, str], dict],
    in_flight_files: set[tuple[str, str, str]],
) -> tuple[list[dict], list[dict], list[dict], int]:
    """Compare manifest files with linked and currently processing files."""
    added: list[dict] = []
    modified: list[dict] = []
    deleted: list[dict] = []
    unmodified_count = 0
    manifest_keys: set[tuple[str, str]] = set()

    for entry in manifest:
        key = (entry.path, entry.filename)
        manifest_keys.add(key)

        if key not in indexed_files:
            if (entry.path, entry.filename, entry.checksum) in in_flight_files:
                unmodified_count += 1
            else:
                added.append({'filename': entry.filename, 'path': entry.path})
        elif indexed_files[key]['checksum'] != entry.checksum:
            modified.append(
                {
                    'filename': entry.filename,
                    'path': entry.path,
                    'stale_file_id': indexed_files[key]['file_id'],
                }
            )
        else:
            unmodified_count += 1

    for key, file_info in indexed_files.items():
        if key not in manifest_keys:
            deleted.append({'file_id': file_info['file_id'], 'filename': key[1]})

    return added, modified, deleted, unmodified_count
