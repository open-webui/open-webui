

from typing import IO
import logging
import requests

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

class PdftotextLoader():
    def __init__(self, pdf_path: str, url: str, max_pages: int):
        self.pdf_path = pdf_path
        url+="/api-ds-ocr/text_extract"
        self.url = url
        self.max_pages = max_pages
    def load(self):
        with open(self.pdf_path, "rb") as f:
            pdf = f.read()

        log.info(self.max_pages)

        headers = {
            "accept": "application/json",
        }
        files = {
            "pdf_upload": pdf
        }
        data = {
            'max_pages' : self.max_pages,
            'header_footer': False
        }

        r = requests.post(url=self.url, headers=headers, files=files, data=data, timeout=240)
        log.info(r)
        response = r.json()
        txt = response.get("text", "")

        log.info(
            "REQ_ID: %s Extracted text from pdf using OCR, len(txt) -> %s "
        )

        return txt