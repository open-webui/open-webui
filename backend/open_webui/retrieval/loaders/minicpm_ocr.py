import base64
import io
import logging
import os
import sys
from typing import List

import requests
from langchain_core.documents import Document
from open_webui.env import GLOBAL_LOG_LEVEL

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)

MINICPM_OCR_IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp']
MINICPM_OCR_SUPPORTED_EXTENSIONS = ['pdf'] + MINICPM_OCR_IMAGE_EXTENSIONS

DEFAULT_MINICPM_OCR_MODEL = 'minicpm-ocr'
DEFAULT_MINICPM_OCR_PROMPT = 'Text Recognition:'
DEFAULT_MINICPM_OCR_TIMEOUT = 120


class MiniCPMOCRLoader:
    """Loader that sends page images to a MiniCPM-OCR OpenAI-compatible service.

    MiniCPM-OCR is a block-level recognition model served over
    ``/v1/chat/completions``. PDF pages are not rendered: the image XObjects
    embedded in each page are OCR'd, which covers scanned PDFs. A page that
    already has a usable text layer is kept as-is, so digital PDFs do not pay
    for OCR and pages without embedded images still produce their text.
    """

    def __init__(
        self,
        base_url: str,
        file_path: str,
        api_key: str = '',
        model: str = DEFAULT_MINICPM_OCR_MODEL,
        timeout: int | str = DEFAULT_MINICPM_OCR_TIMEOUT,
        prompt: str = DEFAULT_MINICPM_OCR_PROMPT,
    ):
        if not base_url:
            raise ValueError('MiniCPM OCR API Base URL is required.')
        file_path = str(file_path)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'File not found at {file_path}')

        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or ''
        self.model = (model or '').strip() or DEFAULT_MINICPM_OCR_MODEL
        self.prompt = (prompt or '').strip() or DEFAULT_MINICPM_OCR_PROMPT
        self.timeout = self._parse_timeout(timeout)
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)

    def load(self) -> List[Document]:
        log.info('Processing with MiniCPM OCR: %s', self.file_path)

        file_ext = self.file_path.lower().rsplit('.', 1)[-1]
        if file_ext not in MINICPM_OCR_SUPPORTED_EXTENSIONS:
            raise ValueError(
                f'MiniCPM OCR does not support .{file_ext} files; expected one of {MINICPM_OCR_SUPPORTED_EXTENSIONS}.'
            )

        try:
            if file_ext == 'pdf':
                return self._load_pdf()
            return self._load_image()
        except Exception as e:
            log.error(f'Error calling MiniCPM OCR: {e}')
            return [self._error_document(f'Error during OCR processing: {e}')]

    def _load_image(self) -> List[Document]:
        from PIL import Image

        with Image.open(self.file_path) as image:
            text = self._recognize(image.convert('RGB'))

        if not text:
            return [self._error_document('No valid text content found in document', 'no_valid_pages')]

        return [Document(page_content=text, metadata=self._metadata(page=0, total_pages=1))]

    def _load_pdf(self) -> List[Document]:
        from pypdf import PdfReader

        reader = PdfReader(self.file_path)
        total_pages = len(reader.pages)
        documents = []
        skipped_pages = 0
        failed_pages = 0
        last_error = ''

        for index, page in enumerate(reader.pages):
            try:
                text = self._process_page(page)
            except Exception as e:
                failed_pages += 1
                last_error = str(e)
                log.error('MiniCPM OCR failed on page %s: %s', index + 1, e)
                continue

            if not text:
                skipped_pages += 1
                continue

            documents.append(Document(page_content=text, metadata=self._metadata(page=index, total_pages=total_pages)))

        if skipped_pages:
            log.info('MiniCPM OCR: processed %s pages, skipped %s empty pages.', len(documents), skipped_pages)
        if failed_pages:
            log.warning('MiniCPM OCR: %s pages failed and were not included.', failed_pages)

        if not documents:
            if last_error:
                return [self._error_document(f'Error during OCR processing: {last_error}')]
            return [self._error_document('No valid text content found in document', 'no_valid_pages')]

        return documents

    def _process_page(self, page) -> str:
        embedded_text = (page.extract_text() or '').strip()
        # Same validity rule as the PDF text extractor: a non-empty run of
        # (cid:..) placeholders means the text layer is unusable.
        if embedded_text and '(cid:' not in embedded_text:
            return embedded_text

        image_texts = []
        for image in self._page_images(page):
            text = self._recognize(image)
            if text:
                image_texts.append(text)

        return '\n\n'.join(image_texts).strip()

    def _page_images(self, page):
        from PIL import Image, UnidentifiedImageError

        if '/Resources' not in page:
            return []
        resources = page['/Resources']
        if '/XObject' not in resources:
            return []

        images = []
        xobjects = resources['/XObject']
        for name in xobjects:
            try:
                stream = xobjects[name]
                if stream.get('/Subtype') != '/Image':
                    continue
                try:
                    # Encoded images, including CMYK JPEGs, can go straight to Pillow.
                    image = Image.open(io.BytesIO(stream.get_data()))
                except UnidentifiedImageError:
                    image = stream.decode_as_image()
                images.append(image.convert('RGB'))
            except Exception as e:
                log.warning('Skipping unreadable PDF image %s: %s', name, e)

        return images

    def _recognize(self, image) -> str:
        payload = {
            'model': self.model,
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': self.prompt},
                        {
                            'type': 'image_url',
                            'image_url': {'url': self._encode_image(image)},
                        },
                    ],
                }
            ],
            'temperature': 0,
            'stream': False,
        }
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        response = requests.post(
            f'{self.base_url}/chat/completions',
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        body = response.json()

        try:
            choice = body['choices'][0]
            content = choice['message']['content']
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f'MiniCPM OCR returned an unexpected response: {body!r}') from exc

        # A cut-off completion must not be stored as complete OCR.
        finish_reason = choice.get('finish_reason')
        if finish_reason not in (None, '', 'stop'):
            raise RuntimeError(f'MiniCPM OCR returned an incomplete response (finish_reason={finish_reason!r})')

        if content is None:
            return ''
        if not isinstance(content, str):
            raise RuntimeError(f'MiniCPM OCR returned non-text content ({type(content).__name__}): {content!r}')
        return content.strip()

    def _metadata(self, page: int, total_pages: int) -> dict:
        return {
            'page': page,
            'page_label': page + 1,
            'total_pages': total_pages,
            'file_name': self.file_name,
            'processing_engine': 'minicpm-ocr',
        }

    def _error_document(self, content: str, error: str = 'processing_failed') -> Document:
        return Document(
            page_content=content,
            metadata={
                'error': error,
                'file_name': self.file_name,
                'processing_engine': 'minicpm-ocr',
            },
        )

    @staticmethod
    def _encode_image(image) -> str:
        with io.BytesIO() as buffer:
            image.save(buffer, format='PNG')
            encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
        return f'data:image/png;base64,{encoded}'

    @staticmethod
    def _parse_timeout(timeout: int | str) -> int:
        try:
            parsed = int(timeout)
        except (TypeError, ValueError):
            return DEFAULT_MINICPM_OCR_TIMEOUT
        return parsed if parsed > 0 else DEFAULT_MINICPM_OCR_TIMEOUT
