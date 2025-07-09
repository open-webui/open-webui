from open_webui.test.util.abstract_integration_test import AbstractIntegrationTest
from open_webui.test.util.mock_user import mock_user


class TestModels(AbstractIntegrationTest):
    BASE_PATH = "/api/v1/models"

    def test_models(self, postgres_client):
        self.fast_api_client = postgres_client
        app = self.fast_api_client.app
        with mock_user(app, id="2"):
            response = self.fast_api_client.get(self.create_url("/"))
        assert response.status_code == 200
        assert len(response.json()) == 0

        with mock_user(app, id="2"):
            response = self.fast_api_client.post(
                self.create_url("/create"),
                json={
                    "id": "my-model",
                    "base_model_id": "base-model-id",
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

        with mock_user(app, id="2"):
            response = self.fast_api_client.get(self.create_url("/"))
        assert response.status_code == 200
        assert len(response.json()) == 1

        with mock_user(app, id="2"):
            response = self.fast_api_client.get(
                self.create_url("/", query_params={"id": "my-model"})
            )
        assert response.status_code == 200
        data = response.json()[0]
        assert data["id"] == "my-model"
        assert data["name"] == "Hello World"

        with mock_user(app, id="2"):
            response = self.fast_api_client.delete(
                self.create_url("/model/delete", query_params={"id": "my-model"})
            )
        assert response.status_code == 200

        with mock_user(app, id="2"):
            response = self.fast_api_client.get(self.create_url("/"))
        assert response.status_code == 200
        assert len(response.json()) == 0
