from pathlib import Path


def test_ollama_cloud_web_search_api_key_reads_matching_env_var():
    config_source = Path('backend/open_webui/config.py').read_text()

    setting_start = config_source.index("OLLAMA_CLOUD_WEB_SEARCH_API_KEY = ConfigVar(")
    setting_end = config_source.index('SEARXNG_QUERY_URL = ConfigVar(', setting_start)
    setting_source = config_source[setting_start:setting_end]

    assert "os.getenv('OLLAMA_CLOUD_WEB_SEARCH_API_KEY'" in setting_source
