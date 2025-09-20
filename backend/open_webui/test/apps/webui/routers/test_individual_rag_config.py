from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user

class TestRagConfig(AbstractPostgresTest):
    BASE_PATH = "/api/v1/config"

    def setup_class(cls):
        super().setup_class()
        from open_webui.models.knowledge import Knowledges

        cls.knowledges = Knowledges

    def setup_method(self):
        super().setup_method()
        # Insert a knowledge base with default settings
        self.knowledges.insert_new_knowledge(
            id="1",
            name="Default KB",
            rag_config={
                "DEFAULT_RAG_SETTINGS": True,
                "TEMPLATE": "default-template",
                "TOP_K": 5,
            },
        )
        # Insert a knowledge base with custom RAG config
        self.knowledges.insert_new_knowledge(
            id="2",
            name="Custom KB",
            rag_config={
                "DEFAULT_RAG_SETTINGS": False,
                "TEMPLATE": "custom-template",
                "TOP_K": 10,
                "web": {
                    "ENABLE_WEB_SEARCH": True,
                    "WEB_SEARCH_ENGINE": "custom-engine"
                }
            },
        )

    def test_get_rag_config_default(self):
        # Should return default config for knowledge base with DEFAULT_RAG_SETTINGS True
        with mock_webui_user(id="1"):
            response = self.fast_api_client.post(
                self.create_url(""),
                json={"knowledge_id": "1"}
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert data["RAG_TEMPLATE"] == "default-template"
        assert data["TOP_K"] == 5
        assert data["DEFAULT_RAG_SETTINGS"] is True

    def test_get_rag_config_individual(self):
        # Should return custom config for knowledge base with DEFAULT_RAG_SETTINGS False
        with mock_webui_user(id="1"):
            response = self.fast_api_client.post(
                self.create_url(""),
                json={"knowledge_id": "2"}
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert data["RAG_TEMPLATE"] == "custom-template"
        assert data["TOP_K"] == 10
        assert data["DEFAULT_RAG_SETTINGS"] is False
        assert data["web"]["ENABLE_WEB_SEARCH"] is True
        assert data["web"]["WEB_SEARCH_ENGINE"] == "custom-engine"

    def test_get_rag_config_unauthorized(self):
        # Should return 401 if not authenticated
        response = self.fast_api_client.post(
            self.create_url(""),
            json={"knowledge_id": "1"}
        )
        assert response.status_code == 401

    def test_update_rag_config_default(self):
        # Should update the global config for knowledge base with DEFAULT_RAG_SETTINGS True
        with mock_webui_user(id="1"):
            response = self.fast_api_client.post(
                self.create_url("/update"),
                json={
                    "knowledge_id": "1",
                    "RAG_TEMPLATE": "updated-template",
                    "TOP_K": 42,
                    "ENABLE_RAG_HYBRID_SEARCH": False,
                }
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert data["RAG_TEMPLATE"] == "updated-template"
        assert data["TOP_K"] == 42
        assert data["ENABLE_RAG_HYBRID_SEARCH"] is False

    def test_update_rag_config_individual(self):
        # Should update the config for knowledge base with DEFAULT_RAG_SETTINGS False
        with mock_webui_user(id="1"):
            response = self.fast_api_client.post(
                self.create_url("/update"),
                json={
                    "knowledge_id": "2",
                    "TEMPLATE": "individual-updated",
                    "TOP_K": 99,
                    "web": {
                        "ENABLE_WEB_SEARCH": False,
                        "WEB_SEARCH_ENGINE": "updated-engine"
                    }
                }
            )
        assert response.status_code == 200
        data = response.json()
        assert data["TEMPLATE"] == "individual-updated"
        assert data["TOP_K"] == 99
        assert data["web"]["ENABLE_WEB_SEARCH"] is False
        assert data["web"]["WEB_SEARCH_ENGINE"] == "updated-engine"

    def test_update_reranking_model_and_states_individual(self):
        # Simulate app state for reranking models
        app = self.fast_api_client.app
        app.state.rf = {}
        app.state.config.LOADED_RERANKING_MODELS = {"": [], "external": []}
        app.state.config.DOWNLOADED_RERANKING_MODELS = {"": [], "external": []}

        # Update individual config with new reranking model
        with mock_webui_user(id="1"):
            response = self.fast_api_client.post(
                self.create_url("/update"),
                json={
                    "knowledge_id": "2",
                    "RAG_RERANKING_MODEL": "",
                    "RAG_RERANKING_ENGINE": "",
                    "RAG_EXTERNAL_RERANKER_URL": "",
                    "RAG_EXTERNAL_RERANKER_API_KEY": "",
                    "ENABLE_RAG_HYBRID_SEARCH": True,
                }
            )
        assert response.status_code == 200
        data = response.json()
        # Model should be in loaded and downloaded models
        loaded = app.state.config.LOADED_RERANKING_MODELS[""]
        downloaded = app.state.config.DOWNLOADED_RERANKING_MODELS[""]
        assert any(m["RAG_RERANKING_MODEL"] == "BBAI/bge-reranker-v2-m3" for m in loaded)
        assert "BBAI/bge-reranker-v2-m3" in downloaded
        assert "BBAI/bge-reranker-v2-m3" in app.state.rf

    def test_update_reranking_model_and_states_default(self):
        # Simulate app state for reranking models
        app = self.fast_api_client.app
        app.state.rf = {}
        app.state.config.LOADED_RERANKING_MODELS = {"": [], "external": []}
        app.state.config.DOWNLOADED_RERANKING_MODELS = {"": [], "external": []}

        # Update default config with new reranking model
        with mock_webui_user(id="1"):
            response = self.fast_api_client.post(
                self.create_url("/update"),
                json={
                    "knowledge_id": "1",
                    "RAG_RERANKING_MODEL": "BBAI/bge-reranker-v2-m3",
                    "RAG_RERANKING_ENGINE": "",
                    "RAG_EXTERNAL_RERANKER_URL": "",
                    "RAG_EXTERNAL_RERANKER_API_KEY": "",
                    "ENABLE_RAG_HYBRID_SEARCH": True,
                }
            )
        assert response.status_code == 200
        data = response.json()
        loaded = app.state.config.LOADED_RERANKING_MODELS[""]
        downloaded = app.state.config.DOWNLOADED_RERANKING_MODELS[""]
        assert any(m["RAG_RERANKING_MODEL"] == "BBAI/bge-reranker-v2-m3" for m in loaded)
        assert "BBAI/bge-reranker-v2-m3" in downloaded
        assert "BBAI/bge-reranker-v2-m3" in app.state.rf

    def test_update_rag_config_unauthorized(self):
        # Should return 401 if not authenticated
        response = self.fast_api_client.post(
            self.create_url("/update"),
            json={"knowledge_id": "1", "RAG_TEMPLATE": "should-not-update"}
        )
        assert response.status_code == 401

    def test_reranking_model_freed_only_if_not_in_use_elsewhere(self):
        """
        Test that the reranking model is only deleted from state if no other knowledge base is using it.
        """
        app = self.fast_api_client.app
        app.state.rf = {"rerank-model-shared": object()}
        app.state.config.LOADED_RERANKING_MODELS = {"": [{"RAG_RERANKING_MODEL": "BBAI/bge-reranker-v2-m3"}]}
        app.state.config.DOWNLOADED_RERANKING_MODELS = {"": ["BBAI/bge-reranker-v2-m3"]}

        # Patch is_model_in_use_elsewhere to simulate model still in use
        from unittest.mock import patch

        with patch("open_webui.models.knowledge.Knowledges.is_model_in_use_elsewhere", return_value=True):
            with mock_webui_user(id="1"):
                response = self.fast_api_client.post(
                    self.create_url("/update"),
                    json={
                        "knowledge_id": "2",
                        "RAG_RERANKING_MODEL": "BBAI/bge-reranker-v2-m3",
                        "RAG_RERANKING_ENGINE": "",
                        "ENABLE_RAG_HYBRID_SEARCH": False,
                    }
                )
            assert response.status_code == 200
            # Model should NOT be deleted from state
            assert "rerank-model-shared" in app.state.rf
            assert any(m["RAG_RERANKING_MODEL"] == "BBAI/bge-reranker-v2-m3" for m in app.state.config.LOADED_RERANKING_MODELS[""])

        # Now simulate model NOT in use elsewhere
        app.state.rf = {"rerank-model-shared": object()}
        app.state.config.LOADED_RERANKING_MODELS = {"": [{"RAG_RERANKING_MODEL": "BBAI/bge-reranker-v2-m3"}]}
        app.state.config.DOWNLOADED_RERANKING_MODELS = {"": ["BBAI/bge-reranker-v2-m3"]}

        with patch("open_webui.models.knowledge.Knowledges.is_model_in_use_elsewhere", return_value=False):
            with mock_webui_user(id="1"):
                response = self.fast_api_client.post(
                    self.create_url("/update"),
                    json={
                        "knowledge_id": "2",
                        "RAG_RERANKING_MODEL": "BBAI/bge-reranker-v2-m3",
                        "RAG_RERANKING_ENGINE": "",
                        "ENABLE_RAG_HYBRID_SEARCH": False,
                    }
                )
            assert response.status_code == 200
            # Model should be deleted from state
            assert "rerank-model-shared" not in app.state.rf
            assert not any(m["RAG_RERANKING_MODEL"] == "BBAI/bge-reranker-v2-m3" for m in app.state.config.LOADED_RERANKING_MODELS[""])
    
    def test_get_embedding_config_default(self):
        # Should return default embedding config for knowledge base with DEFAULT_RAG_SETTINGS True
        # First, add embedding config to the default KB
        self.knowledges.update_rag_config_by_id(
            id="1",
            rag_config={
                "DEFAULT_RAG_SETTINGS": True,
                "embedding_engine": "",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "embedding_batch_size": 1,
                "openai_config": {"url": "https://api.openai.com", "key": "default-key"},
                "ollama_config": {"url": "http://localhost:11434", "key": "ollama-key"},
            }
        )
        with mock_webui_user(id="1"):
            response = self.fast_api_client.post(
                self.create_url("/embedding"),
                json={"knowledge_id": "1"}
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert data["embedding_engine"] == ""
        assert data["embedding_model"] == "sentence-transformers/all-MiniLM-L6-v2"
        assert data["embedding_batch_size"] == 1
        assert data["openai_config"]["url"] == "https://api.openai.com"
        assert data["openai_config"]["key"] == "default-key"
        assert data["ollama_config"]["url"] == "http://localhost:11434"
        assert data["ollama_config"]["key"] == "ollama-key"

    def test_get_embedding_config_individual(self):
        # Should return custom embedding config for knowledge base with DEFAULT_RAG_SETTINGS False
        self.knowledges.update_rag_config_by_id(
            id="2",
            rag_config={
                "DEFAULT_RAG_SETTINGS": False,
                "embedding_engine": "",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "embedding_batch_size": 2,
                "openai_config": {"url": "https://custom.openai.com", "key": "custom-key"},
                "ollama_config": {"url": "http://custom-ollama:11434", "key": "custom-ollama-key"},
            }
        )
        with mock_webui_user(id="1"):
            response = self.fast_api_client.post(
                self.create_url("/embedding"),
                json={"knowledge_id": "2"}
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert data["embedding_engine"] == ""
        assert data["embedding_model"] == "sentence-transformers/all-MiniLM-L6-v2"
        assert data["embedding_batch_size"] == 2
        assert data["openai_config"]["url"] == "https://custom.openai.com"
        assert data["openai_config"]["key"] == "custom-key"
        assert data["ollama_config"]["url"] == "http://custom-ollama:11434"
        assert data["ollama_config"]["key"] == "custom-ollama-key"

    def test_update_embedding_config_default(self):
        # Should update the global embedding config for knowledge base with DEFAULT_RAG_SETTINGS True
        with mock_webui_user(id="1"):
            response = self.fast_api_client.post(
                self.create_url("/embedding/update"),
                json={
                    "knowledge_id": "1",
                    "embedding_engine": "",
                    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                    "embedding_batch_size": 4,
                    "openai_config": {"url": "https://api.openai.com/v2", "key": "updated-key"},
                    "ollama_config": {"url": "http://localhost:11434", "key": "ollama-key"},
                }
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert data["embedding_engine"] == ""
        assert data["embedding_model"] == "sentence-transformers/all-MiniLM-L6-v2"
        assert data["embedding_batch_size"] == 4
        assert data["openai_config"]["url"] == "https://api.openai.com/v2"
        assert data["openai_config"]["key"] == "updated-key"

    def test_update_embedding_config_individual(self):
        # Should update the embedding config for knowledge base with DEFAULT_RAG_SETTINGS False
        with mock_webui_user(id="1"):
            response = self.fast_api_client.post(
                self.create_url("/embedding/update"),
                json={
                    "knowledge_id": "2",
                    "embedding_engine": "",
                    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                    "embedding_batch_size": 8,
                    "openai_config": {"url": "https://custom.openai.com/v2", "key": "custom-key-2"},
                    "ollama_config": {"url": "http://custom-ollama:11434/v2", "key": "custom-ollama-key-2"},
                }
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert data["embedding_engine"] == ""
        assert data["embedding_model"] == "sentence-transformers/all-MiniLM-L6-v2"
        assert data["embedding_batch_size"] == 8
        assert data["openai_config"]["url"] == "https://custom.openai.com/v2"
        assert data["openai_config"]["key"] == "custom-key-2"
        assert data["ollama_config"]["url"] == "http://custom-ollama:11434/v2"
        assert data["ollama_config"]["key"] == "custom-ollama-key-2"    