"""from open_webui.utils.ocr_engine import OCREngine
#from langchain.schema import Document
from langchain_core.documents import Document

class GoogleOCRLoader:

    def __init__(self, filename, content_type, file_path):
        self.filename = filename
        self.content_type = content_type
        self.file_path = file_path

    def load(self) -> list[Document]:
        # Actually read the file bytes here
        with open(self.file_path, "rb") as f:
            file_bytes = f.read()
            
        text = self.ocr.extract_text(file_bytes)

        return [
            Document(
                page_content=text,
                metadata={
                    "source": self.filename,
                    "content_type": self.content_type,
                    "loader": "google_ocr",
                },
            )
        ]"""
from langchain_core.documents import Document
from open_webui.utils.ocr_engine import OCREngine

class GoogleOCRLoader:
    def __init__(self, filename, content_type, file_path):
        # IMPORTANT: Replace these with your actual GCP details or env variables
        self.ocr = OCREngine(
            project_id="clinicia-hipaa-dev",
            location="us", # e.g., 'us' or 'eu'
            processor_id="41a120aee1cd018"
        )
        self.filename = filename
        self.content_type = content_type
        self.file_path = file_path

    def load(self) -> list[Document]:
        with open(self.file_path, "rb") as f:
            file_bytes = f.read()
            
        # Document AI uses the content_type to decide how to parse (PDF vs Image)
        text = self.ocr.extract_text(file_bytes, self.content_type)

        return [
            Document(
                page_content=text,
                metadata={
                    "source": self.filename,
                    "content_type": self.content_type,
                    "loader": "google_doc_ai",
                },
            )
        ]