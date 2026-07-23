import unittest
from unittest.mock import patch

from open_webui.retrieval.utils import get_loader
from open_webui.retrieval.web.firecrawl import build_firecrawl_headers
from open_webui.retrieval.web.utils import (
    SafeWebBaseLoader,
    get_web_loader,
)


class TestWebLoaderConfig(unittest.TestCase):
    def test_build_firecrawl_headers(self):
        # Test headers with api_key
        headers_with_key = build_firecrawl_headers('test-key')
        self.assertEqual(headers_with_key.get('Authorization'), 'Bearer test-key')
        self.assertEqual(headers_with_key.get('Content-Type'), 'application/json')

        # Test headers with empty api_key (should not contain Authorization)
        headers_empty_key = build_firecrawl_headers('')
        self.assertNotIn('Authorization', headers_empty_key)
        self.assertEqual(headers_empty_key.get('Content-Type'), 'application/json')

        # Test headers with None api_key (should not contain Authorization)
        headers_none_key = build_firecrawl_headers(None)
        self.assertNotIn('Authorization', headers_none_key)
        self.assertEqual(headers_none_key.get('Content-Type'), 'application/json')

    @patch('open_webui.retrieval.web.utils.SafePlaywrightURLLoader')
    @patch('open_webui.retrieval.web.utils.SafeFireCrawlLoader')
    @patch('open_webui.retrieval.web.utils.SafeTavilyLoader')
    @patch('open_webui.retrieval.web.utils.SafeMicrosoftWebIQLoader')
    @patch('open_webui.retrieval.web.utils.ExternalWebLoader')
    @patch('open_webui.retrieval.web.utils.safe_validate_urls')
    def test_get_web_loader_fallback_and_custom(self, mock_validate, mock_ext, mock_ms, mock_tv, mock_fc, mock_pw):
        mock_validate.return_value = ['https://example.com']

        # Test fallback to constants (safe_web by default)
        loader = get_web_loader('https://example.com')
        self.assertIsInstance(loader, SafeWebBaseLoader)

        # Test custom engine playwright
        get_web_loader(
            'https://example.com',
            engine='playwright',
            playwright_timeout=5000,
            playwright_ws_url='ws://localhost',
        )
        mock_pw.assert_called_once_with(
            web_paths=['https://example.com'],
            verify_ssl=True,
            requests_per_second=2,
            continue_on_failure=True,
            trust_env=False,
            playwright_timeout=5000,
            playwright_ws_url='ws://localhost',
        )

        # Test custom engine firecrawl
        get_web_loader(
            'https://example.com',
            engine='firecrawl',
            firecrawl_api_key='fc-key',
            firecrawl_api_url='http://fc-api',
            firecrawl_timeout=20,
        )
        mock_fc.assert_called_once_with(
            web_paths=['https://example.com'],
            verify_ssl=True,
            requests_per_second=2,
            continue_on_failure=True,
            trust_env=False,
            api_key='fc-key',
            api_url='http://fc-api',
            timeout=20,
        )

        # Test custom engine tavily
        get_web_loader('https://example.com', engine='tavily', tavily_api_key='tv-key')
        mock_tv.assert_called_once_with(
            web_paths=['https://example.com'],
            verify_ssl=True,
            requests_per_second=2,
            continue_on_failure=True,
            trust_env=False,
            api_key='tv-key',
            extract_depth='basic',
        )

        # Test custom engine microsoft_web_iq
        get_web_loader(
            'https://example.com',
            engine='microsoft_web_iq',
            microsoft_web_iq_api_base_url='http://ms-api',
            microsoft_web_iq_api_key='ms-key',
            microsoft_web_iq_language='fr',
            timeout='15',
        )
        mock_ms.assert_called_once_with(
            web_paths=['https://example.com'],
            verify_ssl=True,
            requests_per_second=2,
            continue_on_failure=True,
            trust_env=False,
            api_base_url='http://ms-api',
            api_key='ms-key',
            language='fr',
            timeout=15,
        )

        # Test custom engine external
        get_web_loader(
            'https://example.com',
            engine='external',
            external_url='http://ext-api',
            external_api_key='ext-key',
        )
        mock_ext.assert_called_once_with(
            web_paths=['https://example.com'],
            verify_ssl=True,
            requests_per_second=2,
            continue_on_failure=True,
            trust_env=False,
            external_url='http://ext-api',
            external_api_key='ext-key',
        )

    @patch('open_webui.retrieval.utils.get_web_loader')
    def test_get_loader_config_propagation(self, mock_get_web_loader):
        # Mock config dict
        mock_config = {
            'web_loader_ssl_verification': True,
            'web_loader_concurrent_requests': 5,
            'web_search_trust_env': True,
            'web_loader_engine': 'firecrawl',
            'web_loader_timeout': '30',
            'playwright_timeout': 10000,
            'playwright_ws_url': 'ws://custom',
            'firecrawl_api_key': 'test-fc-key',
            'firecrawl_api_url': 'http://test-fc-base',
            'firecrawl_timeout': 20,
            'tavily_api_key': 'test-tv-key',
            'tavily_extract_depth': 'advanced',
            'microsoft_web_iq_api_base_url': 'http://test-ms-base',
            'microsoft_web_iq_api_key': 'test-ms-key',
            'microsoft_web_iq_language': 'fr',
            'external_web_loader_url': 'http://test-ext-url',
            'external_web_loader_api_key': 'test-ext-key',
        }

        get_loader(None, 'https://example.com', mock_config)

        mock_get_web_loader.assert_called_once_with(
            'https://example.com',
            verify_ssl=True,
            requests_per_second=5,
            trust_env=True,
            engine='firecrawl',
            timeout='30',
            playwright_timeout=10000,
            playwright_ws_url='ws://custom',
            firecrawl_api_key='test-fc-key',
            firecrawl_api_url='http://test-fc-base',
            firecrawl_timeout=20,
            tavily_api_key='test-tv-key',
            tavily_extract_depth='advanced',
            microsoft_web_iq_api_base_url='http://test-ms-base',
            microsoft_web_iq_api_key='test-ms-key',
            microsoft_web_iq_language='fr',
            external_url='http://test-ext-url',
            external_api_key='test-ext-key',
        )
