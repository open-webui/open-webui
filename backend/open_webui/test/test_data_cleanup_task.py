from datetime import datetime
import time
from pathlib import Path
from typing import Literal, NamedTuple

from open_webui.test.util.abstract_integration_test import AbstractDBTest, AbstractPostgresTest, AbstractSQLiteTest
from open_webui.test.util.mock_user import mock_webui_user
from pydantic import BaseModel

class DataCleanupTaskUnitTestMixin(AbstractDBTest):
    "tests individual functions of the data cleanup task, with any DB backend"

    def test_try_acquire_db_lock_exclusive(self):
        """
        Test that the try_acquire_db_lock method works as expected.
        Ideally this would be tested across multiple processes, but this is fine for now.
        """
        from open_webui.data_cleanup_task import try_acquire_db_lock
        with (
            try_acquire_db_lock("test") as acquired_a,
            try_acquire_db_lock("test") as acquired_b
        ):
            assert acquired_a != acquired_b # xor
    
    def test_delete_cache_files(self):
        from open_webui.data_cleanup_task import CACHE_DIR, delete_cache_files
        def dummy_paths(cache_paths: list[str]) -> list[Path]:
            fps = [Path(CACHE_DIR) / path for path in cache_paths]
            for fp in fps:
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.touch()
            return fps
        
        before_cutoff = dummy_paths(["audio/dummy_before.wav", "image/dummy_before.png"])
        cutoff = datetime.now()
        after_cutoff = dummy_paths(["audio/dummy_after.wav", "image/dummy_after.png"])
        
        delete_cache_files(cutoff)
        
        # Check that the older files were deleted
        for dummy_fp in before_cutoff:
            assert not dummy_fp.exists()
        # and the newer ones were not
        for dummy_fp in after_cutoff:
            assert dummy_fp.exists()
    
    def test_delete_chats_and_uploads(self):
        from open_webui.data_cleanup_task import delete_chats_and_uploads, VECTOR_DB_CLIENT
        from open_webui.models.chats import Chats
        from open_webui.models.files import Files

        # a url file that's shared between all chats
        shared_web_url = "https://google.com/robots.txt?type=shared"
        # a url file that's only shared between expired chats
        before_cutoff_shared_web_url = "https://google.com/robots.txt?type=shared_by_expiring"
        # a url file that's only shared between non-expired chats
        after_cutoff_shared_web_url = "https://google.com/robots.txt?type=shared_by_non_expiring"

        with mock_webui_user():
            shared_web_file_1 = self._process_web(shared_web_url)
            before_cutoff_shared_web_file_1 = self._process_web(before_cutoff_shared_web_url)
            before_cutoff_uploaded_file_1 = self._upload_file("dummy1.txt", b"dummy content")
            before_cutoff_uploaded_file_1_path = Path(Files.get_file_by_id(before_cutoff_uploaded_file_1.id).path) # type: ignore
            before_cutoff_chat_1_id = self._create_chat_with_files([shared_web_file_1, before_cutoff_shared_web_file_1, before_cutoff_uploaded_file_1])

            shared_web_file_2 = self._process_web(shared_web_url)
            before_cutoff_shared_web_file_2 = self._process_web(before_cutoff_shared_web_url)
            before_cutoff_uploaded_file_2 = self._upload_file("dummy2.txt", b"dummy content")
            before_cutoff_uploaded_file_2_path = Path(Files.get_file_by_id(before_cutoff_uploaded_file_2.id).path) # type: ignore
            before_cutoff_chat_2_id = self._create_chat_with_files([shared_web_file_2, before_cutoff_shared_web_file_2, before_cutoff_uploaded_file_2])
        
            time.sleep(1) # ensure that the cutoff is different from chat.created_at (timestamp has seconds granularity)
            cutoff = datetime.now()

            shared_web_file_3 = self._process_web(shared_web_url)
            after_cutoff_shared_web_file_1 = self._process_web(after_cutoff_shared_web_url)
            after_cutoff_uploaded_file_1 = self._upload_file("dummy3.txt", b"dummy content")
            after_cutoff_uploaded_file_1_path = Path(Files.get_file_by_id(after_cutoff_uploaded_file_1.id).path) # type: ignore
            after_cutoff_chat_1_id = self._create_chat_with_files([shared_web_file_3, after_cutoff_shared_web_file_1, after_cutoff_uploaded_file_1])

            after_cutoff_shared_web_file_2 = self._process_web(after_cutoff_shared_web_url)
            after_cutoff_uploaded_file_2 = self._upload_file("dummy4.txt", b"dummy content")
            after_cutoff_uploaded_file_2_path = Path(Files.get_file_by_id(after_cutoff_uploaded_file_2.id).path) # type: ignore
            after_cutoff_chat_2_id = self._create_chat_with_files([after_cutoff_shared_web_file_2, after_cutoff_uploaded_file_2])
         
        delete_chats_and_uploads(cutoff)

        # validate that all shared web files share the same collection name
        assert shared_web_file_1.collection_name == shared_web_file_2.collection_name == shared_web_file_3.collection_name
        assert before_cutoff_shared_web_file_1.collection_name == before_cutoff_shared_web_file_2.collection_name
        assert after_cutoff_shared_web_file_1.collection_name == after_cutoff_shared_web_file_2.collection_name

        # validate shared web files are deleted ONLYif they are not shared with any non-expired chats
        assert VECTOR_DB_CLIENT.has_collection(shared_web_file_1.collection_name)
        assert not VECTOR_DB_CLIENT.has_collection(before_cutoff_shared_web_file_1.collection_name)
        assert VECTOR_DB_CLIENT.has_collection(after_cutoff_shared_web_file_1.collection_name)

        # validate expected assets of before_cutoff_chat_1 are deleted
        assert not Chats.get_chat_by_id(before_cutoff_chat_1_id)
        assert not Files.get_file_by_id(before_cutoff_uploaded_file_1.id)
        assert not VECTOR_DB_CLIENT.has_collection(before_cutoff_shared_web_file_1.collection_name)
        assert not before_cutoff_uploaded_file_1_path.exists()

        # validate expected assets of before_cutoff_chat_2 are deleted
        assert not Chats.get_chat_by_id(before_cutoff_chat_2_id)
        assert not Files.get_file_by_id(before_cutoff_uploaded_file_2.id)
        assert not VECTOR_DB_CLIENT.has_collection(before_cutoff_shared_web_file_2.collection_name)
        assert not before_cutoff_uploaded_file_2_path.exists()

        # validate expected assets of after_cutoff_chat_1 are not deleted
        assert Chats.get_chat_by_id(after_cutoff_chat_1_id)
        assert Files.get_file_by_id(after_cutoff_uploaded_file_1.id)
        assert VECTOR_DB_CLIENT.has_collection(after_cutoff_shared_web_file_1.collection_name)
        assert after_cutoff_uploaded_file_1_path.exists()

        # validate expected assets of after_cutoff_chat_2 are not deleted
        assert Chats.get_chat_by_id(after_cutoff_chat_2_id)
        assert Files.get_file_by_id(after_cutoff_uploaded_file_2.id)
        assert VECTOR_DB_CLIENT.has_collection(after_cutoff_shared_web_file_2.collection_name)
        assert after_cutoff_uploaded_file_2_path.exists()


    def _upload_file(self, file_name: str, file_content: bytes) -> "ChatFileUploaded":
        """
        Helper function for POST /api/v1/files/
        """
        response = self.fast_api_client.post(
            "/api/v1/files/",
            files={"file": (file_name, file_content)}
        )
        response.raise_for_status()
        data = response.json()
        return ChatFileUploaded(
            id=data["id"],
            collection_name=data["meta"]["collection_name"],
        )

    def _process_web(self, url: str) -> "ChatFile":
        from open_webui.routers.retrieval import ProcessUrlForm
        """
        Helper function for POST /api/v1/retrieval/process/web/
        """
        response = self.fast_api_client.post(
            "/api/v1/retrieval/process/web",
            json=ProcessUrlForm(url=url).model_dump()
        )
        response.raise_for_status()
        return ChatFile(
            collection_name=response.json()["collection_name"],
        )

    def _create_chat_with_files(self, files: list["ChatFile | ChatFileUploaded"]) -> str:
        """
        Helper function for POST /api/v1/chats/new
        Returns the chat ID.
        """
        from open_webui.models.chats import ChatForm

        response = self.fast_api_client.post(
            "/api/v1/chats/new",
            json=ChatForm(chat={
                "files": [file.model_dump() for file in files],
            }).model_dump(),
        )
        response.raise_for_status()
        return response.json()["id"]



class TestDataCleanupTaskUnitTestPostgres(DataCleanupTaskUnitTestMixin, AbstractPostgresTest):
    ...

class TestDataCleanupTaskUnitTestSQLite(DataCleanupTaskUnitTestMixin, AbstractSQLiteTest):
    ...

class ChatFile(BaseModel):
    status: Literal["uploaded"] = "uploaded"
    collection_name: str


class ChatFileUploaded(ChatFile):
    id: str
