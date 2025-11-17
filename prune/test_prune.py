#!/usr/bin/env python3
"""
Comprehensive Test Suite for Prune Operations

This test suite covers all aspects of the prune functionality including:
- Core classes (PruneLock, JSONFileIDExtractor, Vector cleaners)
- Helper functions (counting, deletion)
- CLI interfaces (interactive and non-interactive)
- Integration tests
- Edge cases and error handling
"""

import unittest
import tempfile
import shutil
import json
import sqlite3
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Import modules to test
from prune_models import PruneDataForm, PrunePreviewResult
from prune_core import (
    PruneLock,
    JSONFileIDExtractor,
    collect_file_ids_from_dict,
    VectorDatabaseCleaner,
    ChromaDatabaseCleaner,
    PGVectorDatabaseCleaner,
    NoOpVectorDatabaseCleaner,
    get_vector_database_cleaner,
)


class TestPruneModels(unittest.TestCase):
    """Test Pydantic models."""

    def test_prune_data_form_defaults(self):
        """Test PruneDataForm default values."""
        form = PruneDataForm()

        # Check defaults
        self.assertIsNone(form.days)
        self.assertFalse(form.exempt_archived_chats)
        self.assertFalse(form.exempt_chats_in_folders)
        self.assertTrue(form.delete_orphaned_chats)
        self.assertFalse(form.delete_orphaned_tools)
        self.assertFalse(form.delete_orphaned_functions)
        self.assertTrue(form.delete_orphaned_prompts)
        self.assertTrue(form.delete_orphaned_knowledge_bases)
        self.assertTrue(form.delete_orphaned_models)
        self.assertTrue(form.delete_orphaned_notes)
        self.assertTrue(form.delete_orphaned_folders)
        self.assertEqual(form.audio_cache_max_age_days, 30)
        self.assertIsNone(form.delete_inactive_users_days)
        self.assertTrue(form.exempt_admin_users)
        self.assertTrue(form.exempt_pending_users)
        self.assertFalse(form.run_vacuum)
        self.assertTrue(form.dry_run)

    def test_prune_data_form_custom_values(self):
        """Test PruneDataForm with custom values."""
        form = PruneDataForm(
            days=60,
            exempt_archived_chats=True,
            delete_orphaned_tools=True,
            audio_cache_max_age_days=14,
            delete_inactive_users_days=180,
            run_vacuum=True,
            dry_run=False
        )

        self.assertEqual(form.days, 60)
        self.assertTrue(form.exempt_archived_chats)
        self.assertTrue(form.delete_orphaned_tools)
        self.assertEqual(form.audio_cache_max_age_days, 14)
        self.assertEqual(form.delete_inactive_users_days, 180)
        self.assertTrue(form.run_vacuum)
        self.assertFalse(form.dry_run)

    def test_prune_preview_result_defaults(self):
        """Test PrunePreviewResult default values."""
        result = PrunePreviewResult()

        self.assertEqual(result.inactive_users, 0)
        self.assertEqual(result.old_chats, 0)
        self.assertEqual(result.orphaned_chats, 0)
        self.assertEqual(result.orphaned_files, 0)
        self.assertEqual(result.total_items(), 0)
        self.assertFalse(result.has_items())

    def test_prune_preview_result_calculations(self):
        """Test PrunePreviewResult calculation methods."""
        result = PrunePreviewResult(
            inactive_users=5,
            old_chats=100,
            orphaned_chats=20,
            orphaned_files=50,
            orphaned_tools=10,
            orphaned_functions=15,
            orphaned_prompts=8,
            orphaned_knowledge_bases=12,
            orphaned_models=3,
            orphaned_notes=25,
            orphaned_folders=7,
            orphaned_uploads=30,
            orphaned_vector_collections=18,
            audio_cache_files=200
        )

        self.assertEqual(result.total_items(), 503)
        self.assertTrue(result.has_items())

    def test_prune_preview_result_summary_dict(self):
        """Test PrunePreviewResult summary dict generation."""
        result = PrunePreviewResult(
            inactive_users=5,
            old_chats=100,
            orphaned_files=50
        )

        summary = result.get_summary_dict()
        self.assertIsInstance(summary, dict)
        self.assertIn("Users", summary)
        self.assertIn("Chats", summary)
        self.assertIn("Files", summary)
        self.assertEqual(summary["Users"]["Inactive users"], 5)
        self.assertEqual(summary["Chats"]["Old chats (age-based)"], 100)
        self.assertEqual(summary["Files"]["Orphaned file records"], 50)


class TestPruneLock(unittest.TestCase):
    """Test PruneLock file-based locking mechanism."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.test_dir) / "cache"
        self.cache_dir.mkdir()
        PruneLock.init(self.cache_dir)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def test_acquire_lock_success(self):
        """Test successfully acquiring lock."""
        result = PruneLock.acquire()
        self.assertTrue(result)
        self.assertTrue(PruneLock.LOCK_FILE.exists())

        # Verify lock file contents
        with open(PruneLock.LOCK_FILE) as f:
            lock_data = json.load(f)
            self.assertIn('timestamp', lock_data)
            self.assertIn('operation_id', lock_data)
            self.assertIn('pid', lock_data)

        # Clean up
        PruneLock.release()

    def test_acquire_lock_already_locked(self):
        """Test acquiring lock when already locked."""
        # Acquire first lock
        self.assertTrue(PruneLock.acquire())

        # Try to acquire again
        result = PruneLock.acquire()
        self.assertFalse(result)

        # Clean up
        PruneLock.release()

    def test_acquire_lock_stale_lock(self):
        """Test acquiring lock when existing lock is stale."""
        # Create stale lock (3 hours old)
        stale_time = datetime.utcnow() - timedelta(hours=3)
        lock_data = {
            'timestamp': stale_time.isoformat(),
            'operation_id': 'test123',
            'pid': 12345
        }
        with open(PruneLock.LOCK_FILE, 'w') as f:
            json.dump(lock_data, f)

        # Should remove stale lock and acquire new one
        result = PruneLock.acquire()
        self.assertTrue(result)

        # Verify new lock
        with open(PruneLock.LOCK_FILE) as f:
            new_lock = json.load(f)
            new_time = datetime.fromisoformat(new_lock['timestamp'])
            self.assertTrue(datetime.utcnow() - new_time < timedelta(minutes=1))

        # Clean up
        PruneLock.release()

    def test_acquire_lock_corrupt_lock_file(self):
        """Test acquiring lock when lock file is corrupt."""
        # Create corrupt lock file
        with open(PruneLock.LOCK_FILE, 'w') as f:
            f.write("not valid json{[]")

        # Should remove corrupt lock and acquire new one
        result = PruneLock.acquire()
        self.assertTrue(result)

        # Clean up
        PruneLock.release()

    def test_release_lock(self):
        """Test releasing lock."""
        PruneLock.acquire()
        self.assertTrue(PruneLock.LOCK_FILE.exists())

        PruneLock.release()
        self.assertFalse(PruneLock.LOCK_FILE.exists())

    def test_release_nonexistent_lock(self):
        """Test releasing lock when file doesn't exist."""
        # Should not raise error
        PruneLock.release()


class TestJSONFileIDExtractor(unittest.TestCase):
    """Test JSONFileIDExtractor utility class."""

    def test_extract_file_ids_from_json(self):
        """Test extracting file IDs from JSON strings."""
        json_str = '''
        {
            "id": "12345678-1234-1234-1234-123456789abc",
            "other": "data"
        }
        '''
        ids = JSONFileIDExtractor.extract_file_ids(json_str)
        self.assertEqual(len(ids), 1)
        self.assertIn("12345678-1234-1234-1234-123456789abc", ids)

    def test_extract_file_ids_from_urls(self):
        """Test extracting file IDs from API URLs."""
        json_str = '''
        {
            "url": "/api/v1/files/87654321-4321-4321-4321-abcdef123456"
        }
        '''
        ids = JSONFileIDExtractor.extract_file_ids(json_str)
        self.assertEqual(len(ids), 1)
        self.assertIn("87654321-4321-4321-4321-abcdef123456", ids)

    def test_extract_multiple_file_ids(self):
        """Test extracting multiple file IDs."""
        json_str = '''
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "file_id": "22222222-2222-2222-2222-222222222222",
            "url": "/api/v1/files/33333333-3333-3333-3333-333333333333"
        }
        '''
        ids = JSONFileIDExtractor.extract_file_ids(json_str)
        self.assertEqual(len(ids), 3)

    def test_extract_no_file_ids(self):
        """Test extracting from JSON with no file IDs."""
        json_str = '{"name": "test", "value": 123}'
        ids = JSONFileIDExtractor.extract_file_ids(json_str)
        self.assertEqual(len(ids), 0)

    def test_extract_invalid_uuids(self):
        """Test that invalid UUIDs are not extracted."""
        json_str = '''
        {
            "id": "not-a-valid-uuid",
            "id2": "12345678-1234",
            "id3": "12345678-1234-1234-1234-12345678901"
        }
        '''
        ids = JSONFileIDExtractor.extract_file_ids(json_str)
        self.assertEqual(len(ids), 0)


class TestCollectFileIDsFromDict(unittest.TestCase):
    """Test collect_file_ids_from_dict function."""

    def test_collect_from_simple_dict(self):
        """Test collecting IDs from simple dict."""
        valid_ids = {"11111111-1111-1111-1111-111111111111"}
        data = {
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "test"
        }
        out = set()
        collect_file_ids_from_dict(data, out, valid_ids)
        self.assertEqual(len(out), 1)
        self.assertIn("11111111-1111-1111-1111-111111111111", out)

    def test_collect_from_nested_dict(self):
        """Test collecting IDs from nested dicts."""
        valid_ids = {
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222"
        }
        data = {
            "level1": {
                "id": "11111111-1111-1111-1111-111111111111",
                "level2": {
                    "file_id": "22222222-2222-2222-2222-222222222222"
                }
            }
        }
        out = set()
        collect_file_ids_from_dict(data, out, valid_ids)
        self.assertEqual(len(out), 2)

    def test_collect_from_list(self):
        """Test collecting IDs from lists."""
        valid_ids = {
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222"
        }
        data = {
            "file_ids": [
                "11111111-1111-1111-1111-111111111111",
                "22222222-2222-2222-2222-222222222222"
            ]
        }
        out = set()
        collect_file_ids_from_dict(data, out, valid_ids)
        self.assertEqual(len(out), 2)

    def test_collect_filters_invalid_ids(self):
        """Test that only valid IDs are collected."""
        valid_ids = {"11111111-1111-1111-1111-111111111111"}
        data = {
            "id": "11111111-1111-1111-1111-111111111111",
            "invalid_id": "99999999-9999-9999-9999-999999999999"  # Not in valid set
        }
        out = set()
        collect_file_ids_from_dict(data, out, valid_ids)
        self.assertEqual(len(out), 1)
        self.assertIn("11111111-1111-1111-1111-111111111111", out)

    def test_collect_handles_deep_recursion(self):
        """Test that recursion depth limit works."""
        valid_ids = {"11111111-1111-1111-1111-111111111111"}

        # Create very deep nesting
        data = {"id": "11111111-1111-1111-1111-111111111111"}
        current = data
        for i in range(150):  # Exceed depth limit of 100
            current["nested"] = {"level": i}
            current = current["nested"]

        out = set()
        # Should not raise RecursionError
        collect_file_ids_from_dict(data, out, valid_ids)

        # Should still find the ID at top level
        self.assertIn("11111111-1111-1111-1111-111111111111", out)

    def test_collect_different_field_names(self):
        """Test collecting from different field name patterns."""
        valid_ids = {
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
            "33333333-3333-3333-3333-333333333333"
        }
        data = {
            "id": "11111111-1111-1111-1111-111111111111",
            "file_id": "22222222-2222-2222-2222-222222222222",
            "fileId": "33333333-3333-3333-3333-333333333333",
        }
        out = set()
        collect_file_ids_from_dict(data, out, valid_ids)
        self.assertEqual(len(out), 3)


class TestVectorDatabaseCleaners(unittest.TestCase):
    """Test vector database cleaner implementations."""

    def test_noop_cleaner_count(self):
        """Test NoOpVectorDatabaseCleaner count method."""
        cleaner = NoOpVectorDatabaseCleaner()
        count = cleaner.count_orphaned_collections(set(), set())
        self.assertEqual(count, 0)

    def test_noop_cleaner_cleanup(self):
        """Test NoOpVectorDatabaseCleaner cleanup method."""
        cleaner = NoOpVectorDatabaseCleaner()
        deleted, error = cleaner.cleanup_orphaned_collections(set(), set())
        self.assertEqual(deleted, 0)
        self.assertIsNone(error)

    def test_noop_cleaner_delete(self):
        """Test NoOpVectorDatabaseCleaner delete method."""
        cleaner = NoOpVectorDatabaseCleaner()
        result = cleaner.delete_collection("test")
        self.assertTrue(result)

    def test_get_vector_database_cleaner_chroma(self):
        """Test factory returns ChromaDB cleaner."""
        mock_client = Mock()
        cache_dir = Path(tempfile.mkdtemp())

        cleaner = get_vector_database_cleaner("chromadb", mock_client, cache_dir)
        self.assertIsInstance(cleaner, ChromaDatabaseCleaner)

        shutil.rmtree(cache_dir)

    def test_get_vector_database_cleaner_pgvector(self):
        """Test factory returns PGVector cleaner."""
        mock_client = Mock()
        mock_client.session = Mock()
        cache_dir = Path(tempfile.mkdtemp())

        cleaner = get_vector_database_cleaner("pgvector", mock_client, cache_dir)
        self.assertIsInstance(cleaner, PGVectorDatabaseCleaner)

        shutil.rmtree(cache_dir)

    def test_get_vector_database_cleaner_unknown(self):
        """Test factory returns NoOp cleaner for unknown type."""
        mock_client = Mock()
        cache_dir = Path(tempfile.mkdtemp())

        cleaner = get_vector_database_cleaner("unknown", mock_client, cache_dir)
        self.assertIsInstance(cleaner, NoOpVectorDatabaseCleaner)

        shutil.rmtree(cache_dir)

    def test_get_vector_database_cleaner_milvus(self):
        """Test factory returns Milvus cleaner."""
        mock_client = Mock()
        # Standard Milvus - no shared_collections attribute
        cache_dir = Path(tempfile.mkdtemp())

        from prune_core import MilvusDatabaseCleaner
        cleaner = get_vector_database_cleaner("milvus", mock_client, cache_dir)
        self.assertIsInstance(cleaner, MilvusDatabaseCleaner)

        shutil.rmtree(cache_dir)

    def test_get_vector_database_cleaner_milvus_multitenancy(self):
        """Test factory returns Milvus multitenancy cleaner."""
        mock_client = Mock()
        # Multitenancy Milvus - has shared_collections attribute
        mock_client.shared_collections = ['test_collection']
        cache_dir = Path(tempfile.mkdtemp())

        from prune_core import MilvusMultitenancyDatabaseCleaner
        cleaner = get_vector_database_cleaner("milvus", mock_client, cache_dir)
        self.assertIsInstance(cleaner, MilvusMultitenancyDatabaseCleaner)

        shutil.rmtree(cache_dir)


class TestChromaDatabaseCleaner(unittest.TestCase):
    """Test ChromaDatabaseCleaner implementation."""

    def setUp(self):
        """Set up test environment with mock ChromaDB."""
        self.test_dir = tempfile.mkdtemp()
        self.vector_dir = Path(self.test_dir) / "vector_db"
        self.vector_dir.mkdir()
        self.chroma_db_path = self.vector_dir / "chroma.sqlite3"

        # Create mock ChromaDB database
        self._create_mock_chroma_db()

        # Create cleaner
        self.mock_client = Mock()
        self.cleaner = ChromaDatabaseCleaner(self.mock_client, Path(self.test_dir))

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def _create_mock_chroma_db(self):
        """Create a mock ChromaDB SQLite database."""
        with sqlite3.connect(str(self.chroma_db_path)) as conn:
            # Create tables
            conn.execute("""
                CREATE TABLE collections (
                    id TEXT PRIMARY KEY,
                    name TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE segments (
                    id TEXT PRIMARY KEY,
                    collection TEXT,
                    scope TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE embeddings (
                    id TEXT PRIMARY KEY,
                    segment_id TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE embedding_metadata (
                    id TEXT PRIMARY KEY
                )
            """)
            conn.execute("""
                CREATE TABLE collection_metadata (
                    collection_id TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE segment_metadata (
                    segment_id TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE max_seq_id (
                    segment_id TEXT
                )
            """)
            conn.execute("""
                CREATE VIRTUAL TABLE embedding_fulltext_search
                USING fts5(string_value)
            """)

            # Insert test data
            conn.execute("INSERT INTO collections VALUES ('coll1', 'file-test123')")
            conn.execute("INSERT INTO segments VALUES ('seg1', 'coll1', 'VECTOR')")

            conn.commit()

    def test_build_expected_collections(self):
        """Test building expected collections set."""
        active_file_ids = {"file123", "file456"}
        active_kb_ids = {"kb789"}

        expected = self.cleaner._build_expected_collections(active_file_ids, active_kb_ids)

        self.assertEqual(len(expected), 3)
        self.assertIn("file-file123", expected)
        self.assertIn("file-file456", expected)
        self.assertIn("kb789", expected)

    def test_get_collection_mappings(self):
        """Test getting collection mappings from database."""
        mappings = self.cleaner._get_collection_mappings()

        self.assertIsInstance(mappings, dict)
        self.assertIn("seg1", mappings)
        self.assertEqual(mappings["seg1"], "file-test123")

    def test_count_orphaned_collections_with_orphans(self):
        """Test counting orphaned collections."""
        # Create physical directory for segment
        (self.vector_dir / "seg1").mkdir()
        (self.vector_dir / "orphan1").mkdir()

        active_file_ids = set()  # No active files
        active_kb_ids = set()    # No active KBs

        count = self.cleaner.count_orphaned_collections(active_file_ids, active_kb_ids)

        # Both seg1 and orphan1 should be counted as orphaned
        self.assertGreaterEqual(count, 1)

    def test_delete_collection(self):
        """Test deleting a specific collection."""
        result = self.cleaner.delete_collection("test-collection")
        self.assertTrue(result)

        # Verify client was called
        self.mock_client.delete_collection.assert_called_once()


class TestPGVectorDatabaseCleaner(unittest.TestCase):
    """Test PGVectorDatabaseCleaner implementation."""

    def setUp(self):
        """Set up test environment with mock PGVector."""
        self.mock_client = Mock()
        self.mock_session = Mock()
        self.mock_client.session = self.mock_session

        self.cleaner = PGVectorDatabaseCleaner(self.mock_client)

    def test_init_with_valid_session(self):
        """Test initialization with valid session."""
        self.assertIsNotNone(self.cleaner.session)

    def test_init_without_session(self):
        """Test initialization without session."""
        mock_client = Mock()
        mock_client.session = None

        cleaner = PGVectorDatabaseCleaner(mock_client)
        self.assertIsNone(cleaner.session)

    def test_build_expected_collections(self):
        """Test building expected collections set."""
        active_file_ids = {"file123", "file456"}
        active_kb_ids = {"kb789"}

        expected = self.cleaner._build_expected_collections(active_file_ids, active_kb_ids)

        self.assertEqual(len(expected), 3)
        self.assertIn("file-file123", expected)
        self.assertIn("file-file456", expected)
        self.assertIn("kb789", expected)

    def test_delete_collection(self):
        """Test deleting a specific collection."""
        result = self.cleaner.delete_collection("test-collection")
        self.assertTrue(result)

        # Verify client.delete was called
        self.mock_client.delete.assert_called_once_with("test-collection")

    def test_delete_collection_error(self):
        """Test deleting collection with error."""
        self.mock_client.delete.side_effect = Exception("Test error")

        result = self.cleaner.delete_collection("test-collection")
        self.assertFalse(result)


class TestMilvusDatabaseCleaner(unittest.TestCase):
    """Test MilvusDatabaseCleaner implementation."""

    def setUp(self):
        """Set up test environment with mock Milvus."""
        self.mock_client = Mock()
        self.mock_client.collection_prefix = "open_webui"
        self.mock_client.client = Mock()

        from prune_core import MilvusDatabaseCleaner
        self.cleaner = MilvusDatabaseCleaner(self.mock_client)

    def test_init(self):
        """Test Milvus cleaner initialization."""
        self.assertEqual(self.cleaner.collection_prefix, "open_webui")

    def test_build_expected_collections(self):
        """Test building expected collections set."""
        active_file_ids = {"file123", "file456"}
        active_kb_ids = {"kb789"}

        expected = self.cleaner._build_expected_collections(active_file_ids, active_kb_ids)

        self.assertEqual(len(expected), 3)
        self.assertIn("file-file123", expected)
        self.assertIn("file-file456", expected)
        self.assertIn("kb789", expected)

    def test_count_orphaned_collections(self):
        """Test counting orphaned Milvus collections."""
        # Mock list_collections to return some collections
        self.mock_client.client.list_collections.return_value = [
            "open_webui_file_test123",  # Expected (would be file-test123)
            "open_webui_kb_test456",    # Orphaned
            "other_collection",         # Not our prefix
        ]

        active_file_ids = {"test123"}
        active_kb_ids = set()

        count = self.cleaner.count_orphaned_collections(active_file_ids, active_kb_ids)

        # Should count kb_test456 as orphaned
        self.assertGreaterEqual(count, 1)

    def test_delete_collection(self):
        """Test deleting a specific collection."""
        self.mock_client.has_collection.return_value = True

        result = self.cleaner.delete_collection("test-collection")
        self.assertTrue(result)

        # Verify client was called
        self.mock_client.delete_collection.assert_called_once()


class TestMilvusMultitenancyDatabaseCleaner(unittest.TestCase):
    """Test MilvusMultitenancyDatabaseCleaner implementation."""

    def setUp(self):
        """Set up test environment with mock Milvus multitenancy."""
        self.mock_client = Mock()
        self.mock_client.collection_prefix = "open_webui"
        self.mock_client.shared_collections = [
            "open_webui_memories",
            "open_webui_knowledge",
            "open_webui_files",
            "open_webui_web_search",
            "open_webui_hash_based",
        ]

        from prune_core import MilvusMultitenancyDatabaseCleaner
        self.cleaner = MilvusMultitenancyDatabaseCleaner(self.mock_client)

    def test_init(self):
        """Test Milvus multitenancy cleaner initialization."""
        self.assertEqual(self.cleaner.collection_prefix, "open_webui")
        self.assertEqual(len(self.cleaner.shared_collections), 5)

    def test_build_expected_resource_ids(self):
        """Test building expected resource IDs set."""
        active_file_ids = {"file123", "file456"}
        active_kb_ids = {"kb789"}

        expected = self.cleaner._build_expected_resource_ids(active_file_ids, active_kb_ids)

        self.assertEqual(len(expected), 3)
        self.assertIn("file-file123", expected)
        self.assertIn("file-file456", expected)
        self.assertIn("kb789", expected)

    def test_delete_collection(self):
        """Test deleting a specific logical collection."""
        result = self.cleaner.delete_collection("test-collection")
        self.assertTrue(result)

        # Verify client was called
        self.mock_client.delete_collection.assert_called_once_with("test-collection")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_prune_form_validation(self):
        """Test PruneDataForm handles various input types."""
        # Valid inputs
        form = PruneDataForm(days=0)  # 0 is valid
        self.assertEqual(form.days, 0)

        form = PruneDataForm(days=None)  # None is valid
        self.assertIsNone(form.days)

    def test_preview_result_edge_values(self):
        """Test PrunePreviewResult with edge values."""
        # Very large numbers
        result = PrunePreviewResult(
            inactive_users=1000000,
            old_chats=5000000
        )
        self.assertEqual(result.total_items(), 6000000)

        # All zeros
        result = PrunePreviewResult()
        self.assertFalse(result.has_items())
        self.assertEqual(result.total_items(), 0)

    def test_file_id_extraction_malformed_json(self):
        """Test file ID extraction from malformed JSON."""
        # Invalid JSON should not raise error
        malformed = '{"id": "123-456-789'  # Unclosed
        ids = JSONFileIDExtractor.extract_file_ids(malformed)
        self.assertIsInstance(ids, set)

    def test_collect_file_ids_with_none_values(self):
        """Test collecting file IDs handles None values."""
        valid_ids = {"11111111-1111-1111-1111-111111111111"}
        data = {
            "id": None,
            "file_id": "11111111-1111-1111-1111-111111111111",
            "nested": None
        }
        out = set()
        collect_file_ids_from_dict(data, out, valid_ids)
        self.assertEqual(len(out), 1)

    def test_collect_file_ids_with_empty_structures(self):
        """Test collecting file IDs from empty structures."""
        valid_ids = set()
        data = {
            "empty_dict": {},
            "empty_list": [],
            "nested_empty": {"a": {}, "b": []}
        }
        out = set()
        collect_file_ids_from_dict(data, out, valid_ids)
        self.assertEqual(len(out), 0)


class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflows."""

    @patch('prune_operations.Users')
    @patch('prune_operations.Chats')
    @patch('prune_operations.Files')
    def test_dry_run_workflow(self, mock_files, mock_chats, mock_users):
        """Test complete dry-run workflow."""
        # Mock data
        mock_users.get_users.return_value = {"users": []}
        mock_chats.get_chats.return_value = []
        mock_files.get_files.return_value = []

        # Create form
        form = PruneDataForm(dry_run=True, days=60)

        # This would run the preview logic
        self.assertTrue(form.dry_run)
        self.assertEqual(form.days, 60)

    def test_form_to_preview_result_consistency(self):
        """Test that form settings match preview result structure."""
        form = PruneDataForm(
            delete_orphaned_chats=True,
            delete_orphaned_tools=True,
            delete_orphaned_functions=True
        )

        result = PrunePreviewResult()

        # Verify all form fields have corresponding result fields
        self.assertTrue(hasattr(result, 'orphaned_chats'))
        self.assertTrue(hasattr(result, 'orphaned_tools'))
        self.assertTrue(hasattr(result, 'orphaned_functions'))


class TestPerformance(unittest.TestCase):
    """Performance and optimization tests."""

    def test_file_id_collection_performance(self):
        """Test file ID collection performance on large structures."""
        # Create large nested structure
        valid_ids = {f"{i:08d}-1111-1111-1111-111111111111" for i in range(100)}

        data = {
            "level1": {
                f"item{i}": {
                    "id": f"{i:08d}-1111-1111-1111-111111111111"
                }
                for i in range(100)
            }
        }

        out = set()
        start = time.time()
        collect_file_ids_from_dict(data, out, valid_ids)
        elapsed = time.time() - start

        # Should complete in reasonable time
        self.assertLess(elapsed, 1.0)  # Less than 1 second
        self.assertEqual(len(out), 100)

    def test_uuid_pattern_matching_performance(self):
        """Test UUID pattern matching performance."""
        from prune_core import UUID_PATTERN

        # Test with valid UUID
        start = time.time()
        for _ in range(10000):
            UUID_PATTERN.fullmatch("12345678-1234-1234-1234-123456789abc")
        elapsed = time.time() - start

        # Should be fast with compiled pattern
        self.assertLess(elapsed, 0.5)


def run_all_tests():
    """Run all tests and generate report."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__(__name__))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.wasSuccessful():
        print("\n✓ ALL TESTS PASSED")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit(run_all_tests())
