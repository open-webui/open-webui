import asyncio
import requests
import logging
import ftfy
import sys
import json

from azure.identity import DefaultAzureCredential
from langchain_community.document_loaders import (
    AzureAIDocumentIntelligenceLoader,
    BSHTMLLoader,
    CSVLoader,
    Docx2txtLoader,
    OutlookMessageLoader,
    PyPDFLoader,
    TextLoader,
    YoutubeLoader,
)
from langchain_core.documents import Document
import csv
import io

from open_webui.retrieval.loaders.external_document import ExternalDocumentLoader
from open_webui.retrieval.loaders.unstructured_loader import UnstructuredUnifiedLoader

from open_webui.retrieval.loaders.mistral import MistralLoader
from open_webui.retrieval.loaders.datalab_marker import DatalabMarkerLoader
from open_webui.retrieval.loaders.mineru import MinerULoader
from open_webui.retrieval.loaders.paddleocr_vl import PaddleOCRVLLoader

from open_webui.env import GLOBAL_LOG_LEVEL, REQUESTS_VERIFY, AIOHTTP_CLIENT_SESSION_SSL

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
                    slide_texts.append(shape.text_frame.text)
            if slide_texts:
                text_parts.append(f'Slide {i}:\n' + '\n'.join(slide_texts))
        return [
            Document(
                page_content='\n\n'.join(text_parts),
                metadata={'source': self.file_path},
            )
        ]


class RobustCSVLoader:
    """
    A robust CSV loader that handles malformed CSVs gracefully.

    Handles common issues:
    - Inconsistent column counts across rows
    - Various delimiters (comma, tab, semicolon, pipe)
    - Files with metadata rows before actual data
    - Encoding issues
    """

    def __init__(self, file_path: str):
        self.file_path = file_path

    def _detect_delimiter(self, sample: str) -> str:
        """Detect the most likely delimiter from a sample of the file."""
        delimiters = [',', '\t', ';', '|']
        counts = {}

        for delim in delimiters:
            # Count occurrences in each line and check consistency
            lines = sample.split('\n')[:10]  # Check first 10 lines
            line_counts = [line.count(delim) for line in lines if line.strip()]
            if line_counts:
                # Prefer delimiter with consistent counts across lines
                avg_count = sum(line_counts) / len(line_counts)
                consistency = 1 - (max(line_counts) - min(line_counts)) / max(max(line_counts), 1)
                counts[delim] = avg_count * consistency

        if counts:
            return max(counts, key=counts.get)
        return ','  # Default to comma

    def load(self) -> list[Document]:
        """Load CSV file with robust error handling."""
        try:
            # Try different encodings
            content = None
            for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    with open(self.file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                # Fallback: read as binary and decode with errors='replace'
                with open(self.file_path, 'rb') as f:
                    content = f.read().decode('utf-8', errors='replace')

            # Detect delimiter
            delimiter = self._detect_delimiter(content)
            log.info(f"CSV detected delimiter: '{delimiter}'")

            # Parse CSV with flexible settings
            rows = []
            max_columns = 0

            reader = csv.reader(io.StringIO(content), delimiter=delimiter)
            for i, row in enumerate(reader):
                if row:  # Skip empty rows
                    rows.append(row)
                    max_columns = max(max_columns, len(row))

            if not rows:
                return [Document(page_content="Empty CSV file", metadata={"source": self.file_path})]

            # Normalize rows to have consistent column count
            normalized_rows = []
            for row in rows:
                if len(row) < max_columns:
                    row = row + [''] * (max_columns - len(row))
                normalized_rows.append(row)

            # Convert to text representation
            # Use first row as header if it looks like one
            header = normalized_rows[0] if normalized_rows else []
            data_rows = normalized_rows[1:] if len(normalized_rows) > 1 else normalized_rows

            # Create document content
            content_parts = []

            # Add header info
            if header:
                content_parts.append(f"Columns ({len(header)}): {', '.join(str(h) for h in header)}")
                content_parts.append("")

            # Add data rows
            for i, row in enumerate(data_rows):
                if any(cell.strip() for cell in row):  # Skip completely empty rows
                    if header:
                        # Format as key-value pairs for better RAG
                        row_parts = []
                        for j, (h, v) in enumerate(zip(header, row)):
                            if v.strip():
                                row_parts.append(f"{h}: {v}")
                        if row_parts:
                            content_parts.append(f"Row {i+1}: {'; '.join(row_parts)}")
                    else:
                        content_parts.append(f"Row {i+1}: {', '.join(row)}")

            text = '\n'.join(content_parts)

            return [
                Document(
                    page_content=text,
                    metadata={
                        "source": self.file_path,
                        "row_count": len(data_rows),
                        "column_count": max_columns,
                        "delimiter": delimiter,
                    },
                )
            ]

        except Exception as e:
            log.error(f"Error loading CSV file {self.file_path}: {e}")
            # Last resort: just read as plain text
            try:
                with open(self.file_path, 'r', errors='replace') as f:
                    content = f.read()
                return [Document(page_content=content, metadata={"source": self.file_path, "parse_error": str(e)})]
            except Exception as e2:
                log.error(f"Failed to read CSV as text: {e2}")
                return [
                    Document(
                        page_content=f"Failed to parse CSV file: {e}",
                        metadata={"source": self.file_path, "error": str(e)},
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

        if self.extract_images == True:
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
    def __init__(self, url, api_key=None, file_path=None, mime_type=None, params=None):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.file_path = file_path
        self.mime_type = mime_type

        self.params = params or {}

    def load(self) -> list[Document]:
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
                verify=AIOHTTP_CLIENT_SESSION_SSL,
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

    async def aload(self, filename: str, file_content_type: str, file_path: str) -> list[Document]:
        """
        Async wrapper around `load`.

        Document loaders dispatched by `_get_loader` (PyMuPDF, Unstructured,
        python-docx, Tika, etc.) are uniformly synchronous and CPU/IO-bound.
        Calling `load` directly from an async handler would block the event
        loop for the entire parse — minutes for large PDFs. This offloads
        the work to a worker thread so the loop stays responsive.
        """
        return await asyncio.to_thread(self.load, filename, file_content_type, file_path)

    def _is_text_file(self, file_ext: str, file_content_type: str) -> bool:
        return file_ext in known_source_ext or (
            file_content_type
            and file_content_type.find('text/') >= 0
            # Avoid text/html files being detected as text
            and not file_content_type.find('html') >= 0
        )

    def _create_unstructured_loader(self, file_path: str) -> UnstructuredUnifiedLoader:
        """Helper method to create UnstructuredUnifiedLoader with consistent configuration"""
        return UnstructuredUnifiedLoader(
            file_path=file_path,
            strategy=self.kwargs.get("UNSTRUCTURED_STRATEGY", "hi_res"),
            include_metadata=self.kwargs.get("UNSTRUCTURED_INCLUDE_METADATA", True),
            clean_text=self.kwargs.get("UNSTRUCTURED_CLEAN_TEXT", True),
            chunk_by_semantic=self.kwargs.get("UNSTRUCTURED_SEMANTIC_CHUNKING", True),
            chunking_strategy=self.kwargs.get("UNSTRUCTURED_CHUNKING_STRATEGY", "by_title"),
            max_characters=self.kwargs.get("CHUNK_SIZE", 1000),
            chunk_overlap=self.kwargs.get("CHUNK_OVERLAP", 200),
            cleaning_level=self.kwargs.get("UNSTRUCTURED_CLEANING_LEVEL", "standard"),
            infer_table_structure=self.kwargs.get("UNSTRUCTURED_INFER_TABLE_STRUCTURE", False),
            extract_images_in_pdf=self.kwargs.get("UNSTRUCTURED_EXTRACT_IMAGES_IN_PDF", False),
        )

    def _get_loader(self, filename: str, file_content_type: str, file_path: str):
        file_ext = filename.split('.')[-1].lower()

        if (
            self.engine == 'external'
            and self.kwargs.get('EXTERNAL_DOCUMENT_LOADER_URL')
            and self.kwargs.get('EXTERNAL_DOCUMENT_LOADER_API_KEY')
        ):
            loader = ExternalDocumentLoader(
                file_path=file_path,
                url=self.kwargs.get('EXTERNAL_DOCUMENT_LOADER_URL'),
                api_key=self.kwargs.get('EXTERNAL_DOCUMENT_LOADER_API_KEY'),
                mime_type=file_content_type,
                user=self.user,
            )
        elif self.engine == 'tika' and self.kwargs.get('TIKA_SERVER_URL'):
            if self._is_text_file(file_ext, file_content_type):
                loader = TextLoader(file_path, autodetect_encoding=True)
            else:
                loader = TikaLoader(
                    url=self.kwargs.get('TIKA_SERVER_URL'),
                    file_path=file_path,
                    extract_images=self.kwargs.get('PDF_EXTRACT_IMAGES'),
                )
        elif (
            self.engine == 'datalab_marker'
            and self.kwargs.get('DATALAB_MARKER_API_KEY')
            and file_ext
            in [
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
            ]
        ):
            api_base_url = self.kwargs.get('DATALAB_MARKER_API_BASE_URL', '')
            if not api_base_url or api_base_url.strip() == '':
                api_base_url = 'https://www.datalab.to/api/v1/marker'  # https://github.com/open-webui/open-webui/pull/16867#issuecomment-3218424349

            loader = DatalabMarkerLoader(
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
        elif self.engine == 'docling' and self.kwargs.get('DOCLING_SERVER_URL'):
            if self._is_text_file(file_ext, file_content_type):
                loader = TextLoader(file_path, autodetect_encoding=True)
            else:
                # Build params for DoclingLoader
                params = self.kwargs.get('DOCLING_PARAMS', {})
                if not isinstance(params, dict):
                    try:
                        params = json.loads(params)
                    except json.JSONDecodeError:
                        log.error('Invalid DOCLING_PARAMS format, expected JSON object')
                        params = {}

                loader = DoclingLoader(
                    url=self.kwargs.get('DOCLING_SERVER_URL'),
                    api_key=self.kwargs.get('DOCLING_API_KEY', None),
                    file_path=file_path,
                    mime_type=file_content_type,
                    params=params,
                )
        elif (
            self.engine == 'document_intelligence'
            and self.kwargs.get('DOCUMENT_INTELLIGENCE_ENDPOINT') != ''
            and (
                file_ext in ['pdf', 'docx', 'ppt', 'pptx']
                or file_content_type
                in [
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'application/vnd.ms-powerpoint',
                    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                ]
            )
        ):
            if self.kwargs.get('DOCUMENT_INTELLIGENCE_KEY') != '':
                loader = AzureAIDocumentIntelligenceLoader(
                    file_path=file_path,
                    api_endpoint=self.kwargs.get('DOCUMENT_INTELLIGENCE_ENDPOINT'),
                    api_key=self.kwargs.get('DOCUMENT_INTELLIGENCE_KEY'),
                    api_model=self.kwargs.get('DOCUMENT_INTELLIGENCE_MODEL'),
                )
            else:
                loader = AzureAIDocumentIntelligenceLoader(
                    file_path=file_path,
                    api_endpoint=self.kwargs.get('DOCUMENT_INTELLIGENCE_ENDPOINT'),
                    azure_credential=DefaultAzureCredential(),
                    api_model=self.kwargs.get('DOCUMENT_INTELLIGENCE_MODEL'),
                )
        elif self.engine == 'mineru' and file_ext in ['pdf']:  # MinerU currently only supports PDF
            mineru_timeout = self.kwargs.get('MINERU_API_TIMEOUT', 300)
            if mineru_timeout:
                try:
                    mineru_timeout = int(mineru_timeout)
                except ValueError:
                    mineru_timeout = 300

            loader = MinerULoader(
                file_path=file_path,
                api_mode=self.kwargs.get('MINERU_API_MODE', 'local'),
                api_url=self.kwargs.get('MINERU_API_URL', 'http://localhost:8000'),
                api_key=self.kwargs.get('MINERU_API_KEY', ''),
                params=self.kwargs.get('MINERU_PARAMS', {}),
                timeout=mineru_timeout,
            )
        elif (
            self.engine == 'mistral_ocr'
            and self.kwargs.get('MISTRAL_OCR_API_KEY') != ''
            and file_ext in ['pdf']  # Mistral OCR currently only supports PDF and images
        ):
            loader = MistralLoader(
                base_url=self.kwargs.get('MISTRAL_OCR_API_BASE_URL'),
                api_key=self.kwargs.get('MISTRAL_OCR_API_KEY'),
                file_path=file_path,
            )
        elif self.engine == 'paddleocr_vl' and self.kwargs.get('PADDLEOCR_VL_TOKEN') != '':
            loader = PaddleOCRVLLoader(
                api_url=self.kwargs.get('PADDLEOCR_VL_BASE_URL'),
                token=self.kwargs.get('PADDLEOCR_VL_TOKEN'),
                file_path=file_path,
            )
        elif file_ext == "csv":
            # Use robust CSV loader to handle malformed CSVs gracefully
            # This avoids pandas "Error tokenizing data" issues with inconsistent columns
            log.info(f"Using RobustCSVLoader for CSV file: {filename}")
            loader = RobustCSVLoader(file_path=file_path)
        elif self.engine in ["", "unstructured"]:
            # Use Unstructured.io as the default unified loader
            loader = self._create_unstructured_loader(file_path)
        else:
            # Fallback: route everything through Unstructured.io (covers all supported formats).
            log.info(f"Using Unstructured.io fallback for file type: {file_ext}")
            loader = self._create_unstructured_loader(file_path)

        return loader
