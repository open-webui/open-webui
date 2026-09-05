import io
import logging
from typing import Literal

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders.parsers.pdf import PyPDFParser
from langchain_core.document_loaders import Blob
from PIL import Image
from pypdf import PageObject
from pypdf.generic import StreamObject

log = logging.getLogger(__name__)


def _is_cmyk_jpeg(image_stream: StreamObject) -> bool:
    """True when the image is a CMYK JPEG whose data pypdf will hand back inverted."""
    filters = image_stream['/Filter'] if '/Filter' in image_stream else None
    if (filters[-1] if isinstance(filters, list) else filters) != '/DCTDecode':
        return False
    return Image.open(io.BytesIO(image_stream.get_data())).mode == 'CMYK'


class PyPDFParserWithSafeImages(PyPDFParser):
    """PyPDFParser that lets pypdf decode page images instead of reading /Filter itself."""

    def extract_images_from_page(self, page: PageObject) -> str:
        if not self.images_parser:
            return ''

        page.inline_images = {}
        try:
            images = page.images[:]
        except Exception as e:
            log.warning('Skipping images on PDF page: %s', e)
            return ''

        image_texts = []
        for index in range(len(images)):
            try:
                image_file = images[index]
                image_stream = image_file.indirect_reference.get_object()
                image = image_file.image
                # pypdf re-inverts CMYK JPEGs that PIL already un-inverted, and an /SMask makes that unrecoverable
                if _is_cmyk_jpeg(image_stream):
                    image = Image.open(io.BytesIO(image_stream.get_data()))

                png_bytes = io.BytesIO()
                image.convert('RGB').save(png_bytes, format='PNG')
            except Exception as e:
                log.warning('Skipping unreadable image %s on PDF page: %s', index, e)
                continue

            blob = Blob.from_data(png_bytes.getvalue(), mime_type='image/png')
            text = next(self.images_parser.lazy_parse(blob)).page_content
            if text:
                image_texts.append(text)

        if not image_texts:
            return ''
        return '\n\n' + '\n'.join(image_texts) + '\n\n'


class PyPDFLoaderWithSafeImages(PyPDFLoader):
    """Loads a PDF with pypdf, tolerating images it cannot decode instead of failing the document."""

    def __init__(
        self, file_path: str, *, extract_images: bool = False, mode: Literal['single', 'page'] = 'page'
    ) -> None:
        super().__init__(file_path, extract_images=extract_images, mode=mode)
        self.parser = PyPDFParserWithSafeImages(extract_images=extract_images, mode=mode)
