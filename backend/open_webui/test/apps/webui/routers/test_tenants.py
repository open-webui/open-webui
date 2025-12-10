from uuid import uuid4

from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user

import boto3
from moto import mock_aws


class TestTenants(AbstractPostgresTest):
    BASE_PATH = "/api/v1/tenants"

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.mock = mock_aws()
        cls.mock.start()
        cls.region = "us-east-2"
        cls.bucket_name = f"tenant-test-bucket-{uuid4().hex}"
        s3_client = boto3.client("s3", region_name=cls.region)
        s3_client.create_bucket(
            Bucket=cls.bucket_name,
            CreateBucketConfiguration={"LocationConstraint": cls.region},
        )

        from open_webui.routers import tenants as tenants_router
        from open_webui.services import s3 as s3_service
        from open_webui.models.tenants import Tenants
        from open_webui.models.users import Users

        tenants_router.S3_BUCKET_NAME = cls.bucket_name
        tenants_router.STORAGE_PROVIDER = "s3"
        s3_service._s3_client = None

        cls.tenants = Tenants
        cls.users = Users

    @classmethod
    def teardown_class(cls):
        cls.mock.stop()
        super().teardown_class()

    def setup_method(self):
        super().setup_method()
        from open_webui.services import s3 as s3_service

        s3_service._s3_client = None

    def _create_tenant_via_api(self, name="Tenant One"):
        with mock_webui_user(role="admin"):
            response = self.fast_api_client.post(self.create_url(""), json={"name": name})
        assert response.status_code == 200
        return response.json()

    def test_create_list_delete_tenant(self):
        tenant = self._create_tenant_via_api("Tenant Alpha")

        with mock_webui_user(role="admin"):
            list_response = self.fast_api_client.get(self.create_url(""))
        assert list_response.status_code == 200
        data = list_response.json()
        assert len(data) == 1
        assert data[0]["id"] == tenant["id"]
        assert data[0]["name"] == "Tenant Alpha"
        assert data[0]["s3_bucket"] == tenant["s3_bucket"]

        with mock_webui_user(role="admin"):
            delete_response = self.fast_api_client.delete(self.create_url(f"/{tenant['id']}"))
        assert delete_response.status_code == 200

    def test_delete_blocked_when_users_exist(self):
        tenant = self._create_tenant_via_api("Tenant Bravo")

        self.users.insert_new_user(
            id="tenant-user",
            name="Tenant User",
            email="tenant.user@example.com",
            profile_image_url="/tenant-user.png",
            role="user",
            tenant_id=tenant["id"],
        )

        with mock_webui_user(role="admin"):
            response = self.fast_api_client.delete(self.create_url(f"/{tenant['id']}"))
        assert response.status_code == 400
        assert "Cannot delete tenant" in response.json()["detail"]

    def test_prompt_upload_list_delete(self):
        tenant = self._create_tenant_via_api("Tenant Prompts")
        files = {"file": ("greeting.txt", b"hello prompts", "text/plain")}

        with mock_webui_user(role="admin"):
            upload_response = self.fast_api_client.post(
                self.create_url(f"/{tenant['id']}/prompts"), files=files
            )
        assert upload_response.status_code == 200
        uploaded = upload_response.json()
        assert uploaded["bucket"] == self.bucket_name
        assert uploaded["key"].endswith("greeting.txt")

        with mock_webui_user(role="admin"):
            list_response = self.fast_api_client.get(self.create_url(f"/{tenant['id']}/prompts"))
        assert list_response.status_code == 200
        prompts = list_response.json()
        assert len(prompts) == 1
        assert prompts[0]["key"] == uploaded["key"]

        with mock_webui_user(role="admin"):
            delete_response = self.fast_api_client.request(
                "DELETE",
                self.create_url(f"/{tenant['id']}/prompts"),
                json={"key": uploaded["key"]},
            )
        assert delete_response.status_code == 200

        with mock_webui_user(role="admin"):
            list_response = self.fast_api_client.get(self.create_url(f"/{tenant['id']}/prompts"))
        assert list_response.status_code == 200
        assert list_response.json() == []
