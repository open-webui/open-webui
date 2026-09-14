import json
import tempfile
import unittest
from unittest.mock import Mock, patch

from open_webui.retrieval.loaders.main import DoclingLoader, _parse_docling_markdown


class ParseDoclingMarkdownTest(unittest.TestCase):
    def test_success_returns_markdown(self):
        self.assertEqual(
            _parse_docling_markdown({'status': 'success', 'document': {'md_content': '# Hello'}}),
            '# Hello',
        )

    def test_partial_success_is_accepted(self):
        self.assertEqual(
            _parse_docling_markdown(
                {'status': 'partial_success', 'document': {'md_content': 'page'}}
            ),
            'page',
        )

    def test_success_status_is_case_insensitive(self):
        self.assertEqual(
            _parse_docling_markdown(
                {'status': 'Success', 'document': {'md_content': 'ok'}}
            ),
            'ok',
        )

    def test_failure_is_not_treated_as_success(self):
        with self.assertRaisesRegex(Exception, 'failure'):
            _parse_docling_markdown(
                {
                    'status': 'failure',
                    'document': {'md_content': ''},
                    'errors': [{'error_message': 'synthetic conversion failure'}],
                }
            )

    def test_skipped_null_markdown_raises(self):
        with self.assertRaisesRegex(Exception, 'skipped'):
            _parse_docling_markdown(
                {
                    'status': 'skipped',
                    'document': {'filename': 'sample.pdf', 'md_content': None},
                    'errors': [],
                }
            )

    def test_missing_status_raises(self):
        with self.assertRaisesRegex(Exception, 'missing'):
            _parse_docling_markdown({'document': {'md_content': '# Hello'}})

    def test_blank_markdown_on_success_raises(self):
        with self.assertRaisesRegex(Exception, 'no Markdown content'):
            _parse_docling_markdown({'status': 'success', 'document': {'md_content': '   '}})


class DoclingLoaderStatusTest(unittest.TestCase):
    def _load(self, payload):
        response = Mock(ok=True, reason='OK', text=json.dumps(payload))
        response.json.return_value = payload
        with tempfile.NamedTemporaryFile(suffix='.pdf') as source:
            loader = DoclingLoader(
                'http://docling.invalid',
                file_path=source.name,
                mime_type='application/pdf',
            )
            with patch(
                'open_webui.retrieval.loaders.main.requests.post', return_value=response
            ):
                return loader.load()

    def test_http_200_failure_does_not_index_placeholder(self):
        with self.assertRaisesRegex(Exception, 'synthetic conversion failure'):
            self._load(
                {
                    'document': {'filename': 'sample.pdf', 'md_content': ''},
                    'status': 'failure',
                    'errors': [
                        {
                            'component_type': 'document_backend',
                            'module_name': 'reproduction',
                            'error_message': 'synthetic conversion failure',
                        }
                    ],
                    'processing_time': 0.01,
                    'timings': {},
                }
            )

    def test_http_200_success_returns_document(self):
        docs = self._load(
            {
                'document': {'filename': 'sample.pdf', 'md_content': '# Title\n\nBody'},
                'status': 'success',
                'errors': [],
            }
        )
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].page_content, '# Title\n\nBody')

    def test_page_break_splitting_preserved(self):
        docs = self._load(
            {
                'document': {
                    'filename': 'sample.pdf',
                    'md_content': 'page one\fpage two',
                },
                'status': 'success',
                'errors': [],
            }
        )
        self.assertEqual(len(docs), 2)
        self.assertEqual(docs[0].page_content, 'page one')
        self.assertEqual(docs[0].metadata.get('page'), 0)
        self.assertEqual(docs[1].page_content, 'page two')
        self.assertEqual(docs[1].metadata.get('page'), 1)


if __name__ == '__main__':
    unittest.main()
