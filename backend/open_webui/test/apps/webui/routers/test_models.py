from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user


class TestModels(AbstractPostgresTest):
    BASE_PATH = "/api/v1/models"

    def setup_class(cls):
        super().setup_class()
        from open_webui.models.models import Model

        cls.models = Model

    def test_models(self):
        # Query for a unique base model id to avoid depending on whatever
        # models might already exist in the test DB.
        unique_query = "test-base-model-id-for-models-router-test"

        with mock_webui_user(id="2", role="admin"):
            response = self.fast_api_client.get(
                self.create_url("/list", query_params={"query": unique_query})
            )
        assert response.status_code == 200
        assert response.json() == {"items": [], "total": 0}

        with mock_webui_user(id="2", role="admin"):
            response = self.fast_api_client.post(
                self.create_url("/create"),
                json={
                    "id": "my-model",
                    "base_model_id": unique_query,
                    "name": "Hello World",
                    "meta": {
                        "profile_image_url": "/static/favicon.png",
                        "description": "description",
                        "capabilities": None,
                        "model_config": {},
                    },
                    "params": {},
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "my-model"
        assert data["name"] == "Hello World"

        with mock_webui_user(id="2", role="admin"):
            response = self.fast_api_client.get(
                self.create_url("/model", query_params={"id": "my-model"})
            )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "my-model"
        assert data["name"] == "Hello World"

        with mock_webui_user(id="2", role="admin"):
            response = self.fast_api_client.get(
                self.create_url("/list", query_params={"query": unique_query})
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert len(payload["items"]) == 1
        assert payload["items"][0]["id"] == "my-model"

        with mock_webui_user(id="2", role="admin"):
            response = self.fast_api_client.post(
                self.create_url("/model/delete"),
                json={"id": "my-model"},
            )
        assert response.status_code == 200
        assert response.json() is True

        with mock_webui_user(id="2", role="admin"):
            response = self.fast_api_client.get(
                self.create_url("/model", query_params={"id": "my-model"})
            )
        assert response.status_code == 401
