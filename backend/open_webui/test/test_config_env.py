"""
Unit tests for environment variable JSON config parsing.

Tests the pattern used by OPENAI_API_CONFIGS and OLLAMA_API_CONFIGS:
    json.loads(os.environ.get('VAR_NAME', '{}'))
with fallback to {} on parse error.

We define a helper that mirrors the parsing logic rather than importing
config.py directly (it has heavy import-time side effects).
"""

import json
import os


def parse_config_from_env(var_name: str) -> dict:
    """Parse a JSON dict from an env var, returning {} on any failure."""
    raw = os.environ.get(var_name, '')
    if not raw:
        return {}
    try:
        result = json.loads(raw)
        if not isinstance(result, dict):
            return {}
        return result
    except (json.JSONDecodeError, TypeError):
        return {}


class TestOpenAIApiConfigs:
    ENV_VAR = 'OPENAI_API_CONFIGS'

    def test_absent_returns_empty_dict(self, monkeypatch):
        monkeypatch.delenv(self.ENV_VAR, raising=False)
        assert parse_config_from_env(self.ENV_VAR) == {}

    def test_empty_string_returns_empty_dict(self, monkeypatch):
        monkeypatch.setenv(self.ENV_VAR, '')
        assert parse_config_from_env(self.ENV_VAR) == {}

    def test_single_connection(self, monkeypatch):
        cfg = {
            '0': {
                'enable': True,
                'model_ids': ['gpt-4o'],
                'prefix_id': 'openai',
            }
        }
        monkeypatch.setenv(self.ENV_VAR, json.dumps(cfg))
        result = parse_config_from_env(self.ENV_VAR)
        assert result == cfg
        assert result['0']['model_ids'] == ['gpt-4o']

    def test_multiple_connections(self, monkeypatch):
        cfg = {
            '0': {
                'enable': True,
                'model_ids': ['gpt-4o'],
                'prefix_id': 'openai',
            },
            '1': {
                'enable': True,
                'model_ids': ['claude-3-opus'],
                'prefix_id': 'anthropic',
                'connection_type': 'external',
            },
        }
        monkeypatch.setenv(self.ENV_VAR, json.dumps(cfg))
        result = parse_config_from_env(self.ENV_VAR)
        assert len(result) == 2
        assert '0' in result
        assert '1' in result

    def test_invalid_json_returns_empty_dict(self, monkeypatch):
        monkeypatch.setenv(self.ENV_VAR, '{not valid json')
        assert parse_config_from_env(self.ENV_VAR) == {}

    def test_non_dict_json_returns_empty_dict(self, monkeypatch):
        monkeypatch.setenv(self.ENV_VAR, '["a", "b"]')
        assert parse_config_from_env(self.ENV_VAR) == {}

    def test_azure_openai_config(self, monkeypatch):
        """Realistic Azure OpenAI connection config."""
        cfg = {
            '0': {
                'enable': True,
                'model_ids': ['gpt-4o', 'gpt-4o-mini'],
                'prefix_id': 'azure',
                'connection_type': 'external',
                'auth_type': 'bearer',
                'headers': {
                    'api-key': 'sk-azure-abc123',
                },
            }
        }
        monkeypatch.setenv(self.ENV_VAR, json.dumps(cfg))
        result = parse_config_from_env(self.ENV_VAR)
        assert result['0']['auth_type'] == 'bearer'
        assert result['0']['headers']['api-key'] == 'sk-azure-abc123'
        assert result['0']['prefix_id'] == 'azure'
        assert result['0']['connection_type'] == 'external'


class TestOllamaApiConfigs:
    ENV_VAR = 'OLLAMA_API_CONFIGS'

    def test_absent_returns_empty_dict(self, monkeypatch):
        monkeypatch.delenv(self.ENV_VAR, raising=False)
        assert parse_config_from_env(self.ENV_VAR) == {}

    def test_empty_string_returns_empty_dict(self, monkeypatch):
        monkeypatch.setenv(self.ENV_VAR, '')
        assert parse_config_from_env(self.ENV_VAR) == {}

    def test_single_connection(self, monkeypatch):
        cfg = {
            '0': {
                'enable': True,
                'model_ids': ['llama3'],
                'prefix_id': 'ollama',
            }
        }
        monkeypatch.setenv(self.ENV_VAR, json.dumps(cfg))
        result = parse_config_from_env(self.ENV_VAR)
        assert result == cfg

    def test_multiple_connections(self, monkeypatch):
        cfg = {
            '0': {
                'enable': True,
                'model_ids': ['llama3'],
            },
            '1': {
                'enable': False,
                'model_ids': ['mistral'],
            },
        }
        monkeypatch.setenv(self.ENV_VAR, json.dumps(cfg))
        result = parse_config_from_env(self.ENV_VAR)
        assert len(result) == 2
        assert result['1']['enable'] is False

    def test_invalid_json_returns_empty_dict(self, monkeypatch):
        monkeypatch.setenv(self.ENV_VAR, '{{bad')
        assert parse_config_from_env(self.ENV_VAR) == {}
