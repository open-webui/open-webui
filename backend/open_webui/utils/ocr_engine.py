"""import logging
from google.cloud import vision

logger = logging.getLogger(__name__)

class OCREngine:
    def __init__(self):
        self.client = vision.ImageAnnotatorClient()

    def extract_text(self, file_bytes: bytes) -> str:
        try:
            image = vision.Image(content=file_bytes)

            response = self.client.document_text_detection(image=image)

            if response.error.message:
                raise RuntimeError(response.error.message)

            return response.full_text_annotation.text or ""

        except Exception as e:
            logger.exception("OCR extraction failed")
            raise RuntimeError("OCR processing failed") from e"""

import logging
# Import the specific version to avoid namespace collisions
import google.cloud.documentai_v1 as documentai

logger = logging.getLogger(__name__)

class OCREngine:
    def __init__(self, project_id: str, location: str, processor_id: str):
        self.project_id = project_id
        self.location = location
        self.processor_id = processor_id
        
        # Use a dict instead of ClientOptions class to avoid Pylance/Import errors
        client_options = {"api_endpoint": f"{self.location}-documentai.googleapis.com"}
        
        self.client = documentai.DocumentProcessorServiceClient(
            client_options=client_options
        )

    def extract_text(self, file_bytes: bytes, mime_type: str) -> str:
        try:
            name = self.client.processor_path(self.project_id, self.location, self.processor_id)

            raw_document = documentai.RawDocument(content=file_bytes, mime_type=mime_type)
            request = documentai.ProcessRequest(name=name, raw_document=raw_document)

            result = self.client.process_document(request=request)
            
            # Use .text property; result.document is the Document proto object
            return result.document.text or ""

        except Exception as e:
            logger.exception(f"Document AI extraction failed: {str(e)}")
            # Helpful for debugging in logs
            raise RuntimeError(f"GCP DocAI Error: {str(e)}") from e