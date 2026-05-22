from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user


class TestVersionSecurity(AbstractPostgresTest):
    BASE_PATH = ''

    def test_version_requires_auth(self):
        response = self.fast_api_client.get('/api/version')
        assert response.status_code == 401

        response = self.fast_api_client.get('/version')
        assert response.status_code == 401

    def test_health_requires_auth(self):
        response = self.fast_api_client.get('/health')
        assert response.status_code == 401

        response = self.fast_api_client.get('/healthz')
        assert response.status_code == 401

    def test_authenticated_version_and_health(self):
        with mock_webui_user():
            version_response = self.fast_api_client.get('/api/version')
            health_response = self.fast_api_client.get('/healthz')

        assert version_response.status_code == 200
        assert version_response.json()['version'] is not None
        assert 'deployment_id' in version_response.json()
        assert health_response.status_code == 200
        assert health_response.json() == {'status': True}