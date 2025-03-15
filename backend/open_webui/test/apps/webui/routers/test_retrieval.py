from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user
from unittest.mock import patch, MagicMock

from langchain_core.documents import Document


class TestRetrieval(AbstractPostgresTest):
    BASE_PATH = "/api/v1/retrieval"

    def setup_class(cls):
        super().setup_class()
        from open_webui.retrieval.web.main import SearchResult

        cls.searchresult = SearchResult

    @patch("open_webui.routers.retrieval.search_web")
    @patch("open_webui.routers.retrieval.get_web_loader")
    @patch("open_webui.routers.retrieval.get_config")
    @patch("open_webui.routers.retrieval.run_in_threadpool")
    def test_process_web_search_bypass_scrape(
        self,
        mock_run_in_threadpool,
        mock_get_config,
        mock_get_web_loader,
        mock_search_web,
    ):
        # Setup mocks
        mock_search_results = [
            self.searchresult(
                link="https://example.com/1",
                title="Example 1",
                snippet="Example snippet 1",
            ),
            self.searchresult(
                link="https://example.com/2", title=None, snippet="Example snippet 2"
            ),
        ]
        mock_search_web.return_value = mock_search_results

        mock_config = MagicMock()
        mock_config.BYPASS_WEB_SEARCH_RESULT_LINK_SCRAPE = True
        mock_get_config.return_value = mock_config

        mock_run_in_threadpool.return_value = True

        # Execute function
        with mock_webui_user(id="2"):
            response = self.fast_api_client.post(
                self.create_url("/process/web/search"),
                json={
                    "query": "test query",
                    "collection_name": "test_collection",
                },
            )

        # Assertions
        assert response.status_code == 200
        result = response.json()
        assert not mock_get_web_loader.called
        assert result["status"] is True
        assert result["collection_name"] == "test_collection"
        assert result["loaded_count"] == 2
        assert result["docs"][0].page_content == "Example snippet 1"
        assert result["docs"][1].metadata["title"] == "https://example.com/2"

    @patch("open_webui.routers.retrieval.search_web")
    @patch("open_webui.routers.retrieval.get_web_loader")
    @patch("open_webui.routers.retrieval.get_config")
    @patch("open_webui.routers.retrieval.run_in_threadpool")
    def test_process_web_search_with_scrape(
        self,
        mock_run_in_threadpool,
        mock_get_config,
        mock_get_web_loader,
        mock_search_web,
    ):
        # Setup mocks
        mock_search_results = [
            self.searchresult(
                link="https://example.com/1",
                title="Example 1",
                snippet="Example snippet 1",
            ),
        ]
        mock_search_web.return_value = mock_search_results

        mock_config = MagicMock()
        mock_config.BYPASS_WEB_SEARCH_RESULT_LINK_SCRAPE = False
        mock_get_config.return_value = mock_config

        mock_loader = MagicMock()
        mock_loader.load.return_value = [Document(page_content="Web page content")]
        mock_get_web_loader.return_value = mock_loader

        mock_run_in_threadpool.return_value = True

        # Execute function
        with mock_webui_user(id="2"):
            response = self.fast_api_client.post(
                self.create_url("/process/web/search"),
                json={
                    "query": "test query",
                    "collection_name": "test_collection",
                },
            )

        # Assertions
        assert response.status_code == 200
        result = response.json()
        assert mock_get_web_loader.called
        assert result["status"] is True
        assert result["collection_name"] == "test_collection"
        assert result["loaded_count"] == 1
        assert result["docs"][0].page_content == "Web page content"
