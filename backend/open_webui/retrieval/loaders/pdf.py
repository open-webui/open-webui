import datetime as dt
import io
import logging
from pathlib import Path

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

log = logging.getLogger(__name__)


class PDFLoader(BaseLoader):
    def __init__(self, file_path, *, extract_images=False, mode='page'):
        if mode not in ('single', 'page'):
            raise ValueError("PDF mode must be 'single' or 'page'")
        self.file_path = str(Path(file_path).expanduser())
        self.extract_images = extract_images
        self.mode = mode
        self.ocr = None

    def lazy_load(self):
        from pypdf import PdfReader

        with open(self.file_path, 'rb') as file:
            reader = PdfReader(file)
            metadata = {'producer': 'PyPDF', 'creator': 'PyPDF', 'creationdate': ''}
            for key, value in (reader.metadata or {}).items():
                key = key.removeprefix('/').lower()
                value = value if type(value) in (str, int) else str(value)
                if key in ('creationdate', 'moddate') and isinstance(value, str):
                    try:
                        value = dt.datetime.strptime(value.replace("'", ''), 'D:%Y%m%d%H%M%S%z').isoformat()
                    except ValueError:
                        pass
                metadata[key] = (
                    value.strip()
                    if isinstance(value, str) and key not in ('creationdate', 'moddate', 'page_count', 'file_path')
                    else value
                )
            metadata.update(source=self.file_path, total_pages=len(reader.pages))
            labels = reader.page_labels if self.mode == 'page' else None
            texts = []
            for index, page in enumerate(reader.pages):
                text = page.extract_text()
                if self.extract_images:
                    image_text = self._extract_images(page)
                    if image_text:
                        text = self._merge_image_text(text, image_text)
                text = text.strip()
                if self.mode == 'page':
                    yield Document(page_content=text, metadata={**metadata, 'page': index, 'page_label': labels[index]})
                else:
                    texts.append(text)
            if self.mode == 'single':
                yield Document(page_content='\n\f'.join(texts), metadata=metadata)

    @staticmethod
    def _merge_image_text(text, image_text):
        # Insert before the final paragraphs/footer where possible, matching existing chunks.
        position, separator = len(text), '\n\n'
        for _ in range(2):
            for delimiter in ('\n\n\n', '\n\n'):
                found = text.rfind(delimiter, 0, position)
                if found >= 0:
                    position, separator = found, delimiter
                    break
            else:
                break
        return text[:position] + separator + image_text + text[position:]

    def _extract_images(self, page):
        import numpy as np
        from PIL import Image, UnidentifiedImageError

        if '/Resources' not in page or '/XObject' not in page['/Resources']:
            return ''
        texts = []
        xobjects = page['/Resources']['/XObject']
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
                pixels = np.array(image.convert('RGB'))
            except Exception as e:
                log.warning('Skipping unreadable PDF image %s: %s', name, e)
                continue

            if self.ocr is None:
                from rapidocr import RapidOCR

                self.ocr = RapidOCR()
            result = self.ocr(pixels)
            if result and result.txts:
                texts.append('\n'.join(result.txts).strip())
        return '\n\n' + '\n'.join(filter(None, texts)) + '\n\n' if any(texts) else ''
