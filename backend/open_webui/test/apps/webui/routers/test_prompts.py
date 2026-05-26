from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user


class TestPrompts(AbstractPostgresTest):
    BASE_PATH = '/api/v1/prompts'

    def setup_class(cls):
        super().setup_class()
        from open_webui.models.prompts import Prompts

        cls.prompts = Prompts

    def test_create_and_get_prompt(self):
        # Initially the prompt list should be empty
        with mock_webui_user():
            response = self.fast_api_client.get(self.create_url('/'))
        assert response.status_code == 200
        assert response.json() == []

        # Create a new prompt
        with mock_webui_user():
            response = self.fast_api_client.post(
                self.create_url('/create'),
                json={
                    'command': '/greet',
                    'name': 'Greeting Prompt',
                    'content': 'Say hello to {{name}}.',
                },
            )
        assert response.status_code == 200
        created = response.json()
        assert created['command'] == '/greet'
        assert created['name'] == 'Greeting Prompt'
        assert created['content'] == 'Say hello to {{name}}.'
        assert created['id'] is not None
        prompt_id = created['id']

        # Retrieve the prompt by ID and verify the fields round-trip correctly
        with mock_webui_user():
            response = self.fast_api_client.get(self.create_url(f'/id/{prompt_id}'))
        assert response.status_code == 200
        fetched = response.json()
        assert fetched['id'] == prompt_id
        assert fetched['command'] == '/greet'
        assert fetched['name'] == 'Greeting Prompt'
        assert fetched['content'] == 'Say hello to {{name}}.'

        # The prompt should now appear in the listing
        with mock_webui_user():
            response = self.fast_api_client.get(self.create_url('/'))
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]['id'] == prompt_id

    def test_duplicate_command_rejected(self):
        # Create the first prompt
        with mock_webui_user():
            response = self.fast_api_client.post(
                self.create_url('/create'),
                json={
                    'command': '/summarize',
                    'name': 'Summarizer',
                    'content': 'Summarize the following text: {{text}}',
                },
            )
        assert response.status_code == 200

        # A second prompt with the same command must be rejected
        with mock_webui_user():
            response = self.fast_api_client.post(
                self.create_url('/create'),
                json={
                    'command': '/summarize',
                    'name': 'Duplicate Summarizer',
                    'content': 'Another summarize prompt.',
                },
            )
        assert response.status_code == 400

    def test_update_and_delete_prompt(self):
        # Create a prompt to exercise the update/delete lifecycle
        with mock_webui_user():
            response = self.fast_api_client.post(
                self.create_url('/create'),
                json={
                    'command': '/translate',
                    'name': 'Translator',
                    'content': 'Translate this text to {{language}}: {{text}}',
                },
            )
        assert response.status_code == 200
        prompt_id = response.json()['id']

        # Update name and content
        with mock_webui_user():
            response = self.fast_api_client.post(
                self.create_url(f'/id/{prompt_id}/update'),
                json={
                    'command': '/translate',
                    'name': 'Translator v2',
                    'content': 'Translate the following to {{language}}: {{text}}',
                },
            )
        assert response.status_code == 200
        updated = response.json()
        assert updated['name'] == 'Translator v2'
        assert updated['content'] == 'Translate the following to {{language}}: {{text}}'

        # Re-fetch to confirm the change is durable, not just in the response object
        with mock_webui_user():
            response = self.fast_api_client.get(self.create_url(f'/id/{prompt_id}'))
        assert response.status_code == 200
        assert response.json()['name'] == 'Translator v2'
        assert response.json()['content'] == 'Translate the following to {{language}}: {{text}}'

        # Delete the prompt
        with mock_webui_user():
            response = self.fast_api_client.delete(self.create_url(f'/id/{prompt_id}/delete'))
        assert response.status_code == 200
        assert response.json() is True

        # Verify the prompt is gone
        with mock_webui_user():
            response = self.fast_api_client.get(self.create_url(f'/id/{prompt_id}'))
        assert response.status_code == 404
