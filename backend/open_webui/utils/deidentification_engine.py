import logging
import os
from google.cloud import dlp_v2

logger = logging.getLogger(__name__)


class DLPEngine:
    MAX_CHUNK_SIZE = 450000  # stay safely under DLP 512KB limit

    def __init__(self):
        self.client = dlp_v2.DlpServiceClient()

        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT env var not set")

        self.parent = f"projects/clinicia-hipaa-dev"

        # InfoTypes to detect
        self.inspect_config = {
            "info_types": [
                {"name": "AGE"},
                {"name": "DRIVERS_LICENSE_NUMBER"},
                {"name": "EMAIL_ADDRESS"},
                {"name": "PHONE_NUMBER"},
                {"name": "PERSON_NAME"},
                {"name": "FEMALE_NAME"},
                {"name": "FIRST_NAME"},
                {"name": "LAST_NAME"},
                {"name": "MALE_NAME"},
                {"name": "MEDICAL_ID"},
                {"name": "MEDICAL_RECORD_NUMBER"},
                {"name": "STREET_ADDRESS"},
                {"name": "CREDIT_CARD_DATA"},
            ]
        }

        # Replace sensitive values with infoType label
        self.deidentify_config = {
            "info_type_transformations": {
                "transformations": [
                    {
                        "primitive_transformation": {
                            "replace_with_info_type_config": {}
                        }
                    }
                ]
            }
        }

    def _process_chunk(self, text: str) -> str:
        """Send a single chunk to DLP."""
        try:
            response = self.client.deidentify_content(
                request={
                    "parent": self.parent,
                    "inspect_config": self.inspect_config,
                    "deidentify_config": self.deidentify_config,
                    "item": {"value": text},
                }
            )

            return response.item.value

        except Exception:
            logger.exception("DLP failed for chunk")
            raise RuntimeError("DLP processing failed")

    def _split_text(self, text: str):
        """Split large text into safe chunks."""
        for i in range(0, len(text), self.MAX_CHUNK_SIZE):
            yield text[i:i + self.MAX_CHUNK_SIZE]

    def deidentify(self, text: str) -> str:
        """
        Deidentify sensitive data in text.
        Works for both small and very large documents.
        """

        if not text:
            return text

        try:
            if len(text) <= self.MAX_CHUNK_SIZE:
                return self._process_chunk(text)

            logger.info("Large text detected. Chunking for DLP processing.")

            chunks = self._split_text(text)

            processed_chunks = []
            for chunk in chunks:
                processed_chunks.append(self._process_chunk(chunk))

            return "".join(processed_chunks)

        except Exception:
            logger.exception("DLP failed")
            raise RuntimeError("DLP processing failed")