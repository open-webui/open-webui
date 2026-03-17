import json
import logging
import sys
from typing import Any

import ftfy
import requests
from azure.identity import DefaultAzureCredential
from langchain_community.document_loaders import (
    AzureAIDocumentIntelligenceLoader,
    BSHTMLLoader,
    CSVLoader,
    Docx2txtLoader,
    OutlookMessageLoader,
    PyPDFLoader,
    TextLoader,
)
from langchain_core.documents import Document
from open_webui.env import GLOBAL_LOG_LEVEL, REQUESTS_VERIFY
from open_webui.retrieval.loaders.datalab_marker import DatalabMarkerLoader
from open_webui.retrieval.loaders.external_document import ExternalDocumentLoader
from open_webui.retrieval.loaders.mineru import MinerULoader
from open_webui.retrieval.loaders.mistral import MistralLoader

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)

known_source_ext = [
    'go',
    'py',
    'java',
    'sh',
    'bat',
    'ps1',
    'cmd',
    'js',
    'ts',
    'css',
    'cpp',
    'hpp',
    'h',
    'c',
    'cs',
    'sql',
    'log',
    'ini',
    'pl',
    'pm',
    'r',
    'dart',
    'dockerfile',
    'env',
    'php',
    'hs',
    'hsc',
    'lua',
    'nginxconf',
    'conf',
    'm',
    'mm',
    'plsql',
    'perl',
    'rb',
    'rs',
    'db2',
    'scala',
    'bash',
    'swift',
    'vue',
    'svelte',
    'ex',
    'exs',
    'erl',
    'tsx',
    'jsx',
    'hs',
    'lhs',
    'json',
    'yaml',
    'yml',
    'toml',
]


class ExcelLoader:
    """Fallback Excel loader using pandas when unstructured is not installed."""

    def __init__(self, file_path):
        self.file_path = file_path

    def load(self) -> list[Document]:
        import pandas as pd

        text_parts = []
        xls = pd.ExcelFile(self.file_path)
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            text_parts.append(f'Sheet: {sheet_name}\n{df.to_string(index=False)}')
        return [
            Document(
                page_content='\n\n'.join(text_parts),
                metadata={'source': self.file_path},
            )
        ]


class PptxLoader:
    """Fallback PowerPoint loader using python-pptx when unstructured is not installed."""

    def __init__(self, file_path):
        self.file_path = file_path

    def load(self) -> list[Document]:
        from pptx import Presentation

        prs = Presentation(self.file_path)
        text_parts = []
        for i, slide in enumerate(prs.slides, 1):
            slide_texts = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    text_frame = getattr(shape, 'text_frame', None)
                    if text_frame is not None:
                        slide_texts.append(text_frame.text)
            if slide_texts:
                text_parts.append(f'Slide {i}:\n' + '\n'.join(slide_texts))
        return [
            Document(
                page_content='\n\n'.join(text_parts),
                metadata={'source': self.file_path},
            )
        ]


class TikaLoader:
    def __init__(self, url, file_path, mime_type=None, extract_images=None):
        self.url = url
        self.file_path = file_path
        self.mime_type = mime_type

        self.extract_images = extract_images

    def load(self) -> list[Document]:
        with open(self.file_path, 'rb') as f:
            data = f.read()

        if self.mime_type is not None:
            headers = {'Content-Type': self.mime_type}
        else:
            headers = {}

        if self.extract_images:
            headers['X-Tika-PDFextractInlineImages'] = 'true'

        endpoint = self.url
        if not endpoint.endswith('/'):
            endpoint += '/'
        endpoint += 'tika/text'

        r = requests.put(endpoint, data=data, headers=headers, verify=REQUESTS_VERIFY)

        if r.ok:
            raw_metadata = r.json()
            text = raw_metadata.get('X-TIKA:content', '<No text content found>').strip()

            if 'Content-Type' in raw_metadata:
                headers['Content-Type'] = raw_metadata['Content-Type']

            log.debug('Tika extracted text: %s', text)

            return [Document(page_content=text, metadata=headers)]
        else:
            raise Exception(f'Error calling Tika: {r.reason}')


class DoclingLoader:
    def __init__(
        self,
        url: str,
        api_key: str | None = None,
        file_path: str | None = None,
        mime_type: str | None = None,
        params: dict[str, Any] | None = None,
    ):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.file_path = file_path
        self.mime_type = mime_type

        self.params = params or {}

    def load(self) -> list[Document]:
        if self.file_path is None:
            raise ValueError('DoclingLoader requires a file_path')

        with open(self.file_path, 'rb') as f:
            headers = {}
            if self.api_key:
                headers['X-Api-Key'] = f'{self.api_key}'

            r = requests.post(
                f'{self.url}/v1/convert/file',
                files={
                    'files': (
                        self.file_path,
                        f,
                        self.mime_type or 'application/octet-stream',
                    )
                },
                data={
                    'image_export_mode': 'placeholder',
                    **self.params,
                },
                headers=headers,
            )
        if r.ok:
            result = r.json()
            document_data = result.get('document', {})
            text = document_data.get('md_content', '<No text content found>')

            metadata = {'Content-Type': self.mime_type} if self.mime_type else {}

            log.debug('Docling extracted text: %s', text)
            return [Document(page_content=text, metadata=metadata)]
        else:
            error_msg = f'Error calling Docling API: {r.reason}'
            if r.text:
                try:
                    error_data = r.json()
                    if 'detail' in error_data:
                        error_msg += f' - {error_data["detail"]}'
                except Exception:
                    error_msg += f' - {r.text}'
            raise Exception(f'Error calling Docling: {error_msg}')


class Loader:
    def __init__(self, engine: str = '', **kwargs):
        self.engine = engine
        self.user = kwargs.get('user', None)
        self.kwargs = kwargs

    def load(self, filename: str, file_content_type: str, file_path: str) -> list[Document]:
        loader = self._get_loader(filename, file_content_type, file_path)
        docs = loader.load()

        return [Document(page_content=ftfy.fix_text(doc.page_content), metadata=doc.metadata) for doc in docs]

    def _is_text_file(self, file_ext: str, file_content_type: str) -> bool:
        return file_ext in known_source_ext or bool(
            file_content_type
            and file_content_type.find('text/') >= 0
            # Avoid text/html files being detected as text
            and not file_content_type.find('html') >= 0
        )

    def _get_docling_params(self) -> dict:
        params = self.kwargs.get('DOCLING_PARAMS', {})
        if isinstance(params, dict):
            return params

        try:
            return json.loads(params)
        except json.JSONDecodeError:
            log.error('Invalid DOCLING_PARAMS format, expected JSON object')
            return {}

    def _get_external_loader(self, file_path: str, file_content_type: str):
        if not (
            self.engine == 'external'
            and self.kwargs.get('EXTERNAL_DOCUMENT_LOADER_URL')
            and self.kwargs.get('EXTERNAL_DOCUMENT_LOADER_API_KEY')
        ):
            return None

        return ExternalDocumentLoader(
            file_path=file_path,
            url=str(self.kwargs.get('EXTERNAL_DOCUMENT_LOADER_URL')),
            api_key=str(self.kwargs.get('EXTERNAL_DOCUMENT_LOADER_API_KEY')),
            mime_type=file_content_type,
            user=self.user,
        )

    def _get_tika_loader(self, file_ext: str, file_content_type: str, file_path: str):
        if not (self.engine == 'tika' and self.kwargs.get('TIKA_SERVER_URL')):
            return None

        if self._is_text_file(file_ext, file_content_type):
            return TextLoader(file_path, autodetect_encoding=True)

        return TikaLoader(
            url=str(self.kwargs.get('TIKA_SERVER_URL')),
            file_path=file_path,
            extract_images=bool(self.kwargs.get('PDF_EXTRACT_IMAGES')),
        )

    def _get_datalab_marker_loader(self, file_ext: str, file_path: str):
        supported_exts = {
            'pdf',
            'xls',
            'xlsx',
            'ods',
            'doc',
            'docx',
            'odt',
            'ppt',
            'pptx',
            'odp',
            'html',
            'epub',
            'png',
            'jpeg',
            'jpg',
            'webp',
            'gif',
            'tiff',
        }
        if not (
            self.engine == 'datalab_marker' and self.kwargs.get('DATALAB_MARKER_API_KEY') and file_ext in supported_exts
        ):
            return None

        api_base_url = self.kwargs.get('DATALAB_MARKER_API_BASE_URL', '')
        if not api_base_url or api_base_url.strip() == '':
            api_base_url = 'https://www.datalab.to/api/v1/marker'

        return DatalabMarkerLoader(
            file_path=file_path,
            api_key=self.kwargs['DATALAB_MARKER_API_KEY'],
            api_base_url=api_base_url,
            additional_config=self.kwargs.get('DATALAB_MARKER_ADDITIONAL_CONFIG'),
            use_llm=self.kwargs.get('DATALAB_MARKER_USE_LLM', False),
            skip_cache=self.kwargs.get('DATALAB_MARKER_SKIP_CACHE', False),
            force_ocr=self.kwargs.get('DATALAB_MARKER_FORCE_OCR', False),
            paginate=self.kwargs.get('DATALAB_MARKER_PAGINATE', False),
            strip_existing_ocr=self.kwargs.get('DATALAB_MARKER_STRIP_EXISTING_OCR', False),
            disable_image_extraction=self.kwargs.get('DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION', False),
            format_lines=self.kwargs.get('DATALAB_MARKER_FORMAT_LINES', False),
            output_format=self.kwargs.get('DATALAB_MARKER_OUTPUT_FORMAT', 'markdown'),
        )

    def _get_docling_loader(self, file_ext: str, file_content_type: str, file_path: str):
        if not (self.engine == 'docling' and self.kwargs.get('DOCLING_SERVER_URL')):
            return None

        if self._is_text_file(file_ext, file_content_type):
            return TextLoader(file_path, autodetect_encoding=True)

        return DoclingLoader(
            url=str(self.kwargs.get('DOCLING_SERVER_URL')),
            api_key=self.kwargs.get('DOCLING_API_KEY', None),
            file_path=file_path,
            mime_type=file_content_type,
            params=self._get_docling_params(),
        )

    def _get_document_intelligence_loader(self, file_ext: str, file_content_type: str, file_path: str):
        supported_types = {
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        }
        if not (
            self.engine == 'document_intelligence'
            and self.kwargs.get('DOCUMENT_INTELLIGENCE_ENDPOINT') != ''
            and (file_ext in ['pdf', 'docx', 'ppt', 'pptx'] or file_content_type in supported_types)
        ):
            return None

        loader_kwargs = {
            'file_path': file_path,
            'api_endpoint': self.kwargs.get('DOCUMENT_INTELLIGENCE_ENDPOINT'),
            'api_model': self.kwargs.get('DOCUMENT_INTELLIGENCE_MODEL'),
        }
        if self.kwargs.get('DOCUMENT_INTELLIGENCE_KEY') != '':
            loader_kwargs['api_key'] = self.kwargs.get('DOCUMENT_INTELLIGENCE_KEY')
        else:
            loader_kwargs['azure_credential'] = DefaultAzureCredential()

        return AzureAIDocumentIntelligenceLoader(**loader_kwargs)

    def _get_mineru_loader(self, file_ext: str, file_path: str):
        if not (self.engine == 'mineru' and file_ext in ['pdf']):
            return None

        mineru_timeout = self.kwargs.get('MINERU_API_TIMEOUT', 300)
        if mineru_timeout:
            try:
                mineru_timeout = int(mineru_timeout)
            except ValueError:
                mineru_timeout = 300

        return MinerULoader(
            file_path=file_path,
            api_mode=self.kwargs.get('MINERU_API_MODE', 'local'),
            api_url=self.kwargs.get('MINERU_API_URL', 'http://localhost:8000'),
            api_key=self.kwargs.get('MINERU_API_KEY', ''),
            params=self.kwargs.get('MINERU_PARAMS', {}),
            timeout=mineru_timeout,
        )

    def _get_mistral_loader(self, file_ext: str, file_path: str):
        if not (self.engine == 'mistral_ocr' and self.kwargs.get('MISTRAL_OCR_API_KEY') != '' and file_ext in ['pdf']):
            return None

        return MistralLoader(
            base_url=str(self.kwargs.get('MISTRAL_OCR_API_BASE_URL')),
            api_key=str(self.kwargs.get('MISTRAL_OCR_API_KEY')),
            file_path=file_path,
        )

    def _get_engine_loader(self, file_ext: str, file_content_type: str, file_path: str):
        for loader in (
            self._get_external_loader(file_path, file_content_type),
            self._get_tika_loader(file_ext, file_content_type, file_path),
            self._get_datalab_marker_loader(file_ext, file_path),
            self._get_docling_loader(file_ext, file_content_type, file_path),
            self._get_document_intelligence_loader(file_ext, file_content_type, file_path),
            self._get_mineru_loader(file_ext, file_path),
            self._get_mistral_loader(file_ext, file_path),
        ):
            if loader is not None:
                return loader

        return None

    def _get_rst_loader(self, file_path: str):
        try:
            from langchain_community.document_loaders import UnstructuredRSTLoader

            return UnstructuredRSTLoader(file_path, mode='elements')
        except ImportError:
            log.warning(
                "The 'unstructured' package is not installed. "
                'Falling back to plain text loading for .rst file. '
                'Install it with: pip install unstructured'
            )
            return TextLoader(file_path, autodetect_encoding=True)

    def _get_xml_loader(self, file_path: str):
        try:
            from langchain_community.document_loaders import UnstructuredXMLLoader

            return UnstructuredXMLLoader(file_path)
        except ImportError:
            log.warning(
                "The 'unstructured' package is not installed. "
                'Falling back to plain text loading for .xml file. '
                'Install it with: pip install unstructured'
            )
            return TextLoader(file_path, autodetect_encoding=True)

    def _get_epub_loader(self, file_path: str):
        try:
            from langchain_community.document_loaders import UnstructuredEPubLoader

            return UnstructuredEPubLoader(file_path)
        except ImportError:
            raise ValueError(
                "Processing .epub files requires the 'unstructured' package. Install it with: pip install unstructured"
            )

    def _get_excel_loader(self, file_path: str):
        try:
            from langchain_community.document_loaders import UnstructuredExcelLoader

            return UnstructuredExcelLoader(file_path)
        except ImportError:
            log.warning(
                "The 'unstructured' package is not installed. "
                'Falling back to pandas for Excel file loading. '
                'Install unstructured for better results: pip install unstructured'
            )
            return ExcelLoader(file_path)

    def _get_powerpoint_loader(self, file_path: str):
        try:
            from langchain_community.document_loaders import UnstructuredPowerPointLoader

            return UnstructuredPowerPointLoader(file_path)
        except ImportError:
            log.warning(
                "The 'unstructured' package is not installed. "
                'Falling back to python-pptx for PowerPoint file loading. '
                'Install unstructured for better results: pip install unstructured'
            )
            return PptxLoader(file_path)

    def _get_odt_loader(self, file_path: str):
        try:
            from langchain_community.document_loaders import UnstructuredODTLoader

            return UnstructuredODTLoader(file_path)
        except ImportError:
            raise ValueError(
                "Processing .odt files requires the 'unstructured' package. Install it with: pip install unstructured"
            )

    def _get_standard_loader(self, file_ext: str, file_path: str):
        if file_ext == 'pdf':
            return PyPDFLoader(
                file_path,
                extract_images=bool(self.kwargs.get('PDF_EXTRACT_IMAGES')),
                mode=self.kwargs.get('PDF_LOADER_MODE', 'page'),
            )
        if file_ext == 'csv':
            return CSVLoader(file_path, autodetect_encoding=True)
        if file_ext == 'rst':
            return self._get_rst_loader(file_path)
        if file_ext == 'xml':
            return self._get_xml_loader(file_path)
        if file_ext in ['htm', 'html']:
            return BSHTMLLoader(file_path, open_encoding='unicode_escape')
        if file_ext == 'md':
            return TextLoader(file_path, autodetect_encoding=True)
        if file_ext == 'msg':
            return OutlookMessageLoader(file_path)
        if file_ext == 'odt':
            return self._get_odt_loader(file_path)
        return None

    def _get_special_loader(self, file_ext: str, file_content_type: str, file_path: str):
        if file_content_type == 'application/epub+zip':
            return self._get_epub_loader(file_path)
        if (
            file_content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            or file_ext == 'docx'
        ):
            return Docx2txtLoader(file_path)
        if file_content_type in [
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        ] or file_ext in ['xls', 'xlsx']:
            return self._get_excel_loader(file_path)
        if file_content_type in [
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        ] or file_ext in ['ppt', 'pptx']:
            return self._get_powerpoint_loader(file_path)
        return None

    def _get_default_loader(self, file_ext: str, file_content_type: str, file_path: str):
        loader = self._get_standard_loader(file_ext, file_path)
        if loader is not None:
            return loader

        loader = self._get_special_loader(file_ext, file_content_type, file_path)
        if loader is not None:
            return loader

        return TextLoader(file_path, autodetect_encoding=True)

    def _get_loader(self, filename: str, file_content_type: str, file_path: str):
        file_ext = filename.split('.')[-1].lower()
        loader = self._get_engine_loader(file_ext, file_content_type, file_path)
        if loader is not None:
            return loader

        if self._is_text_file(file_ext, file_content_type):
            return TextLoader(file_path, autodetect_encoding=True)

        return self._get_default_loader(file_ext, file_content_type, file_path)
