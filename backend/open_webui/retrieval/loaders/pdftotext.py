

from typing import IO
import logging
import requests

logger = logging.getLogger(__name__)


class PdftotextLoader():
    def __init__(self, pdf_path: str, url: str):
        self.pdf_path = pdf_path
        url+="/api-ds-ocr/text_extract"
        self.url = url
    def load(self):
        with open(self.pdf_path, "rb") as f:
            pdf = f.read()

        headers = {
            "accept": "application/json",
        }
        files = {
            "pdf_upload": pdf
        }
        data = {
            'header_footer': str(False)
        }

        r = requests.post(url=self.url, headers=headers, files=files, data=data, timeout=120)
        logger.info(r)
        response = r.json()
        txt = response.get("text", "")

        logger.info(
            "REQ_ID: %s Extracted text from pdf using OCR, len(txt) -> %s "
        )

        return txt