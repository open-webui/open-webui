from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user


class TestModels(AbstractPostgresTest):
    BASE_PATH = "/api/v1/models"

    def setup_class(cls):
        super().setup_class()
        from open_webui.models.models import Model

        cls.models = Model

    def test_models(self):
        with mock_webui_user(id="2"):
            response = self.fast_api_client.get(self.create_url("/"))
        assert response.status_code == 200
        assert len(response.json()) == 0

        with mock_webui_user(id="2"):
            response = self.fast_api_client.post(
                self.create_url("/add"),
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

        with mock_webui_user(id="2"):
            response = self.fast_api_client.get(self.create_url("/"))
        assert response.status_code == 200
        assert len(response.json()) == 1

        with mock_webui_user(id="2"):
            response = self.fast_api_client.get(
                self.create_url(query_params={"id": "my-model"})
            )
        assert response.status_code == 200
        data = response.json()[0]
        assert data["id"] == "my-model"
        assert data["name"] == "Hello World"

        with mock_webui_user(id="2"):
            response = self.fast_api_client.delete(
                self.create_url("/delete?id=my-model")
            )
        assert response.status_code == 200

        with mock_webui_user(id="2"):
            response = self.fast_api_client.get(self.create_url("/"))
        assert response.status_code == 200
        assert len(response.json()) == 0
