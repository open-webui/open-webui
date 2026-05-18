import base64
import os
import requests
import logging
import sys
from typing import List

from langchain_core.documents import Document
from open_webui.env import GLOBAL_LOG_LEVEL

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)


class PaddleOCRVLLoader:
    """Loader that uses PaddleOCR-vl API to extract text from PDF/images."""

    def __init__(
        self,
        api_url: str,
        token: str,
        file_path: str,
    ):
        if not api_url or not token:
            raise ValueError('PaddleOCR-vl API URL and Token are required.')
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'File not found at {file_path}')

        self.api_url = api_url.rstrip('/')
        self.token = token
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)

    def load(self) -> List[Document]:
        log.info(f'Processing with PaddleOCR-vl: {self.file_path}')

        try:
            with open(self.file_path, 'rb') as file:
                file_bytes = file.read()
                file_data = base64.b64encode(file_bytes).decode('ascii')
        except Exception as e:
            log.error(f'Failed to read file {self.file_path}: {e}')
            raise

        headers = {'Authorization': f'token {self.token}', 'Content-Type': 'application/json'}

        # Detect fileType based on file extension
        ext = self.file_path.lower().split('.')[-1]
        image_extensions = ['png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp']
        file_type = 1 if ext in image_extensions else 0

        payload = {
            'file': file_data,
            'fileType': file_type,
            'useDocOrientationClassify': False,
            'useDocUnwarping': False,
            'useChartRecognition': False,
        }

        try:
            response = requests.post(f'{self.api_url}/layout-parsing', json=payload, headers=headers)
            response.raise_for_status()

            result = response.json().get('result', {})
            layout_results = result.get('layoutParsingResults', [])

            documents = []
            total_pages = len(layout_results)
            skipped_pages = 0

            for i, res in enumerate(layout_results):
                markdown_text = res.get('markdown', {}).get('text', '')

                if isinstance(markdown_text, str):
                    cleaned_content = markdown_text.strip()
                else:
                    cleaned_content = str(markdown_text).strip()

                if not cleaned_content:
                    skipped_pages += 1
                    continue

                documents.append(
                    Document(
                        page_content=cleaned_content,
                        metadata={
                            'page': i,
                            'page_label': i + 1,
                            'total_pages': total_pages,
                            'file_name': self.file_name,
                            'processing_engine': 'paddleocr-vl',
                        },
                    )
                )

            if skipped_pages > 0:
                log.info(f'PaddleOCR-vl: Processed {len(documents)} pages, skipped {skipped_pages} empty pages.')

            if not documents:
                log.warning('No valid text content found by PaddleOCR-vl.')
                return [
                    Document(
                        page_content='No valid text content found in document',
                        metadata={
                            'error': 'no_valid_pages',
                            'file_name': self.file_name,
                            'processing_engine': 'paddleocr-vl',
                        },
                    )
                ]

            return documents

        except Exception as e:
            log.error(f'Error calling PaddleOCR-vl: {e}')
            return [
                Document(
                    page_content=f'Error during OCR processing: {e}',
                    metadata={
                        'error': 'processing_failed',
                        'file_name': self.file_name,
                        'processing_engine': 'paddleocr-vl',
                    },
                )
            ]
