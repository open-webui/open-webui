import io
import json

from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user, mock_rag_user


class TestDocuments(AbstractPostgresTest):

    BASE_PATH = "/api/v1/documents"

    def setup_class(cls):
        super().setup_class()
        from apps.webui.models.documents import Documents

        cls.documents = Documents

    def test_documents(self):
        # Empty database
        assert len(self.documents.get_docs()) == 0
        with mock_webui_user(id="2"):
            response = self.fast_api_client.get(self.create_url("/"))
        assert response.status_code == 200
        assert len(response.json()) == 0

        # Upload document
        with mock_rag_user(id="2"):
            file = io.BytesIO()
            file.write(b"test")
            response = self.fast_api_client.post(
                "/rag/api/v1/doc",
                files={
                    "file": ("doc_name.txt", b"test", "text/plain"),
                },
            )
        assert response.status_code == 200
        file_id = response.json()["file_id"]

        # Create a new document
        with mock_webui_user(id="2"):
            response = self.fast_api_client.post(
                self.create_url("/create"),
                json={
                    "name": "doc_name",
                    "title": "doc title",
                    "collection_name": "custom collection",
                    "filename": "doc_name.pdf",
                    "content": json.dumps({"file_id": file_id}),
                },
            )
        assert response.status_code == 200
        assert response.json()["name"] == "doc_name"
        assert len(self.documents.get_docs()) == 1

        # Get the document
        with mock_webui_user(id="2"):
            response = self.fast_api_client.get(self.create_url("/doc?name=doc_name"))
        assert response.status_code == 200
        data = response.json()
        assert data["collection_name"] == "custom collection"
        assert data["name"] == "doc_name"
        assert data["title"] == "doc title"
        assert data["filename"] == "doc_name.pdf"
        assert data["content"] == {"file_id": file_id}

        # Create another document
        with mock_webui_user(id="2"):
            response = self.fast_api_client.post(
                self.create_url("/create"),
                json={
                    "name": "doc_name 2",
                    "title": "doc title 2",
                    "collection_name": "custom collection 2",
                    "filename": "doc_name2.pdf",
                    "content": "",
                },
            )
        assert response.status_code == 200
        assert response.json()["name"] == "doc_name 2"
        assert len(self.documents.get_docs()) == 2

        # Get all documents
        with mock_webui_user(id="2"):
            response = self.fast_api_client.get(self.create_url("/"))
        assert response.status_code == 200
        assert len(response.json()) == 2

        # Update the first document
        with mock_webui_user(id="2"):
            response = self.fast_api_client.post(
                self.create_url("/doc/update?name=doc_name"),
                json={"name": "doc_name rework", "title": "updated title"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "doc_name rework"
        assert data["title"] == "updated title"

        # Tag the first document
        with mock_webui_user(id="2"):
            response = self.fast_api_client.post(
                self.create_url("/doc/tags"),
                json={
                    "name": "doc_name rework",
                    "tags": [{"name": "testing-tag"}, {"name": "another-tag"}],
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "doc_name rework"
        assert data["content"] == {
            "tags": [{"name": "testing-tag"}, {"name": "another-tag"}],
            "file_id": file_id,
        }
        assert len(self.documents.get_docs()) == 2

        # Download the first document
        with mock_webui_user(id="2"):
            response = self.fast_api_client.get(f"/api/v1/files/{file_id}/content")
        assert response.status_code == 200
        assert response.content == b"test"

        # Delete the first document
        with mock_webui_user(id="2"):
            response = self.fast_api_client.delete(
                self.create_url("/doc/delete?name=doc_name rework")
            )
        assert response.status_code == 200
        assert len(self.documents.get_docs()) == 1
